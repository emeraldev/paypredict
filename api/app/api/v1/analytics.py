"""Dashboard analytics endpoints."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.analytics import (
    AccuracyResponse,
    AnalyticsSummaryResponse,
    CollectionRateResponse,
    FactorsResponse,
)
from app.services.analytics_service import (
    get_accuracy,
    get_collection_rate,
    get_factor_contributions,
    get_summary,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummaryResponse)
async def summary(
    period: str = Query("30d", pattern="^(7d|14d|30d|60d|90d)$"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsSummaryResponse:
    """Aggregate analytics summary for the given period."""
    return await get_summary(db, user.tenant_id, period)


@router.get("/collection-rate", response_model=CollectionRateResponse)
async def collection_rate(
    period: str = Query("30d", pattern="^(7d|14d|30d|60d|90d)$"),
    interval: str = Query("daily", pattern="^(daily|weekly)$"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CollectionRateResponse:
    """Collection rate over time, bucketed by day or week."""
    return await get_collection_rate(db, user.tenant_id, period, interval)


@router.get("/factors", response_model=FactorsResponse)
async def factors(
    period: str = Query("30d", pattern="^(7d|14d|30d|60d|90d)$"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FactorsResponse:
    """Average factor contributions and correlation with failure."""
    return await get_factor_contributions(db, user.tenant_id, period)


@router.get("/accuracy", response_model=AccuracyResponse)
async def accuracy(
    period: str = Query("30d", pattern="^(7d|14d|30d|60d|90d)$"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AccuracyResponse:
    """Confusion matrix: predicted risk level vs actual outcome."""
    return await get_accuracy(db, user.tenant_id, period)
