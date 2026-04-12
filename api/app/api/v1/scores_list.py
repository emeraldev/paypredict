"""Dashboard scores list + detail endpoints."""
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.scores_list import ScoreDetailResponse, ScoresListResponse
from app.services.scores_service import get_score_detail, list_scores

router = APIRouter(tags=["scores"])


@router.get("/scores", response_model=ScoresListResponse)
async def scores_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    risk_level: str | None = Query(None, pattern="^(HIGH|MEDIUM|LOW)$"),
    collection_method: str | None = Query(
        None, pattern="^(CARD|DEBIT_ORDER|MOBILE_MONEY)$"
    ),
    due_date_from: date | None = None,
    due_date_to: date | None = None,
    search: str | None = None,
    sort_by: str = Query(
        "score",
        pattern="^(score|collection_amount|collection_due_date|created_at)$",
    ),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScoresListResponse:
    """List scored collections for the dashboard table.

    Returns paginated items + summary counts over the full filtered dataset.
    """
    return await list_scores(
        db,
        user.tenant_id,
        page=page,
        page_size=page_size,
        risk_level=risk_level,
        collection_method=collection_method,
        due_date_from=due_date_from,
        due_date_to=due_date_to,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get("/scores/{score_id}", response_model=ScoreDetailResponse)
async def score_detail(
    score_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScoreDetailResponse:
    """Load a single score with factor breakdown, customer context, and
    linked outcome for the risk-detail drawer."""
    result = await get_score_detail(db, user.tenant_id, score_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Score not found")
    return result
