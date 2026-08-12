"""Append + read helpers for the activity_log table.

Complements `weight_audit_service` (which stays dedicated to
per-factor weight-value diffs). This service covers every OTHER
tenant-config mutation an auditor asks about: team CRUD, API key
CRUD, alert config, webhook-secret rotation, outcome soft-deletion.

Every write happens inside the same DB transaction as the actual
mutation — the log and the state can never diverge. Callers must
NOT commit around `log_activity`; the endpoint's `db.commit()`
covers both.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_log import ActivityActorType, ActivityLog


@dataclass
class ActivityActor:
    """Normalised actor descriptor for the activity log.

    Shape matches `WeightChangeActor` on purpose — same semantic
    (who did this?) but scoped to a different table. Denormalized
    `name` keeps the entry readable even if the user is later
    removed; FK-less `id` keeps the audit intact under that event.
    """
    type: ActivityActorType
    id: uuid.UUID | None
    name: str | None


async def log_activity(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    entity_type: str,
    entity_id: uuid.UUID | None,
    action: str,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
    actor: ActivityActor,
    context: str | None = None,
) -> None:
    """Append one row to the activity log.

    Same-transaction guarantee: the caller's endpoint holds the
    session; this helper only `db.add()` + `db.flush()`. The final
    commit happens at the endpoint layer alongside the mutation
    itself, so state and audit land atomically or both roll back.

    `before` and `after` should be SMALL dicts of the fields that
    meaningfully changed. Do NOT dump full ORM rows here (bulky
    JSONB is expensive to read, and dumps often carry PII fields
    that oughtn't hit the audit surface).
    """
    db.add(
        ActivityLog(
            tenant_id=tenant_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            before=before,
            after=after,
            actor_type=actor.type,
            actor_id=actor.id,
            actor_name=actor.name,
            context=context,
        )
    )
    await db.flush()


async def list_activity(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    limit: int = 25,
    offset: int = 0,
    entity_type: str | None = None,
    action: str | None = None,
) -> tuple[Sequence[ActivityLog], int]:
    """Paginated read for the dashboard's Activity tab.

    Returns (rows, total_count). Ordered most-recent first.
    """
    filters = [ActivityLog.tenant_id == tenant_id]
    if entity_type is not None:
        filters.append(ActivityLog.entity_type == entity_type)
    if action is not None:
        filters.append(ActivityLog.action == action)

    count_stmt = select(func.count()).select_from(ActivityLog).where(*filters)
    total = (await db.execute(count_stmt)).scalar_one()

    rows_stmt = (
        select(ActivityLog)
        .where(*filters)
        .order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = (await db.execute(rows_stmt)).scalars().all()
    return rows, total


def actor_from_user(user) -> ActivityActor:
    """Helper for endpoints that resolve auth as a `User` (JWT path).

    Every dashboard mutation site follows the same pattern:
    `actor = actor_from_user(user)` at the top of the handler.
    """
    return ActivityActor(
        type=ActivityActorType.USER,
        id=user.id,
        name=user.name,
    )
