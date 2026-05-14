"""Analytics endpoints — appear in the public lender docs and are also
consumed by the dashboard. Accept either an API key (lender) or a JWT
(dashboard) via the shared dual-auth dependency."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.docs_config import LENDER_API_RESPONSES
from app.database import get_db
from app.dependencies import enforce_rate_limit_or_jwt
from app.models.tenant import Tenant
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

router = APIRouter(prefix="/analytics", tags=["Analytics"], responses=LENDER_API_RESPONSES)


@router.get("/summary", response_model=AnalyticsSummaryResponse)
async def summary(
    period: str = Query("30d", pattern="^(7d|14d|30d|60d|90d)$"),
    tenant: Tenant = Depends(enforce_rate_limit_or_jwt),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsSummaryResponse:
    """Aggregate analytics summary for the given period."""
    return await get_summary(db, tenant.id, period)


@router.get("/collection-rate", response_model=CollectionRateResponse)
async def collection_rate(
    period: str = Query("30d", pattern="^(7d|14d|30d|60d|90d)$"),
    interval: str = Query("daily", pattern="^(daily|weekly)$"),
    tenant: Tenant = Depends(enforce_rate_limit_or_jwt),
    db: AsyncSession = Depends(get_db),
) -> CollectionRateResponse:
    """Collection rate over time, bucketed by day or week."""
    return await get_collection_rate(db, tenant.id, period, interval)


@router.get("/factors", response_model=FactorsResponse)
async def factors(
    period: str = Query("30d", pattern="^(7d|14d|30d|60d|90d)$"),
    tenant: Tenant = Depends(enforce_rate_limit_or_jwt),
    db: AsyncSession = Depends(get_db),
) -> FactorsResponse:
    """Average factor contributions and correlation with failure."""
    return await get_factor_contributions(db, tenant.id, period)


@router.get("/accuracy", response_model=AccuracyResponse)
async def accuracy(
    period: str = Query("30d", pattern="^(7d|14d|30d|60d|90d)$"),
    tenant: Tenant = Depends(enforce_rate_limit_or_jwt),
    db: AsyncSession = Depends(get_db),
) -> AccuracyResponse:
    """Confusion matrix: predicted risk level vs actual outcome."""
    return await get_accuracy(db, tenant.id, period)
