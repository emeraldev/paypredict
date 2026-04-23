"""Dashboard alert configuration endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.config import AlertsConfigResponse, AlertsConfigUpdateRequest
from app.services.config_service import get_alerts_config, update_alerts_config

router = APIRouter(prefix="/config/alerts", tags=["config"])


@router.get("", response_model=AlertsConfigResponse)
async def get_config(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AlertsConfigResponse:
    return await get_alerts_config(db, user.tenant_id)


@router.put("", response_model=AlertsConfigResponse)
async def update_config(
    req: AlertsConfigUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AlertsConfigResponse:
    result = await update_alerts_config(db, user.tenant_id, req)
    await db.commit()
    return result
