import uuid
from datetime import datetime, timezone

import bcrypt
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.api_key import ApiKey
from app.models.tenant import Tenant
from app.models.user import User

security = HTTPBearer()
session_security = HTTPBearer(auto_error=False)


async def get_current_tenant(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    """Validate API key and resolve to a tenant."""
    token = credentials.credentials

    # Extract prefix (first 8 chars) for fast lookup
    if len(token) < 8:
        raise HTTPException(status_code=401, detail="Invalid API key")

    key_prefix = token[:8]

    # Look up candidate keys by prefix
    result = await db.execute(
        select(ApiKey)
        .options(selectinload(ApiKey.tenant))
        .where(ApiKey.key_prefix == key_prefix, ApiKey.is_active.is_(True))
    )
    candidates = result.scalars().all()

    if not candidates:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Verify hash against each candidate (usually just one)
    matched_key: ApiKey | None = None
    for api_key in candidates:
        if bcrypt.checkpw(token.encode("utf-8"), api_key.key_hash.encode("utf-8")):
            matched_key = api_key
            break

    if matched_key is None:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Check tenant is active
    tenant = matched_key.tenant
    if not tenant.is_active:
        raise HTTPException(status_code=401, detail="Tenant is deactivated")

    # Update last_used_at (fire-and-forget, don't fail the request)
    await db.execute(
        update(ApiKey)
        .where(ApiKey.id == matched_key.id)
        .values(last_used_at=datetime.now(timezone.utc))
    )

    return tenant


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(session_security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the dashboard user from a session JWT.

    Validates the bearer token issued by POST /v1/auth/login, loads the
    user from the DB with the tenant relationship eager-loaded, and refuses
    requests for users whose tenant has been deactivated.
    """
    # Lazy import to avoid circular dependency: auth_service uses some of
    # the same DB models, and dependencies.py is imported by main.
    from app.services.auth_service import decode_access_token, get_user_by_id

    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = decode_access_token(credentials.credentials)
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.tenant.is_active:
        raise HTTPException(status_code=401, detail="Tenant is deactivated")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Restrict an endpoint to ADMIN-role users.

    Used by team management endpoints. Returns the user so the route handler
    can still access it via Depends(require_admin) instead of stacking deps.
    """
    from app.models.user import UserRole

    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin role required")
    return user
