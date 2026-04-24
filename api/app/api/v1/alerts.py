"""Alert endpoints — list, read, mark as read."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.alert_service import (
    get_unread_count,
    list_alerts,
    mark_alert_read,
    mark_all_read,
)

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("")
async def list_tenant_alerts(
    unread_only: bool = Query(False),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List alerts for the tenant, newest first."""
    alerts = await list_alerts(db, user.tenant_id, unread_only=unread_only, limit=limit)
    unread = await get_unread_count(db, user.tenant_id)
    return {"items": alerts, "unread_count": unread}


@router.patch("/{alert_id}/read")
async def mark_read(
    alert_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Mark a single alert as read."""
    found = await mark_alert_read(db, user.tenant_id, alert_id)
    if not found:
        raise HTTPException(status_code=404, detail="Alert not found")
    await db.commit()
    return {"status": "ok"}


@router.patch("/read-all")
async def mark_all_alerts_read(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Mark all alerts as read."""
    count = await mark_all_read(db, user.tenant_id)
    await db.commit()
    return {"marked_read": count}
