"""Append + read helpers for the weight_change_log table.

Separate from `weights_service` so the audit layer can be reused from
anywhere weights are mutated (upsert, add-method, future backfill
scripts) and the read path stays isolated from the write path.

Every write happens inside the same DB transaction as the actual
weight mutation — the log and the state can never diverge. Callers
must NOT commit around this function; the endpoint's `db.commit()`
covers both.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.score_request import CollectionMethod
from app.models.weight_change_log import WeightChangeActorType, WeightChangeLog


@dataclass
class WeightChangeActor:
    """Normalised actor descriptor for the audit log.

    `type` is required; `id` is null for API-key actors when we choose
    not to link the key row (audit stays readable if the key is later
    revoked), and null for system actors. `name` is denormalized so
    the log row stays useful even if the user/key is later removed.
    """
    type: WeightChangeActorType
    id: uuid.UUID | None
    name: str | None


async def log_weight_change(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    method: CollectionMethod,
    factor_name: str,
    old_weight: float | None,
    new_weight: float | None,
    actor: WeightChangeActor,
    context: str | None = None,
) -> None:
    """Append one row to the audit log.

    No-op guard: if old == new (nothing actually changed) we still
    write, because the intent to save is itself audit-worthy — a
    curious admin will want to see "someone re-saved the same value
    at this timestamp." Callers that want to skip no-op writes can
    check before calling.
    """
    db.add(
        WeightChangeLog(
            tenant_id=tenant_id,
            collection_method=method.value,
            factor_name=factor_name,
            old_weight=old_weight,
            new_weight=new_weight,
            actor_type=actor.type,
            actor_id=actor.id,
            actor_name=actor.name,
            context=context,
        )
    )
    await db.flush()


async def list_weight_changes(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    limit: int = 25,
    offset: int = 0,
    collection_method: CollectionMethod | None = None,
    factor_name: str | None = None,
) -> tuple[Sequence[WeightChangeLog], int]:
    """Paginated read for the dashboard's Change History table.

    Returns (rows, total_count). Ordered most-recent first.
    """
    filters = [WeightChangeLog.tenant_id == tenant_id]
    if collection_method is not None:
        filters.append(WeightChangeLog.collection_method == collection_method.value)
    if factor_name is not None:
        filters.append(WeightChangeLog.factor_name == factor_name)

    count_stmt = select(func.count()).select_from(WeightChangeLog).where(*filters)
    total = (await db.execute(count_stmt)).scalar_one()

    rows_stmt = (
        select(WeightChangeLog)
        .where(*filters)
        .order_by(WeightChangeLog.changed_at.desc(), WeightChangeLog.id.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = (await db.execute(rows_stmt)).scalars().all()

    return rows, total
