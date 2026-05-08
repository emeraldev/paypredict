"""Dashboard API key management endpoints."""
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.config import (
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeyListItem,
    ApiKeyListResponse,
    ApiKeyToggleRequest,
)
from app.services.config_service import (
    create_api_key,
    delete_api_key,
    list_api_keys,
    toggle_api_key,
)

router = APIRouter(prefix="/config/api-keys", tags=["config"])


@router.get("", response_model=ApiKeyListResponse)
async def list_keys(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyListResponse:
    return await list_api_keys(db, user.tenant_id)


@router.post("", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_key(
    req: ApiKeyCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyCreateResponse:
    result = await create_api_key(db, user.tenant_id, req)
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
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyListItem:
    result = await toggle_api_key(db, user.tenant_id, key_id, req)
    await db.commit()
    return result


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_key(
    key_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    # Get the key label before deleting for the notification
    from sqlalchemy import select as sa_select
    from app.models.api_key import ApiKey
    key_result = await db.execute(sa_select(ApiKey).where(ApiKey.id == key_id, ApiKey.tenant_id == user.tenant_id))
    key_obj = key_result.scalar_one_or_none()
    key_label = key_obj.label if key_obj else "Unknown"

    await delete_api_key(db, user.tenant_id, key_id)
    from app.services.notification_service import EventType, create_notification
    await create_notification(
        db, user.tenant_id, EventType.API_KEY_REVOKED,
        metadata={"actor_name": user.name, "key_label": key_label},
        actor_id=user.id,
    )
    await db.commit()
