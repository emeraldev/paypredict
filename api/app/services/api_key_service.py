"""Mint and parse API keys in the format that survives H2.

Key format:

    pk_live_<12-hex lookup_id>_<43-char secret>
    pk_test_<12-hex lookup_id>_<43-char secret>

Breakdown:
  - `pk_live_` / `pk_test_` — 8-char environment prefix.
  - 12-hex `lookup_id`      — 48 bits of entropy; the DB's UNIQUE
                              indexed lookup column. Public — not a
                              secret. At 2^48 the birthday collision
                              probability is negligible, and mint retries
                              once on the extremely unlikely IntegrityError.
  - `_`                     — mandatory separator; parse rejects anything
                              else at that position.
  - 43-char `secret`        — the actual secret half. `token_urlsafe(32)`
                              always produces 43 chars.

Why a separate lookup id instead of `raw_key[:8]`:
The old scheme lookup was the constant string `"pk_live_"` for every
key, which meant the auth path bcrypt-checked EVERY active key on the
platform per request (H2). Splitting into a public lookup id + a
private secret means auth is a single indexed row fetch followed by
one bcrypt — regardless of how many keys exist.

`key_hash` stays a bcrypt of the FULL raw key (not just the secret).
That way, even if a lookup_id leaks, an attacker still can't construct
the string to bcrypt against without also knowing the secret half.
"""
from __future__ import annotations

import secrets

# Fixed positions in the key string. The parser rejects anything that
# doesn't match — no defensive substring hunting, no ambiguity.
_ENV_PREFIX_LEN = 8   # "pk_live_" / "pk_test_"
_LOOKUP_ID_LEN = 12   # 12 hex chars = 48 bits
_SEPARATOR_POS = _ENV_PREFIX_LEN + _LOOKUP_ID_LEN
_MIN_TOTAL_LEN = _SEPARATOR_POS + 1 + 1  # env + lookup + '_' + at least 1 secret char

_ENV_PREFIXES = ("pk_live_", "pk_test_")


def mint_key(env_prefix: str = "pk_live_") -> tuple[str, str, str]:
    """Generate a new raw key and return (raw_key, lookup_id, display_prefix).

    `raw_key` is what the customer sees once; `lookup_id` is what the
    DB indexes on; `display_prefix` is what the dashboard shows in the
    API-keys list (env + lookup_id, no secret).

    The caller is responsible for bcrypt-hashing `raw_key` into
    `key_hash` and handling the (extremely unlikely) IntegrityError on
    a `lookup_id` collision by calling `mint_key` again.
    """
    if env_prefix not in _ENV_PREFIXES:
        raise ValueError(f"env_prefix must be one of {_ENV_PREFIXES}")
    lookup_id = secrets.token_hex(_LOOKUP_ID_LEN // 2)  # 6 bytes → 12 hex chars
    secret = secrets.token_urlsafe(32)                  # 43 chars, url-safe
    raw_key = f"{env_prefix}{lookup_id}_{secret}"
    display_prefix = f"{env_prefix}{lookup_id}"
    return raw_key, lookup_id, display_prefix


def parse_lookup_id(raw_key: str) -> str | None:
    """Extract the lookup_id from a bearer token, or None if the shape
    doesn't match. Used by the auth path to find the candidate row in
    one indexed SELECT.

    Rejecting invalid shapes early (before touching the DB) is a
    performance win and a debuggability win — a mis-typed token gets a
    fast 401 rather than a fanout query.
    """
    if len(raw_key) < _MIN_TOTAL_LEN:
        return None
    if not any(raw_key.startswith(p) for p in _ENV_PREFIXES):
        return None
    if raw_key[_SEPARATOR_POS] != "_":
        return None
    lookup_id = raw_key[_ENV_PREFIX_LEN:_SEPARATOR_POS]
    # Lookup ids are hex (0-9a-f) by construction; reject anything else
    # so a garbage token can't smuggle SQL-ish characters through.
    if not all(c in "0123456789abcdef" for c in lookup_id):
        return None
    return lookup_id
