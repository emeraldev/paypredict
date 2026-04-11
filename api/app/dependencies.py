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

    Phase 2.5 placeholder: this will validate the JWT issued by
    POST /v1/auth/login (Phase 2 of the dashboard-endpoints branch). Until
    that lands, any caller of a dashboard endpoint gets a clear 501 — we
    do NOT want a silent fallback that leaks data across tenants.
    """
    raise HTTPException(
        status_code=501,
        detail="Dashboard session auth not implemented yet (Phase 2.5 step 2)",
    )
