"""Notification endpoints — bell dropdown, mark read."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.notification_service import (
    get_unread_count,
    list_notifications,
    mark_all_read,
    mark_as_read,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("")
async def list_all(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    category: str | None = Query(None, pattern="^(SYSTEM|ACTIVITY)$"),
    severity: str | None = Query(None, pattern="^(CRITICAL|WARNING|INFO)$"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    items, pagination, unread = await list_notifications(
        db,
        user.tenant_id,
        page=page,
        page_size=page_size,
        unread_only=unread_only,
        category=category,
        severity=severity,
    )
    return {
        "items": items,
        "pagination": pagination.model_dump(),
        "unread_count": unread,
    }


@router.get("/unread-count")
async def unread_count(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    count = await get_unread_count(db, user.tenant_id)
    return {"unread_count": count}


@router.patch("/{notification_id}/read")
async def mark_read(
    notification_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    found = await mark_as_read(db, user.tenant_id, notification_id, user.id)
    if not found:
        raise HTTPException(status_code=404, detail="Notification not found")
    await db.commit()
    return {"status": "ok"}


@router.post("/read-all")
async def read_all(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    count = await mark_all_read(db, user.tenant_id, user.id)
    await db.commit()
    return {"marked_read": count}
