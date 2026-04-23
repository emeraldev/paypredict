"""Dashboard outcomes list service.

Joins Outcome → ScoreResult → ScoreRequest to show predicted risk alongside
actual outcomes and compute prediction_matched.
"""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Select, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outcome import Outcome, OutcomeStatus
from app.models.score_request import ScoreRequest
from app.models.score_result import RiskLevel, ScoreResult
from app.schemas.outcomes_list import (
    OutcomeListItem,
    OutcomeListStats,
    OutcomesListResponse,
)
from app.services.query_utils import paginate


def _prediction_matched(risk_level: str | None, outcome: str) -> bool | None:
    """Compute whether the prediction matched reality.

    - HIGH predicted + FAILED actual → matched
    - LOW predicted + SUCCESS actual → matched
    - MEDIUM is always considered matched (uncertain)
    - No linked score → None
    """
    if risk_level is None:
        return None
    if risk_level == "MEDIUM":
        return True
    if risk_level == "HIGH" and outcome == "FAILED":
        return True
    if risk_level == "LOW" and outcome == "SUCCESS":
        return True
    return False


# ---- Base query ----

def _base_query(tenant_id: uuid.UUID) -> Select:
    """Left-join Outcome → ScoreResult → ScoreRequest to get score context."""
    return (
        select(
            Outcome,
            ScoreResult.score.label("predicted_score"),
            ScoreResult.risk_level.label("predicted_risk_level"),
            ScoreRequest.collection_amount.label("req_amount"),
            ScoreRequest.collection_currency.label("req_currency"),
            ScoreRequest.collection_method.label("req_method"),
        )
        .outerjoin(ScoreResult, ScoreResult.id == Outcome.score_result_id)
        .outerjoin(ScoreRequest, ScoreRequest.id == ScoreResult.score_request_id)
        .where(Outcome.tenant_id == tenant_id)
    )


# ---- Filters ----

_SORT_COLUMNS = {
    "attempted_at": Outcome.attempted_at,
    "score": ScoreResult.score,
    "collection_amount": ScoreRequest.collection_amount,
}


def _apply_filters(
    query: Select,
    *,
    outcome_status: str | None,
    match_filter: str | None,
    date_from: date | None,
    date_to: date | None,
) -> Select:
    if outcome_status:
        query = query.where(Outcome.outcome == OutcomeStatus(outcome_status))

    if date_from:
        query = query.where(Outcome.attempted_at >= date_from)
    if date_to:
        query = query.where(Outcome.attempted_at <= date_to)

    if match_filter == "MATCHED":
        # HIGH+FAILED or LOW+SUCCESS or MEDIUM (always matched)
        query = query.where(
            ScoreResult.id.isnot(None),  # must have a linked score
            (
                (ScoreResult.risk_level == RiskLevel.HIGH)
                & (Outcome.outcome == OutcomeStatus.FAILED)
            )
            | (
                (ScoreResult.risk_level == RiskLevel.LOW)
                & (Outcome.outcome == OutcomeStatus.SUCCESS)
            )
            | (ScoreResult.risk_level == RiskLevel.MEDIUM)
        )
    elif match_filter == "MISMATCHED":
        query = query.where(
            ScoreResult.id.isnot(None),
            (
                (ScoreResult.risk_level == RiskLevel.HIGH)
                & (Outcome.outcome == OutcomeStatus.SUCCESS)
            )
            | (
                (ScoreResult.risk_level == RiskLevel.LOW)
                & (Outcome.outcome == OutcomeStatus.FAILED)
            )
        )

    return query


# ---- Stats (SQL aggregation) ----

async def _compute_stats(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    outcome_status: str | None,
    match_filter: str | None,
    date_from: date | None,
    date_to: date | None,
) -> OutcomeListStats:
    """Aggregate stats over the full filtered dataset (not paged)."""
    base = _base_query(tenant_id)
    base = _apply_filters(
        base,
        outcome_status=outcome_status,
        match_filter=match_filter,
        date_from=date_from,
        date_to=date_to,
    )
    sub = base.subquery()

    # prediction_matched SQL expression:
    # HIGH+FAILED=matched, LOW+SUCCESS=matched, MEDIUM=matched, else mismatched
    matched_case = case(
        (sub.c.predicted_risk_level.is_(None), None),
        (sub.c.predicted_risk_level == "MEDIUM", True),
        (
            (sub.c.predicted_risk_level == "HIGH")
            & (sub.c.outcome == "FAILED"),
            True,
        ),
        (
            (sub.c.predicted_risk_level == "LOW")
            & (sub.c.outcome == "SUCCESS"),
            True,
        ),
        else_=False,
    )

    stats_q = select(
        func.count().label("total"),
        func.count(case((sub.c.outcome == "SUCCESS", 1))).label("success"),
        func.count(case((sub.c.outcome == "FAILED", 1))).label("failed"),
        func.count(case((matched_case == True, 1))).label("matched"),  # noqa: E712
    )

    row = (await db.execute(stats_q)).one()

    total = row.total
    resolved = row.success + row.failed
    success_rate = round(row.success / resolved, 3) if resolved > 0 else 0.0
    matched_plus_mismatched = row.matched + (resolved - row.matched)
    match_rate = round(row.matched / matched_plus_mismatched, 3) if matched_plus_mismatched > 0 else 0.0

    return OutcomeListStats(
        total_outcomes=total,
        success_count=row.success,
        failed_count=row.failed,
        success_rate=success_rate,
        predictions_matched=row.matched,
        match_rate=match_rate,
    )


# ---- List ----

async def list_outcomes(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    page: int = 1,
    page_size: int = 25,
    outcome_status: str | None = None,
    match_filter: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    sort_by: str = "attempted_at",
    sort_order: str = "desc",
) -> OutcomesListResponse:
    query = _base_query(tenant_id)
    query = _apply_filters(
        query,
        outcome_status=outcome_status,
        match_filter=match_filter,
        date_from=date_from,
        date_to=date_to,
    )

    sort_col = _SORT_COLUMNS.get(sort_by, Outcome.attempted_at)
    query = query.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())

    rows, pagination = await paginate(db, query, page, page_size)

    items = [_row_to_item(row) for row in rows]

    stats = await _compute_stats(
        db,
        tenant_id,
        outcome_status=outcome_status,
        match_filter=match_filter,
        date_from=date_from,
        date_to=date_to,
    )

    return OutcomesListResponse(items=items, pagination=pagination, stats=stats)


def _row_to_item(row) -> OutcomeListItem:
    outcome: Outcome = row[0]
    predicted_score = row[1]
    predicted_risk_level = row[2]
    req_amount = row[3]
    req_currency = row[4]
    req_method = row[5]

    risk_str = predicted_risk_level.value if predicted_risk_level else None
    outcome_str = outcome.outcome.value

    return OutcomeListItem(
        outcome_id=outcome.id,
        external_collection_id=outcome.external_collection_id,
        score=predicted_score,
        risk_level=risk_str,
        outcome=outcome_str,
        failure_reason=outcome.failure_reason,
        collection_amount=req_amount,
        collection_currency=req_currency.value if req_currency else None,
        collection_method=req_method.value if req_method else None,
        attempted_at=outcome.attempted_at,
        reported_at=outcome.reported_at,
        prediction_matched=_prediction_matched(risk_str, outcome_str),
    )
