"""Dashboard team management endpoints (admin-only)."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.docs_config import DASHBOARD_ADMIN_RESPONSES, NOT_FOUND_RESPONSES
from app.database import get_db
from app.dependencies import require_admin
from app.models.user import User
from app.schemas.config import (
    TeamInviteRequest,
    TeamListResponse,
    TeamMemberItem,
    TeamUpdateRequest,
)
from app.services.activity_audit_service import (
    actor_from_user,
    log_activity,
)
from app.services.config_service import (
    invite_member,
    list_team,
    remove_member,
    update_member_role,
)

router = APIRouter(
    prefix="/config/team",
    tags=["Team"],
    responses={**DASHBOARD_ADMIN_RESPONSES, **NOT_FOUND_RESPONSES},
)


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
    await log_activity(
        db,
        tenant_id=user.tenant_id,
        entity_type="user",
        entity_id=result.id,
        action="create",
        before=None,
        after={"name": result.name, "email": result.email, "role": result.role.value},
        actor=actor_from_user(user),
        context="team_invite",
    )
    from app.services.notification_service import EventType, create_notification
    await create_notification(
        db, user.tenant_id, EventType.TEAM_MEMBER_INVITED,
        metadata={"actor_name": user.name, "invitee_name": req.name, "invitee_role": req.role.value},
        actor_id=user.id,
    )
    await db.commit()
    return result


@router.patch("/{user_id}", response_model=TeamMemberItem)
async def update_role(
    user_id: UUID,
    req: TeamUpdateRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> TeamMemberItem:
    # Capture the old role BEFORE the mutation so the audit shows the
    # actual diff, not just "role: NEW".
    target = (await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == user.tenant_id)
    )).scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    old_role = target.role.value

    result = await update_member_role(db, user.tenant_id, user_id, req)
    if old_role != result.role.value:
        await log_activity(
            db,
            tenant_id=user.tenant_id,
            entity_type="user",
            entity_id=result.id,
            action="update",
            before={"role": old_role},
            after={"role": result.role.value},
            actor=actor_from_user(user),
            context="role_change",
        )
    await db.commit()
    return result


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove(
    user_id: UUID,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    # Snapshot BEFORE the delete so the log preserves who was removed.
    target = (await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == user.tenant_id)
    )).scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    before = {
        "name": target.name,
        "email": target.email,
        "role": target.role.value,
    }

    await remove_member(db, user.tenant_id, user_id)
    await log_activity(
        db,
        tenant_id=user.tenant_id,
        entity_type="user",
        entity_id=user_id,
        action="delete",
        before=before,
        after=None,
        actor=actor_from_user(user),
        context="team_remove",
    )
    await db.commit()
