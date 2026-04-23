"""Dashboard team management endpoints (admin-only)."""
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_admin
from app.models.user import User
from app.schemas.config import (
    TeamInviteRequest,
    TeamListResponse,
    TeamMemberItem,
    TeamUpdateRequest,
)
from app.services.config_service import (
    invite_member,
    list_team,
    remove_member,
    update_member_role,
)

router = APIRouter(prefix="/config/team", tags=["config"])


@router.get("", response_model=TeamListResponse)
async def list_members(
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> TeamListResponse:
    return await list_team(db, user.tenant_id)


@router.post("", response_model=TeamMemberItem, status_code=status.HTTP_201_CREATED)
async def invite(
    req: TeamInviteRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> TeamMemberItem:
    result = await invite_member(db, user.tenant_id, req)
    await db.commit()
    return result


@router.patch("/{user_id}", response_model=TeamMemberItem)
async def update_role(
    user_id: UUID,
    req: TeamUpdateRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> TeamMemberItem:
    result = await update_member_role(db, user.tenant_id, user_id, req)
    await db.commit()
    return result


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove(
    user_id: UUID,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    await remove_member(db, user.tenant_id, user_id)
    await db.commit()
