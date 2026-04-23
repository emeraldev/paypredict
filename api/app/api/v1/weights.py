"""Dashboard weights configuration endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.factor_weight import FactorWeight
from app.models.user import User

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/weights")
async def get_weights(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return the tenant's factor weights."""
    result = await db.execute(
        select(FactorWeight)
        .where(FactorWeight.tenant_id == user.tenant_id)
        .order_by(FactorWeight.factor_name)
    )
    weights = result.scalars().all()
    return {
        "factor_set": user.tenant.factor_set.value,
        "weights": [
            {"factor_name": w.factor_name, "weight": w.weight}
            for w in weights
        ],
    }


@router.put("/weights")
async def update_weights(
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update the tenant's factor weights.

    Body: { "weights": { "factor_name": 0.25, ... } }
    """
    new_weights: dict[str, float] = body.get("weights", {})
    if not new_weights:
        return await get_weights(user=user, db=db)

    result = await db.execute(
        select(FactorWeight).where(FactorWeight.tenant_id == user.tenant_id)
    )
    existing = {w.factor_name: w for w in result.scalars().all()}

    for factor_name, weight in new_weights.items():
        if factor_name in existing:
            existing[factor_name].weight = weight
            existing[factor_name].updated_by = user.id

    await db.commit()
    return await get_weights(user=user, db=db)
