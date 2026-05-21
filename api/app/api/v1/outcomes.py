"""Outcome endpoints — report (lender, API key) + list (dashboard, JWT).

Split by tag for OpenAPI grouping; the docs filter at the schema level keeps
the dashboard endpoint out of the public Swagger UI.
"""
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.docs_config import DASHBOARD_API_RESPONSES, LENDER_API_RESPONSES
from app.database import get_db
from app.dependencies import enforce_rate_limit, get_current_user
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.outcome import OutcomeRequest, OutcomeResponse
from app.schemas.outcomes_list import OutcomesListResponse
from app.services.outcome_service import record_outcome
from app.services.outcomes_service import list_outcomes

router = APIRouter()


# ---- Lender-facing (API key auth) -------------------------------------------


@router.post(
    "/outcomes",
    response_model=OutcomeResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Outcomes"],
    responses=LENDER_API_RESPONSES,
)
async def report_outcome(
    request: OutcomeRequest,
    tenant: Tenant = Depends(enforce_rate_limit),
    db: AsyncSession = Depends(get_db),
) -> OutcomeResponse:
    """Report the result of a collection attempt."""
    return await record_outcome(request, tenant, db)


# ---- Dashboard-facing (JWT session auth) ------------------------------------


@router.get(
    "/outcomes",
    response_model=OutcomesListResponse,
    tags=["Dashboard Outcomes"],
    responses=DASHBOARD_API_RESPONSES,
)
async def outcomes_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    outcome: str | None = Query(None, pattern="^(SUCCESS|FAILED)$"),
    match: str | None = Query(None, pattern="^(MATCHED|MISMATCHED)$"),
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    sort_by: str = Query(
        "attempted_at",
        pattern="^(attempted_at|score|collection_amount)$",
    ),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OutcomesListResponse:
    """List outcomes with prediction match indicators and aggregate stats.

    Stats reflect the full filtered dataset, not just the current page.
    """
    return await list_outcomes(
        db,
        user.tenant_id,
        page=page,
        page_size=page_size,
        outcome_status=outcome,
        match_filter=match,
        search=search,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        sort_order=sort_order,
    )
