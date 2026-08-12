"""Dashboard activity-audit read endpoint (admin-only).

Sister to `GET /v1/config/weights/history`. Reads the generic
`activity_log` table populated by team / api_keys / alerts_config /
outcomes mutations. Weight changes stay on their dedicated
history endpoint (finer-grained per-factor value diffs).
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_admin
from app.models.user import User
from app.schemas.config import ActivityLogEntry, ActivityLogResponse
from app.services.activity_audit_service import list_activity

# Internal-only tag — same trick weights.history_router uses so this
# endpoint stays out of the public Swagger UI (which filters by tag).
router = APIRouter(prefix="/config", tags=["Activity"])


@router.get("/activity", response_model=ActivityLogResponse)
async def list_tenant_activity(
    entity_type: str | None = Query(
        None,
        description=(
            "Filter to one entity type: `user`, `api_key`, "
            "`alert_config`, `webhook_secret`, `outcome`."
        ),
    ),
    action: str | None = Query(
        None,
        description=(
            "Filter to one action: `create`, `update`, `delete`, "
            "`revoke`, `activate`, `deactivate`, `rotate`."
        ),
    ),
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ActivityLogResponse:
    """Paginated tenant audit trail. Admin-only.

    Every team / API key / alerts config / webhook-secret /
    outcome-delete mutation lands here. Ordered most-recent-first.
    """
    rows, total = await list_activity(
        db,
        user.tenant_id,
        limit=limit,
        offset=offset,
        entity_type=entity_type,
        action=action,
    )
    items = [
        ActivityLogEntry(
            id=row.id,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            action=row.action,
            before=row.before,
            after=row.after,
            actor_type=row.actor_type.value,
            actor_name=row.actor_name,
            context=row.context,
            created_at=row.created_at,
        )
        for row in rows
    ]
    return ActivityLogResponse(
        items=items, total=total, limit=limit, offset=offset
    )
