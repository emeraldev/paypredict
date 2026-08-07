"""Factor-weight helpers.

Central place for loading and persisting per-method factor weights so
scoring, bulk scoring, backtest, and the weights API don't diverge on
how they read the same table.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.factor_weight import FactorWeight
from app.models.score_request import CollectionMethod
from app.scoring.registry import (
    get_default_weights_for_method,
    get_factors_for_method,
)


async def get_custom_weights_for_method(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    method: CollectionMethod,
) -> dict[str, float]:
    """Return only the weights this tenant has explicitly saved for `method`.

    Empty dict when the tenant hasn't tuned this method yet — the engine
    treats an empty custom-weights dict as "use bundle defaults" for every
    factor.
    """
    result = await db.execute(
        select(FactorWeight).where(
            FactorWeight.tenant_id == tenant_id,
            FactorWeight.collection_method == method.value,
        )
    )
    return {w.factor_name: w.weight for w in result.scalars().all()}


async def get_effective_weights_for_method(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    method: CollectionMethod,
) -> dict[str, float]:
    """Return the full weight vector the engine would actually apply.

    Custom values override defaults; missing factors fall back to the
    bundle default. Handy for the weights API GET (so the dashboard sees
    every factor for the method even when nothing has been saved yet).
    """
    defaults = get_default_weights_for_method(method)
    custom = await get_custom_weights_for_method(db, tenant_id, method)
    return {**defaults, **custom}


async def load_all_weights_by_method(
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> dict[str, dict[str, float]]:
    """Load every custom weight for a tenant, bucketed by method value.

    Used by bulk scoring and backtest to amortise the query across many
    rows. Missing methods yield an empty inner dict → engine defaults.
    """
    result = await db.execute(
        select(FactorWeight).where(FactorWeight.tenant_id == tenant_id)
    )
    buckets: dict[str, dict[str, float]] = {}
    for w in result.scalars().all():
        buckets.setdefault(w.collection_method, {})[w.factor_name] = w.weight
    return buckets


async def upsert_weights_for_method(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    method: CollectionMethod,
    weights: dict[str, float],
    updated_by: uuid.UUID | None,
) -> None:
    """Replace the tenant's saved weights for `method` with `weights`.

    Only rows for THIS method are touched — a PUT that tunes CARD never
    perturbs the tenant's PAYROLL weights. Unknown factor names (not in
    the method's bundle) are rejected loudly rather than silently stored;
    that guarantee is what makes the weights API safe to trust.
    """
    valid = set(get_factors_for_method(method).keys())
    unknown = set(weights.keys()) - valid
    if unknown:
        raise ValueError(
            f"Unknown factor names for method {method.value}: {sorted(unknown)}"
        )

    existing = await db.execute(
        select(FactorWeight).where(
            FactorWeight.tenant_id == tenant_id,
            FactorWeight.collection_method == method.value,
        )
    )
    existing_rows = {row.factor_name: row for row in existing.scalars().all()}
    now = datetime.now(timezone.utc)

    for name, weight in weights.items():
        row = existing_rows.pop(name, None)
        if row is None:
            db.add(
                FactorWeight(
                    tenant_id=tenant_id,
                    collection_method=method.value,
                    factor_name=name,
                    weight=weight,
                    updated_by=updated_by,
                )
            )
        else:
            row.weight = weight
            row.updated_at = now
            row.updated_by = updated_by

    # Any pre-existing row for a factor not in the PUT is stale — drop it
    # rather than leave a mismatch between the tenant's UI state and the
    # persisted rows.
    for stale in existing_rows.values():
        await db.delete(stale)

    await db.flush()


async def list_configured_methods(
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> list[CollectionMethod]:
    """Return the set of methods this tenant should see tabs for.

    Rule: a method appears if the tenant has EITHER saved custom weights
    for it OR scored at least one collection with it. Keeps the UI free
    of tabs for methods the tenant doesn't use (a payroll-only lender
    sees one tab, not four).
    """
    from app.models.score_request import ScoreRequest

    weight_methods = await db.execute(
        select(FactorWeight.collection_method)
        .where(FactorWeight.tenant_id == tenant_id)
        .distinct()
    )
    score_methods = await db.execute(
        select(ScoreRequest.collection_method)
        .where(ScoreRequest.tenant_id == tenant_id)
        .distinct()
    )
    seen: set[str] = set()
    seen.update(str(row) for row in weight_methods.scalars().all())
    # ScoreRequest.collection_method is a PG enum; SQLAlchemy hands it back as
    # the enum member — normalise to its string value.
    for row in score_methods.scalars().all():
        seen.add(row.value if isinstance(row, CollectionMethod) else str(row))

    return [m for m in CollectionMethod if m.value in seen]
