"""Dashboard outcomes list endpoint."""
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.outcomes_list import OutcomesListResponse
from app.services.outcomes_service import list_outcomes

router = APIRouter(tags=["outcomes"])


@router.get("/outcomes", response_model=OutcomesListResponse)
async def outcomes_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    outcome: str | None = Query(None, pattern="^(SUCCESS|FAILED)$"),
    match: str | None = Query(None, pattern="^(MATCHED|MISMATCHED)$"),
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
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        sort_order=sort_order,
    )
