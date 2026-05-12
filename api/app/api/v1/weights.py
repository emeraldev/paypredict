"""Factor weight configuration — appears in the public lender docs and is
also consumed by the dashboard. Accepts either an API key or a JWT.
When the caller is a dashboard user (JWT), a notification is created with
that user as the actor; API-key calls record the tenant name instead."""
from fastapi import APIRouter, Depends, Security
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import (
    get_current_user,
    get_tenant_from_either,
    session_security,
)
from app.models.factor_weight import FactorWeight
from app.models.tenant import Tenant
from app.models.user import User

router = APIRouter(prefix="/config", tags=["Configuration"])


@router.get("/weights")
async def get_weights(
    tenant: Tenant = Depends(get_tenant_from_either),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return the tenant's factor weights."""
    result = await db.execute(
        select(FactorWeight)
        .where(FactorWeight.tenant_id == tenant.id)
        .order_by(FactorWeight.factor_name)
    )
    weights = result.scalars().all()
    return {
        "factor_set": tenant.factor_set.value,
        "weights": [
            {"factor_name": w.factor_name, "weight": w.weight}
            for w in weights
        ],
    }


@router.put("/weights")
async def update_weights(
    body: dict,
    tenant: Tenant = Depends(get_tenant_from_either),
    credentials: HTTPAuthorizationCredentials | None = Security(session_security),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update the tenant's factor weights.

    Body: { "weights": { "factor_name": 0.25, ... } }
    """
    new_weights: dict[str, float] = body.get("weights", {})
    if not new_weights:
        return await get_weights(tenant=tenant, db=db)

    result = await db.execute(
        select(FactorWeight).where(FactorWeight.tenant_id == tenant.id)
    )
    existing = {w.factor_name: w for w in result.scalars().all()}

    # Identify the acting user when the call came in via JWT so the
    # notification has a real actor; API-key callers record the tenant.
    actor_user: User | None = None
    if credentials and not credentials.credentials.startswith("pk_"):
        actor_user = await get_current_user(credentials, db)

    for factor_name, weight in new_weights.items():
        if factor_name in existing:
            existing[factor_name].weight = weight
            existing[factor_name].updated_by = actor_user.id if actor_user else None

    await db.flush()

    from app.services.notification_service import EventType, create_notification
    await create_notification(
        db, tenant.id, EventType.WEIGHTS_UPDATED,
        metadata={"actor_name": actor_user.name if actor_user else "API key"},
        actor_id=actor_user.id if actor_user else None,
    )

    await db.commit()
    return await get_weights(tenant=tenant, db=db)
