"""Dashboard auth service.

Handles password hashing, JWT issuance/decoding, and user lookup for the
dashboard session-auth endpoints. Uses `bcrypt` directly (the project
already depends on it for API-key hashing) and `python-jose` for JWT.
"""
from __future__ import annotations

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
# on it. 72 bytes is plenty for any human password.
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
    """Issue a JWT for the given user. Returns (token, expires_in_seconds)."""
    expires_in = settings.jwt_access_token_expire_minutes * 60
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
    }
    token = jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    return token, expires_in


def decode_access_token(token: str) -> uuid.UUID:
    """Decode a JWT and return the user_id from the `sub` claim.

    Raises HTTPException(401) on any failure (expired, malformed, missing sub,
    bad signature). The dashboard endpoints rely on this to enforce auth.
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

    try:
        return uuid.UUID(sub)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid token subject") from exc


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    """Load a user with the tenant relationship eager-loaded."""
    result = await db.execute(
        select(User).options(selectinload(User.tenant)).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def authenticate_user(
    db: AsyncSession, email: str, password: str
) -> User | None:
    """Look up a user by email and verify the password.

    Returns the user with `tenant` eager-loaded on success, `None` on any
    auth failure (unknown email OR wrong password). The caller must NOT
    distinguish between those cases when reporting errors — that would leak
    which emails exist on the platform.
    """
    result = await db.execute(
        select(User)
        .options(selectinload(User.tenant))
        .where(User.email == email.lower())
    )
    user = result.scalar_one_or_none()
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    if not user.tenant.is_active:
        return None
    return user


async def touch_last_login(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Update last_login_at to now (best-effort, fire-and-forget)."""
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(last_login_at=datetime.now(timezone.utc))
    )
