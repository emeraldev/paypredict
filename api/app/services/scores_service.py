"""Dashboard scores list + detail service.

Joins ScoreRequest + ScoreResult (and optionally Outcome) for the dashboard
collections table and the risk-detail drawer.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Select, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.outcome import Outcome
from app.models.score_request import ScoreRequest
from app.models.score_result import RiskLevel, ScoreResult
from app.schemas.score import FactorBreakdown
from app.schemas.scores_list import (
    CustomerContext,
    OutcomeSummary,
    ScoreDetailResponse,
    ScoreListItem,
    ScoresListResponse,
    ScoresSummary,
)
from app.services.query_utils import PaginationMeta, paginate


# ---- Shared base query ----

def _base_query(tenant_id: uuid.UUID) -> Select:
    """ScoreRequest ← ScoreResult join, filtered to tenant."""
    return (
        select(ScoreRequest, ScoreResult)
        .join(ScoreResult, ScoreResult.score_request_id == ScoreRequest.id)
        .where(ScoreRequest.tenant_id == tenant_id)
    )


# ---- List ----

_SORT_COLUMNS = {
    "score": ScoreResult.score,
    "collection_amount": ScoreRequest.collection_amount,
    "collection_due_date": ScoreRequest.collection_due_date,
    "created_at": ScoreResult.created_at,
}


def _apply_filters(
    query: Select,
    *,
    risk_level: str | None,
    collection_method: str | None,
    due_date_from: date | None,
    due_date_to: date | None,
    search: str | None,
) -> Select:
    if risk_level:
        query = query.where(ScoreResult.risk_level == RiskLevel(risk_level))
    if collection_method:
        query = query.where(ScoreRequest.collection_method == collection_method)
    if due_date_from:
        query = query.where(ScoreRequest.collection_due_date >= due_date_from)
    if due_date_to:
        query = query.where(ScoreRequest.collection_due_date <= due_date_to)
    if search:
        pattern = f"%{search}%"
        query = query.where(
            ScoreRequest.external_customer_id.ilike(pattern)
            | ScoreRequest.external_collection_id.ilike(pattern)
        )
    return query


async def _compute_summary(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    risk_level: str | None,
    collection_method: str | None,
    due_date_from: date | None,
    due_date_to: date | None,
    search: str | None,
) -> ScoresSummary:
    """Aggregate counts over the full filtered dataset (not paged)."""
    base = _base_query(tenant_id)
    base = _apply_filters(
        base,
        risk_level=risk_level,
        collection_method=collection_method,
        due_date_from=due_date_from,
        due_date_to=due_date_to,
        search=search,
    )
    sub = base.subquery()

    summary_q = select(
        func.count(case((sub.c.risk_level == RiskLevel.HIGH, 1))).label("high"),
        func.count(case((sub.c.risk_level == RiskLevel.MEDIUM, 1))).label("medium"),
        func.count(case((sub.c.risk_level == RiskLevel.LOW, 1))).label("low"),
        func.coalesce(
            func.sum(
                case(
                    (sub.c.risk_level == RiskLevel.HIGH, sub.c.collection_amount),
                    else_=Decimal(0),
                )
            ),
            Decimal(0),
        ).label("value_at_risk"),
    )

    row = (await db.execute(summary_q)).one()
    return ScoresSummary(
        high_risk=row.high,
        medium_risk=row.medium,
        low_risk=row.low,
        total_value_at_risk=row.value_at_risk,
    )


async def list_scores(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    page: int = 1,
    page_size: int = 25,
    risk_level: str | None = None,
    collection_method: str | None = None,
    due_date_from: date | None = None,
    due_date_to: date | None = None,
    search: str | None = None,
    sort_by: str = "score",
    sort_order: str = "desc",
) -> ScoresListResponse:
    query = _base_query(tenant_id)
    query = _apply_filters(
        query,
        risk_level=risk_level,
        collection_method=collection_method,
        due_date_from=due_date_from,
        due_date_to=due_date_to,
        search=search,
    )

    # Sort
    sort_col = _SORT_COLUMNS.get(sort_by, ScoreResult.score)
    query = query.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())

    rows, pagination = await paginate(db, query, page, page_size)

    items = [_row_to_list_item(req, res) for req, res in rows]

    summary = await _compute_summary(
        db,
        tenant_id,
        risk_level=risk_level,
        collection_method=collection_method,
        due_date_from=due_date_from,
        due_date_to=due_date_to,
        search=search,
    )

    return ScoresListResponse(items=items, pagination=pagination, summary=summary)


def _row_to_list_item(req: ScoreRequest, res: ScoreResult) -> ScoreListItem:
    payload = req.request_payload or {}
    customer = payload.get("customer_data", {})
    return ScoreListItem(
        score_id=res.id,
        external_customer_id=req.external_customer_id,
        external_collection_id=req.external_collection_id,
        collection_amount=req.collection_amount,
        collection_currency=req.collection_currency.value,
        collection_due_date=req.collection_due_date,
        collection_method=req.collection_method.value,
        instalment_number=customer.get("instalment_number"),
        total_instalments=customer.get("total_instalments"),
        score=res.score,
        risk_level=res.risk_level.value,
        recommended_action=res.recommended_action,
        model_version=res.model_version,
        scored_at=res.created_at,
    )


# ---- Detail ----

async def get_score_detail(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    score_id: uuid.UUID,
) -> ScoreDetailResponse | None:
    """Load a single score with factor breakdown, customer context, and
    linked outcome (if any)."""
    result = await db.execute(
        select(ScoreRequest, ScoreResult)
        .join(ScoreResult, ScoreResult.score_request_id == ScoreRequest.id)
        .where(
            ScoreResult.id == score_id,
            ScoreRequest.tenant_id == tenant_id,
        )
    )
    row = result.one_or_none()
    if row is None:
        return None

    req: ScoreRequest = row[0]
    res: ScoreResult = row[1]

    # Load linked outcome
    outcome_result = await db.execute(
        select(Outcome).where(Outcome.score_result_id == res.id)
    )
    outcome_row = outcome_result.scalar_one_or_none()

    return _build_detail(req, res, outcome_row)


def _build_detail(
    req: ScoreRequest,
    res: ScoreResult,
    outcome: Outcome | None,
) -> ScoreDetailResponse:
    payload = req.request_payload or {}
    customer_raw = payload.get("customer_data", {})

    # Extract customer context
    total = customer_raw.get("total_payments")
    successful = customer_raw.get("successful_payments")
    success_rate = None
    if total and total > 0 and successful is not None:
        success_rate = round(successful / total, 3)

    days_since = None
    last_payment_date = customer_raw.get("last_successful_payment_date")
    if last_payment_date:
        try:
            lpd = date.fromisoformat(str(last_payment_date))
            days_since = (datetime.now(timezone.utc).date() - lpd).days
        except (ValueError, TypeError):
            pass

    customer_context = CustomerContext(
        total_payments=total,
        successful_payments=successful,
        success_rate=success_rate,
        days_since_last_payment=days_since,
    )

    # Factor breakdown
    factors_data = res.factors or {}
    factors = [
        FactorBreakdown(
            factor=f["factor_name"],
            raw_score=f["raw_score"],
            weight=f["weight"],
            weighted_score=f["weighted_score"],
            explanation=f["explanation"],
        )
        for f in factors_data.get("evaluated", [])
    ]
    skipped = factors_data.get("skipped", [])

    # Outcome
    outcome_summary = None
    if outcome:
        outcome_summary = OutcomeSummary(
            outcome=outcome.outcome.value,
            failure_reason=outcome.failure_reason,
            attempted_at=outcome.attempted_at,
        )

    return ScoreDetailResponse(
        score_id=res.id,
        external_customer_id=req.external_customer_id,
        external_collection_id=req.external_collection_id,
        collection_amount=req.collection_amount,
        collection_currency=req.collection_currency.value,
        collection_due_date=req.collection_due_date,
        collection_method=req.collection_method.value,
        instalment_number=customer_raw.get("instalment_number"),
        total_instalments=customer_raw.get("total_instalments"),
        score=res.score,
        risk_level=res.risk_level.value,
        recommended_action=res.recommended_action,
        recommended_collection_date=res.recommended_collection_date,
        factors=factors,
        skipped_factors=skipped,
        model_version=res.model_version,
        scored_at=res.created_at,
        scoring_duration_ms=res.scoring_duration_ms,
        customer_context=customer_context,
        outcome=outcome_summary,
    )
