"""Dashboard API key management endpoints."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.docs_config import DASHBOARD_API_RESPONSES, NOT_FOUND_RESPONSES
from app.database import get_db
from app.dependencies import get_current_user, require_admin
from app.models.api_key import ApiKey
from app.models.user import User
from app.schemas.config import (
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeyListItem,
    ApiKeyListResponse,
    ApiKeyToggleRequest,
)
from app.services.activity_audit_service import (
    actor_from_user,
    log_activity,
)
from app.services.config_service import (
    create_api_key,
    delete_api_key,
    list_api_keys,
    toggle_api_key,
)

router = APIRouter(
    prefix="/config/api-keys",
    tags=["API Keys"],
    responses={**DASHBOARD_API_RESPONSES, **NOT_FOUND_RESPONSES},
)


@router.get("", response_model=ApiKeyListResponse)
async def list_keys(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyListResponse:
    return await list_api_keys(db, user.tenant_id)


@router.post("", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_key(
    req: ApiKeyCreateRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyCreateResponse:
    result = await create_api_key(db, user.tenant_id, req)
    await log_activity(
        db,
        tenant_id=user.tenant_id,
        entity_type="api_key",
        entity_id=result.id,
        action="create",
        before=None,
        # Persist the display prefix + label — never the raw key.
        after={"label": result.label, "prefix": result.prefix, "is_active": True},
        actor=actor_from_user(user),
        context="api_key_create",
    )
    from app.services.notification_service import EventType, create_notification
    await create_notification(
        db, user.tenant_id, EventType.API_KEY_CREATED,
        metadata={"actor_name": user.name, "key_label": req.label},
        actor_id=user.id,
    )
    await db.commit()
    return result


@router.patch("/{key_id}", response_model=ApiKeyListItem)
async def update_key(
    key_id: UUID,
    req: ApiKeyToggleRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyListItem:
    # Capture the old active state BEFORE the toggle so the log shows
    # the true transition. `activate` vs `deactivate` action so filters
    # can pull just deactivations without parsing the diff.
    target = (await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.tenant_id == user.tenant_id)
    )).scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="API key not found")
    old_active = target.is_active
    label = target.label
    prefix = target.key_prefix

    result = await toggle_api_key(db, user.tenant_id, key_id, req)
    if old_active != result.is_active:
        await log_activity(
            db,
            tenant_id=user.tenant_id,
            entity_type="api_key",
            entity_id=result.id,
            action="activate" if result.is_active else "deactivate",
            before={"label": label, "prefix": prefix, "is_active": old_active},
            after={"label": result.label, "prefix": prefix, "is_active": result.is_active},
            actor=actor_from_user(user),
            context="api_key_toggle",
        )
    await db.commit()
    return result


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_key(
    key_id: UUID,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    # Snapshot BEFORE the delete so the audit preserves label + prefix.
    # Never log the raw key — that column only ever held the bcrypt hash.
    target = (await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.tenant_id == user.tenant_id)
    )).scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="API key not found")
    key_label = target.label
    key_prefix = target.key_prefix
    was_active = target.is_active

    await delete_api_key(db, user.tenant_id, key_id)
    await log_activity(
        db,
        tenant_id=user.tenant_id,
        entity_type="api_key",
        entity_id=key_id,
        action="revoke",
        before={"label": key_label, "prefix": key_prefix, "is_active": was_active},
        after=None,
        actor=actor_from_user(user),
        context="api_key_revoke",
    )
    from app.services.notification_service import EventType, create_notification
    await create_notification(
        db, user.tenant_id, EventType.API_KEY_REVOKED,
        metadata={"actor_name": user.name, "key_label": key_label},
        actor_id=user.id,
    )
    await db.commit()
