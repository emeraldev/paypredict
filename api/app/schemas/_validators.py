"""Shared Pydantic field validators.

Currently one thing: `validate_opaque_id`, used on every lender-
facing `customer_id` / `collection_id` field so obvious PII shapes
(emails, whitespace-separated names, formatted phone numbers)
never land in `score_requests.external_customer_id`.
"""
from __future__ import annotations

import re

# URL-safe opaque token. Naturally forbids:
# - whitespace (names, addresses)
# - `@` (emails)
# - `+` `(` `)` (formatted phone numbers)
# - `,` `;` (CSV-shaped junk)
# - length > 128 (paragraphs, dumped documents)
#
# Length floor of 1 rejects the empty string (would otherwise slip
# through — pydantic doesn't reject empty strings by default).
OPAQUE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_\-.:]{1,128}$")


def validate_opaque_id(value: str) -> str:
    """Reject the most common PII shapes in customer/collection ids.

    Accepts URL-safe opaque tokens: UUIDs (`550e8400-...`), internal
    DB ids (`500000123`), prefixed strings (`EMP_ROSE_001`,
    `cust.sa.001`, `col:2026:08:13`). Length capped at 128 chars.

    Purely numeric IDs pass on purpose — some lenders' internal
    customer numbers look like `500000123` and it's not our call to
    decide whether that's a phone number in disguise. Our contract
    is to reject the OBVIOUSLY unsafe shapes (emails, names, phone
    numbers with formatting) and document the recommended shape in
    the public API description.

    Raises ValueError on rejection so Pydantic surfaces it as a
    422 with a clear message.
    """
    if not OPAQUE_ID_PATTERN.fullmatch(value):
        raise ValueError(
            "must be an opaque URL-safe token (1-128 characters, "
            "letters / digits / _ / - / . / : only). Personal data "
            "(names, emails, phone numbers, national IDs) is not "
            "accepted — hash or replace with an internal reference."
        )
    return value


# --- Password policy -----------------------------------------------------
#
# Applied at password-SET time (team invite, self-service change,
# admin-set), never at login-time — a legacy hash that predates the
# policy must still let its owner in so they can rotate. Once set, a
# new password must clear this bar.

PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_LENGTH = 72  # bcrypt caps input at 72 bytes; anything longer
# is silently truncated by the hasher. Reject up front so a user's
# 100-char password isn't quietly stored as its first 72 bytes.

_HAS_UPPER = re.compile(r"[A-Z]")
_HAS_LOWER = re.compile(r"[a-z]")
_HAS_DIGIT = re.compile(r"\d")
_HAS_SYMBOL = re.compile(r"[^A-Za-z0-9]")


def validate_password(value: str) -> str:
    """Enforce the platform password policy on any new/changed password.

    Rules (bank-grade minimum for SA / Zambia):
    - Length in [12, 72]. Under 12 is trivially crackable offline;
      over 72 is bcrypt's silent-truncation zone.
    - Must contain at least 3 of the 4 character classes: upper,
      lower, digit, symbol. "3 of 4" (not "all 4") keeps the rule
      passable with strong passphrases like `correct-horse-battery-9`
      while still rejecting `password123`.

    Not applied at login — a user with a legacy short password must
    still be able to log in so they can rotate to a compliant one.

    Raises ValueError on rejection so Pydantic surfaces it as 422.
    """
    if len(value) < PASSWORD_MIN_LENGTH:
        raise ValueError(
            f"password must be at least {PASSWORD_MIN_LENGTH} characters long"
        )
    if len(value) > PASSWORD_MAX_LENGTH:
        raise ValueError(
            f"password must be at most {PASSWORD_MAX_LENGTH} characters "
            "(bcrypt caps input at 72 bytes)"
        )
    classes_present = sum(
        bool(pattern.search(value))
        for pattern in (_HAS_UPPER, _HAS_LOWER, _HAS_DIGIT, _HAS_SYMBOL)
    )
    if classes_present < 3:
        raise ValueError(
            "password must include at least 3 of: uppercase letter, "
            "lowercase letter, digit, symbol"
        )
    return value
