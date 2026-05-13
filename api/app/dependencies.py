import uuid
from datetime import datetime, timezone

import bcrypt
import redis
from fastapi import Depends, HTTPException, Response, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.models.api_key import ApiKey
from app.models.tenant import Tenant
from app.models.user import User
from app.services.rate_limit_service import (
    check_and_increment,
    headers_for,
)

# One process-wide Redis client; redis-py is thread-safe and pools
# connections internally.
_rate_limit_redis = redis.from_url(settings.redis_url, decode_responses=True)

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


async def get_tenant_from_either(
    credentials: HTTPAuthorizationCredentials | None = Security(session_security),
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    """Resolve a tenant from either a lender API key (pk_*) or a dashboard JWT.

    Used on endpoints that appear in the public lender docs but are also
    consumed by the dashboard — currently analytics + config/weights. The
    `pk_` prefix is the cheap discriminator: API keys are minted with
    `pk_live_` / `pk_test_` prefixes, JWTs are dot-separated.
    """
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if credentials.credentials.startswith("pk_"):
        return await get_current_tenant(credentials, db)
    user = await get_current_user(credentials, db)
    return user.tenant


async def enforce_rate_limit(
    response: Response,
    tenant: Tenant = Depends(get_current_tenant),
) -> Tenant:
    """Enforce the per-tenant per-minute request limit defined by the
    tenant's plan tier and attach the standard `X-RateLimit-*` headers
    to the response (whether or not the request is rejected).

    Drop-in replacement for `get_current_tenant` on lender-facing API
    routes. Use this anywhere the public docs declare a 429 response.
    """
    result = check_and_increment(
        tenant.id, tenant.plan.value, _rate_limit_redis,
    )
    for k, v in headers_for(result).items():
        response.headers[k] = v
    if not result.allowed:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Rate limit exceeded ({result.limit} requests/min for "
                f"the {tenant.plan.value} plan). Retry in "
                f"{result.retry_after}s."
            ),
            headers={
                **headers_for(result),
                "Retry-After": str(result.retry_after),
            },
        )
    return tenant


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Restrict an endpoint to ADMIN-role users.

    Used by team management endpoints. Returns the user so the route handler
    can still access it via Depends(require_admin) instead of stacking deps.
    """
    from app.models.user import UserRole

    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin role required")
    return user
