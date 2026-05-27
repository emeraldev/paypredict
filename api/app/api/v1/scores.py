"""Score endpoints — single-score (lender, API key) + list/detail (dashboard, JWT).

Split by tag for OpenAPI grouping; the docs filter at the schema level keeps
the dashboard endpoints out of the public Swagger UI.
"""
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.docs_config import (
    DASHBOARD_API_RESPONSES,
    LENDER_API_RESPONSES,
    NOT_FOUND_RESPONSES,
)
from app.database import get_db
from app.dependencies import (
    enforce_rate_limit_or_jwt,
    get_current_user,
)
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.score import ScoreRequest, ScoreResponse
from app.schemas.scores_list import ScoreDetailResponse, ScoresListResponse
from app.services.bulk_scoring_service import score_bulk_sync
from app.services.csv_parser import parse_scoring_csv
from app.services.scores_service import get_score_detail, list_scores
from app.services.scoring_service import score_collection

router = APIRouter()

# Upload caps. 500 matches the backtest sync cap — these run through the
# bulk-score-sync path so they block the request, but at ~1ms per row a 500-row
# upload finishes in a couple of seconds. Larger files should use the async
# bulk endpoint (POST /v1/score/bulk).
MAX_UPLOAD_ROWS = 500
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB

# Header-only template. We deliberately do NOT ship example data rows —
# uploading an unmodified template would otherwise persist fake collections
# to the dashboard. Lenders see realistic example values in the "Example
# data" card on /dashboard/score for reference.
SCORING_CSV_TEMPLATE = (
    # Required columns
    "customer_id,collection_id,collection_amount,collection_currency,"
    "collection_due_date,collection_method,"
    # Common optional (apply to both factor sets)
    "total_payments,successful_payments,last_successful_payment_date,"
    "average_collection_amount,instalment_number,total_instalments,"
    # CARD_DEBIT optional
    "card_type,card_expiry,last_decline_code,debit_order_returns,known_salary_day,"
    # MOBILE_WALLET optional
    "wallet_balance_7d_avg,wallet_balance_current,hours_since_last_inflow,"
    "regular_inflow_day,active_loan_count,transactions_last_7d,transactions_avg_7d,"
    "last_airtime_purchase_days_ago,new_loan_within_repayment_period,loans_taken_last_90d\n"
)


# ---- Lender-facing (API key auth) -------------------------------------------


@router.post(
    "/score",
    response_model=ScoreResponse,
    tags=["Scoring"],
    responses=LENDER_API_RESPONSES,
)
async def score_single_collection(
    request: ScoreRequest,
    # Dual-auth: API key (rate-limited, same as before) OR dashboard JWT
    # (rate-limit-bypassed, used by the single-collection form on
    # /dashboard/score). Same pattern as /v1/analytics/* and /v1/config/weights.
    tenant: Tenant = Depends(enforce_rate_limit_or_jwt),
    db: AsyncSession = Depends(get_db),
) -> ScoreResponse:
    """Score a single upcoming collection. Returns risk score, level, and factor breakdown."""
    return await score_collection(request, tenant, db)


# ---- Dashboard-facing (JWT session auth) ------------------------------------


@router.get(
    "/scores",
    response_model=ScoresListResponse,
    tags=["Dashboard Scores"],
    responses=DASHBOARD_API_RESPONSES,
)
async def scores_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    risk_level: str | None = Query(None, pattern="^(HIGH|MEDIUM|LOW)$"),
    collection_method: str | None = Query(
        None, pattern="^(CARD|DEBIT_ORDER|MOBILE_MONEY)$"
    ),
    recommended_action: str | None = Query(
        None,
        pattern="^(collect_normally|pre_collection_sms|flag_for_review|shift_date)$",
    ),
    due_date_from: date | None = None,
    due_date_to: date | None = None,
    search: str | None = None,
    sort_by: str = Query(
        "score",
        pattern="^(score|collection_amount|collection_due_date|created_at|customer_id|collection_method)$",
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
        recommended_action=recommended_action,
        due_date_from=due_date_from,
        due_date_to=due_date_to,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )


# CSV upload routes declared BEFORE /scores/{score_id} so FastAPI doesn't try to
# parse "upload" as a UUID (which would 422 instead of falling through).


@router.post(
    "/scores/upload",
    status_code=status.HTTP_201_CREATED,
    tags=["Dashboard Scores"],
    responses=DASHBOARD_API_RESPONSES,
)
async def upload_and_score(
    file: UploadFile,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Upload a CSV of upcoming collections and score each row.

    Validation errors are returned in the response body (200-shape `errors`
    list with row numbers). When all rows are valid the rows are scored,
    persisted to the score tables, and the bulk-score response shape is
    returned — the rows then appear on the main dashboard.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv file")

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large (max {MAX_UPLOAD_BYTES // (1024 * 1024)} MB)",
        )

    items, errors = parse_scoring_csv(content)

    if errors:
        # Same shape as the backtest upload error response so the frontend
        # error-rendering component can be reused.
        return {"errors": [e.model_dump() for e in errors]}

    if not items:
        raise HTTPException(
            status_code=400,
            detail=(
                "CSV contains no data rows. Add at least one row of "
                "collection data under the header."
            ),
        )

    if len(items) > MAX_UPLOAD_ROWS:
        raise HTTPException(
            status_code=413,
            detail=f"CSV contains {len(items)} rows (max {MAX_UPLOAD_ROWS}).",
        )

    collections = [item.model_dump(mode="python") for item in items]
    result = await score_bulk_sync(db, user.tenant, collections)
    await db.commit()
    return result


@router.get(
    "/scores/upload/template",
    tags=["Dashboard Scores"],
    response_class=StreamingResponse,
)
async def download_scoring_template() -> StreamingResponse:
    """Download a CSV template for the scoring upload endpoint."""
    return StreamingResponse(
        iter([SCORING_CSV_TEMPLATE]),
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                'attachment; filename="paypredict_scoring_template.csv"'
            )
        },
    )


@router.get(
    "/scores/{score_id}",
    response_model=ScoreDetailResponse,
    tags=["Dashboard Scores"],
    responses={**DASHBOARD_API_RESPONSES, **NOT_FOUND_RESPONSES},
)
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
