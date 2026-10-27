"""Dashboard analytics service.

All queries use SQL aggregations (COUNT, SUM, AVG with GROUP BY).
No rows are loaded into Python — only aggregate results.
Every query is scoped to tenant_id.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import Float, case, cast, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.database import run_parallel
from app.models.outcome import Outcome, OutcomeStatus
from app.models.score_request import ScoreRequest
from app.models.score_result import RiskLevel, ScoreResult
from app.schemas.analytics import (
    AccuracyResponse,
    AnalyticsSummaryResponse,
    CollectionRatePoint,
    CollectionRateResponse,
    ConfusionMatrix,
    FactorContributionItem,
    FactorsResponse,
    PredictionAccuracy,
    RiskDistribution,
)
from app.services import analytics_cache
from app.services.query_utils import period_start


async def _execute_one(session: AsyncSession, query: Select) -> any:
    """Trivial wrapper: run one SQL query, return its one()-row.

    Exists so `run_parallel(lambda s: _execute_one(s, q))` reads
    cleanly in call sites. Keeps the lambda closure tiny — no
    captured state besides the pre-built query object, which is
    read-only.
    """
    return (await session.execute(query)).one()


# ---- Summary ----

async def get_summary(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    period: str,
) -> AnalyticsSummaryResponse:
    # Cache check — key off (endpoint, tenant_id, period). Short TTL
    # so admin weight edits are visible within ~1 min; long enough
    # that back-to-back clicks are instant.
    params = {"period": period}
    cached = analytics_cache.get(
        AnalyticsSummaryResponse, "summary", tenant_id, params
    )
    if cached is not None:
        return cached

    cutoff = period_start(period)
    prev_cutoff = cutoff - (datetime.now(timezone.utc) - cutoff)

    # Four independent aggregations — before this landed they ran
    # serially (each paying ~160 ms Frankfurt RTT), stacking to
    # 4+ seconds. Running them via `run_parallel` fires each on a
    # fresh session so they overlap in wall-clock time.
    scores_q = (
        select(
            func.count().label("total_scored"),
            func.coalesce(func.sum(ScoreRequest.collection_amount), Decimal(0)).label("total_value_scored"),
            func.coalesce(func.avg(ScoreResult.score), 0).label("avg_score"),
            func.count(case((ScoreResult.risk_level == RiskLevel.HIGH, 1))).label("high"),
            func.count(case((ScoreResult.risk_level == RiskLevel.MEDIUM, 1))).label("medium"),
            func.count(case((ScoreResult.risk_level == RiskLevel.LOW, 1))).label("low"),
            func.coalesce(
                func.sum(case((ScoreResult.risk_level == RiskLevel.HIGH, ScoreRequest.collection_amount), else_=Decimal(0))),
                Decimal(0),
            ).label("value_at_risk"),
        )
        .join(ScoreResult, ScoreResult.score_request_id == ScoreRequest.id)
        .where(ScoreRequest.tenant_id == tenant_id, ScoreResult.created_at >= cutoff)
    )

    outcomes_q = (
        select(
            func.count().label("total_outcomes"),
            func.count(case((Outcome.outcome == OutcomeStatus.SUCCESS, 1))).label("success"),
            func.count(case((Outcome.outcome == OutcomeStatus.FAILED, 1))).label("failed"),
        )
        .where(
            Outcome.tenant_id == tenant_id,
            Outcome.created_at >= cutoff,
            Outcome.deleted_at.is_(None),
        )
    )

    acc_q = (
        select(
            func.count(case((
                (ScoreResult.risk_level == RiskLevel.HIGH) & (Outcome.outcome == OutcomeStatus.FAILED), 1
            ))).label("high_failed"),
            func.count(case((
                ScoreResult.risk_level == RiskLevel.HIGH, 1
            ))).label("high_total"),
            func.count(case((
                (ScoreResult.risk_level == RiskLevel.LOW) & (Outcome.outcome == OutcomeStatus.SUCCESS), 1
            ))).label("low_success"),
            func.count(case((
                ScoreResult.risk_level == RiskLevel.LOW, 1
            ))).label("low_total"),
            func.count().label("linked_total"),
        )
        .select_from(Outcome)
        .join(ScoreResult, ScoreResult.id == Outcome.score_result_id)
        .where(
            Outcome.tenant_id == tenant_id,
            Outcome.created_at >= cutoff,
            Outcome.deleted_at.is_(None),
        )
    )

    prev_outcomes_q = (
        select(
            func.count(case((Outcome.outcome == OutcomeStatus.SUCCESS, 1))).label("success"),
            func.count(case(((Outcome.outcome == OutcomeStatus.SUCCESS) | (Outcome.outcome == OutcomeStatus.FAILED), 1))).label("resolved"),
        )
        .where(
            Outcome.tenant_id == tenant_id,
            Outcome.created_at >= prev_cutoff,
            Outcome.created_at < cutoff,
            Outcome.deleted_at.is_(None),
        )
    )

    sr, orow, arow, prev = await run_parallel(
        lambda s: _execute_one(s, scores_q),
        lambda s: _execute_one(s, outcomes_q),
        lambda s: _execute_one(s, acc_q),
        lambda s: _execute_one(s, prev_outcomes_q),
    )

    high_fail_rate = round(arow.high_failed / arow.high_total, 3) if arow.high_total > 0 else 0.0
    low_success_rate = round(arow.low_success / arow.low_total, 3) if arow.low_total > 0 else 0.0
    # Overall accuracy: high that failed + low that succeeded + all medium / total linked
    matched = arow.high_failed + arow.low_success + (arow.linked_total - arow.high_total - arow.low_total)
    overall_accuracy = round(matched / arow.linked_total, 3) if arow.linked_total > 0 else 0.0

    total_resolved = orow.success + orow.failed
    collection_rate = round(orow.success / total_resolved, 3) if total_resolved > 0 else 0.0
    reporting_rate = round(orow.total_outcomes / sr.total_scored, 3) if sr.total_scored > 0 else 0.0

    prev_rate = round(prev.success / prev.resolved, 3) if prev.resolved > 0 else 0.0
    rate_change = round(collection_rate - prev_rate, 3)

    response = AnalyticsSummaryResponse(
        period=period,
        total_scored=sr.total_scored,
        total_outcomes=orow.total_outcomes,
        collection_rate=collection_rate,
        collection_rate_change=rate_change,
        risk_distribution=RiskDistribution(high=sr.high, medium=sr.medium, low=sr.low),
        prediction_accuracy=PredictionAccuracy(
            high_risk_failure_rate=high_fail_rate,
            low_risk_success_rate=low_success_rate,
            overall_accuracy=overall_accuracy,
        ),
        total_value_scored=float(sr.total_value_scored),
        total_value_at_risk=float(sr.value_at_risk),
        avg_score=round(float(sr.avg_score), 3),
        outcomes_reporting_rate=reporting_rate,
    )

    analytics_cache.set_("summary", tenant_id, params, response)
    return response


# ---- Collection rate over time ----

async def get_collection_rate(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    period: str,
    interval: str,
) -> CollectionRateResponse:
    params = {"period": period, "interval": interval}
    cached = analytics_cache.get(
        CollectionRateResponse, "collection_rate", tenant_id, params
    )
    if cached is not None:
        return cached

    cutoff = period_start(period)

    # Truncate to day or week
    trunc_fn = "day" if interval == "daily" else "week"

    q = (
        select(
            func.date_trunc(trunc_fn, Outcome.attempted_at).label("bucket"),
            func.count().label("scored_count"),
            func.count(case((Outcome.outcome == OutcomeStatus.FAILED, 1))).label("failed_count"),
        )
        .where(
            Outcome.tenant_id == tenant_id,
            Outcome.attempted_at >= cutoff,
            Outcome.deleted_at.is_(None),
        )
        .group_by(text("1"))
        .order_by(text("1"))
    )
    rows = (await db.execute(q)).all()

    points = []
    for row in rows:
        total = row.scored_count
        failed = row.failed_count
        rate = round((total - failed) / total, 3) if total > 0 else 0.0
        points.append(CollectionRatePoint(
            date=row.bucket.strftime("%Y-%m-%d"),
            collection_rate=rate,
            scored_count=total,
            failed_count=failed,
        ))

    response = CollectionRateResponse(data_points=points)
    analytics_cache.set_("collection_rate", tenant_id, params, response)
    return response


# ---- Factor contributions ----

async def get_factor_contributions(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    period: str,
) -> FactorsResponse:
    """Compute average factor contribution and correlation with failure.

    Factor breakdowns are stored in ScoreResult.factors JSONB as:
    {"evaluated": [{"factor_name": "...", "weighted_score": 0.05, ...}], "skipped": [...]}

    We use a subquery that unnests the evaluated array, then aggregate.
    """
    params = {"period": period}
    cached = analytics_cache.get(FactorsResponse, "factors", tenant_id, params)
    if cached is not None:
        return cached

    cutoff = period_start(period)

    # COALESCE on both keys defends against legacy rows written by the old
    # bulk path (key was "factor") before the bulk writer was fixed.
    # WHERE clause then drops any unidentifiable rows so the Pydantic
    # response schema (factor: str) never sees a NULL.
    result = await db.execute(
        text("""
            WITH factor_data AS (
                SELECT
                    COALESCE(
                        f.value ->> 'factor_name',
                        f.value ->> 'factor'
                    ) AS factor_name,
                    (f.value ->> 'weighted_score')::float AS weighted_score,
                    CASE WHEN o.outcome = 'FAILED' THEN 1.0 ELSE 0.0 END AS is_failed
                FROM score_results sr
                CROSS JOIN LATERAL jsonb_array_elements(sr.factors -> 'evaluated') AS f(value)
                LEFT JOIN outcomes o ON o.score_result_id = sr.id
                WHERE sr.tenant_id = :tenant_id
                  AND sr.created_at >= :cutoff
            )
            SELECT
                factor_name,
                ROUND(AVG(weighted_score)::numeric, 4) AS avg_contribution,
                ROUND(CORR(weighted_score, is_failed)::numeric, 4) AS correlation
            FROM factor_data
            WHERE factor_name IS NOT NULL
            GROUP BY factor_name
            ORDER BY avg_contribution DESC
        """),
        {"tenant_id": str(tenant_id), "cutoff": cutoff},
    )
    rows = result.all()

    factors = [
        FactorContributionItem(
            factor=row.factor_name,
            avg_contribution=float(row.avg_contribution or 0),
            correlation_with_failure=float(row.correlation or 0),
        )
        for row in rows
    ]

    response = FactorsResponse(factors=factors)
    analytics_cache.set_("factors", tenant_id, params, response)
    return response


# ---- Confusion matrix ----

async def get_accuracy(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    period: str,
) -> AccuracyResponse:
    params = {"period": period}
    cached = analytics_cache.get(AccuracyResponse, "accuracy", tenant_id, params)
    if cached is not None:
        return cached

    cutoff = period_start(period)

    q = (
        select(
            func.count(case((
                (ScoreResult.risk_level == RiskLevel.HIGH) & (Outcome.outcome == OutcomeStatus.FAILED), 1
            ))).label("ph_af"),
            func.count(case((
                (ScoreResult.risk_level == RiskLevel.HIGH) & (Outcome.outcome == OutcomeStatus.SUCCESS), 1
            ))).label("ph_as"),
            func.count(case((
                (ScoreResult.risk_level == RiskLevel.MEDIUM) & (Outcome.outcome == OutcomeStatus.FAILED), 1
            ))).label("pm_af"),
            func.count(case((
                (ScoreResult.risk_level == RiskLevel.MEDIUM) & (Outcome.outcome == OutcomeStatus.SUCCESS), 1
            ))).label("pm_as"),
            func.count(case((
                (ScoreResult.risk_level == RiskLevel.LOW) & (Outcome.outcome == OutcomeStatus.FAILED), 1
            ))).label("pl_af"),
            func.count(case((
                (ScoreResult.risk_level == RiskLevel.LOW) & (Outcome.outcome == OutcomeStatus.SUCCESS), 1
            ))).label("pl_as"),
        )
        .select_from(Outcome)
        .join(ScoreResult, ScoreResult.id == Outcome.score_result_id)
        .where(
            Outcome.tenant_id == tenant_id,
            Outcome.created_at >= cutoff,
            Outcome.deleted_at.is_(None),
        )
    )
    row = (await db.execute(q)).one()

    response = AccuracyResponse(
        confusion_matrix=ConfusionMatrix(
            predicted_high_actual_failed=row.ph_af,
            predicted_high_actual_success=row.ph_as,
            predicted_medium_actual_failed=row.pm_af,
            predicted_medium_actual_success=row.pm_as,
            predicted_low_actual_failed=row.pl_af,
            predicted_low_actual_success=row.pl_as,
        )
    )
    analytics_cache.set_("accuracy", tenant_id, params, response)
    return response
