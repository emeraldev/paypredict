"""Dashboard auth service.

Handles password hashing, JWT issuance/decoding, and user lookup for the
dashboard session-auth endpoints. Uses `bcrypt` directly (the project
already depends on it for API-key hashing) and `python-jose` for JWT.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import HTTPException
from jose import JWTError, jwt
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.user import User

# bcrypt has a hard 72-byte cap on the password input. Anything longer is
# silently truncated by some libs and outright rejected by bcrypt 4.x.
# We truncate explicitly so the behaviour is documented and tests can rely
# on it. The password-policy validator also caps NEW passwords at 72
# bytes so a user can't set one that would be silently truncated on set
# but rejected on the very next login.
_BCRYPT_MAX_BYTES = 72


def _truncate(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt."""
    return bcrypt.hashpw(_truncate(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Constant-time check that the password matches the stored hash."""
    try:
        return bcrypt.checkpw(_truncate(password), password_hash.encode("utf-8"))
    except ValueError:
        # Malformed hash in the DB — treat as a failed verification rather
        # than a 500. The user simply can't log in.
        return False


def create_access_token(user_id: uuid.UUID) -> tuple[str, int]:
    """Issue a JWT for the given user. Returns (token, expires_in_seconds).

    The payload carries a random `jti` in addition to the usual sub /
    iat / exp. HS256 signing is deterministic over the same payload,
    so without a nonce two tokens minted in the same second would be
    byte-identical (see e.g. login-then-change-password within one
    second). Distinct tokens matter for callers that compare strings,
    and this claim is also the natural surface for a future
    server-side revocation list.
    """
    expires_in = settings.jwt_access_token_expire_minutes * 60
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    token = jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    return token, expires_in


class DecodedToken:
    """Decoded JWT payload we care about: subject + issued-at."""

    __slots__ = ("user_id", "issued_at")

    def __init__(self, user_id: uuid.UUID, issued_at: datetime) -> None:
        self.user_id = user_id
        self.issued_at = issued_at


def decode_access_token(token: str) -> DecodedToken:
    """Decode a JWT and return the user_id + iat from its claims.

    Raises HTTPException(401) on any failure (expired, malformed, missing
    sub/iat, bad signature). Callers compare `issued_at` against the
    user's `password_changed_at` to enforce revocation-on-rotation.
    """
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    iat = payload.get("iat")
    if not isinstance(iat, int):
        raise HTTPException(status_code=401, detail="Invalid token payload")

    try:
        user_id = uuid.UUID(sub)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid token subject") from exc

    return DecodedToken(
        user_id=user_id,
        issued_at=datetime.fromtimestamp(iat, tz=timezone.utc),
    )


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    """Load a user with the tenant relationship eager-loaded."""
    result = await db.execute(
        select(User).options(selectinload(User.tenant)).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


# --- Login + lockout -----------------------------------------------------


class LoginResult(str, enum.Enum):
    """Outcome of an /auth/login attempt.

    OK — credentials verified, user is returned.
    INVALID — unknown email OR wrong password OR tenant inactive. The
      caller MUST NOT distinguish these to the client (existence leak).
    LOCKED — the account has too many recent failures. Response is
      still generic; the extra state only exists so we can attach a
      `Retry-After` header.
    """

    OK = "ok"
    INVALID = "invalid"
    LOCKED = "locked"


async def authenticate_user(
    db: AsyncSession, email: str, password: str
) -> tuple[LoginResult, User | None, int | None]:
    """Verify credentials with failed-login lockout applied.

    Returns a tuple:
      - LoginResult (OK / INVALID / LOCKED)
      - the User on OK, else None (never leak the row on failure)
      - retry_after_seconds on LOCKED, else None

    Side effects (all inside the caller's transaction; caller commits):
      - increments `failed_login_count` on a wrong-password miss and
        sets `locked_until` when the threshold is crossed;
      - on the first successful auth after a lock, clears both fields
        together with `last_login_at`.

    Never distinguishes "unknown email" from "wrong password" in the
    returned result — both are INVALID. LOCKED is only returned for a
    known email whose account is currently locked (revealing lock
    state for an unknown email would be its own existence leak).
    """
    result = await db.execute(
        select(User)
        .options(selectinload(User.tenant))
        .where(User.email == email.lower())
    )
    user = result.scalar_one_or_none()
    if user is None:
        return LoginResult.INVALID, None, None

    now = datetime.now(timezone.utc)
    if user.locked_until is not None and user.locked_until > now:
        retry_after = int((user.locked_until - now).total_seconds())
        return LoginResult.LOCKED, None, max(retry_after, 1)

    if not verify_password(password, user.password_hash):
        # Wrong password. Increment the counter; on the Nth miss, arm
        # the lock. We do this via a targeted UPDATE (not attribute
        # assignment) so the write is atomic even if the caller has a
        # stale copy of the row.
        new_count = user.failed_login_count + 1
        if new_count >= settings.login_lockout_threshold:
            locked_until = now + timedelta(
                minutes=settings.login_lockout_minutes
            )
            await db.execute(
                update(User)
                .where(User.id == user.id)
                .values(
                    failed_login_count=new_count,
                    locked_until=locked_until,
                )
            )
            retry_after = int((locked_until - now).total_seconds())
            return LoginResult.LOCKED, None, max(retry_after, 1)
        await db.execute(
            update(User)
            .where(User.id == user.id)
            .values(failed_login_count=new_count)
        )
        return LoginResult.INVALID, None, None

    if not user.tenant.is_active:
        # Correct password but the tenant is turned off. Do NOT clear
        # the failure counter — we're refusing this login. Return
        # INVALID so we don't leak tenant state to the client either.
        return LoginResult.INVALID, None, None

    # Success — clear any prior failure state and stamp last_login_at.
    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(
            last_login_at=now,
            failed_login_count=0,
            locked_until=None,
        )
    )
    return LoginResult.OK, user, None


# --- Password change -----------------------------------------------------


async def change_password(
    db: AsyncSession, user: User, new_password: str
) -> datetime:
    """Set a new password, bump `password_changed_at` to now.

    Callers must have already verified the user's current password.
    The returned timestamp is what the JWT `iat` check compares
    against — every session issued strictly before it is invalid
    after this call commits.

    The write is a targeted UPDATE so the ORM's `updated_at` also
    ticks and any concurrent copy of the row can't reintroduce the
    old hash.
    """
    now = datetime.now(timezone.utc)
    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(
            password_hash=hash_password(new_password),
            password_changed_at=now,
            # Rotate cancels any lock too — the account owner has just
            # proved control.
            failed_login_count=0,
            locked_until=None,
        )
    )
    return now
