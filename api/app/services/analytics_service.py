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
from app.services.query_utils import period_start


# ---- Summary ----

async def get_summary(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    period: str,
) -> AnalyticsSummaryResponse:
    cutoff = period_start(period)

    # Scores in period
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
    sr = (await db.execute(scores_q)).one()

    # Outcomes in period (joined to ScoreResult for prediction accuracy)
    outcomes_q = (
        select(
            func.count().label("total_outcomes"),
            func.count(case((Outcome.outcome == OutcomeStatus.SUCCESS, 1))).label("success"),
            func.count(case((Outcome.outcome == OutcomeStatus.FAILED, 1))).label("failed"),
        )
        .where(Outcome.tenant_id == tenant_id, Outcome.created_at >= cutoff)
    )
    orow = (await db.execute(outcomes_q)).one()

    # Prediction accuracy: need outcomes joined to score results
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
        .where(Outcome.tenant_id == tenant_id, Outcome.created_at >= cutoff)
    )
    arow = (await db.execute(acc_q)).one()

    high_fail_rate = round(arow.high_failed / arow.high_total, 3) if arow.high_total > 0 else 0.0
    low_success_rate = round(arow.low_success / arow.low_total, 3) if arow.low_total > 0 else 0.0
    # Overall accuracy: high that failed + low that succeeded + all medium / total linked
    matched = arow.high_failed + arow.low_success + (arow.linked_total - arow.high_total - arow.low_total)
    overall_accuracy = round(matched / arow.linked_total, 3) if arow.linked_total > 0 else 0.0

    total_resolved = orow.success + orow.failed
    collection_rate = round(orow.success / total_resolved, 3) if total_resolved > 0 else 0.0
    reporting_rate = round(orow.total_outcomes / sr.total_scored, 3) if sr.total_scored > 0 else 0.0

    # Collection rate change: compare current period vs previous period
    prev_cutoff = cutoff - (datetime.now(timezone.utc) - cutoff)
    prev_outcomes_q = (
        select(
            func.count(case((Outcome.outcome == OutcomeStatus.SUCCESS, 1))).label("success"),
            func.count(case(((Outcome.outcome == OutcomeStatus.SUCCESS) | (Outcome.outcome == OutcomeStatus.FAILED), 1))).label("resolved"),
        )
        .where(
            Outcome.tenant_id == tenant_id,
            Outcome.created_at >= prev_cutoff,
            Outcome.created_at < cutoff,
        )
    )
    prev = (await db.execute(prev_outcomes_q)).one()
    prev_rate = round(prev.success / prev.resolved, 3) if prev.resolved > 0 else 0.0
    rate_change = round(collection_rate - prev_rate, 3)

    return AnalyticsSummaryResponse(
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
        total_value_scored=sr.total_value_scored,
        total_value_at_risk=sr.value_at_risk,
        avg_score=round(float(sr.avg_score), 3),
        outcomes_reporting_rate=reporting_rate,
    )


# ---- Collection rate over time ----

async def get_collection_rate(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    period: str,
    interval: str,
) -> CollectionRateResponse:
    cutoff = period_start(period)

    # Truncate to day or week
    trunc_fn = "day" if interval == "daily" else "week"

    q = (
        select(
            func.date_trunc(trunc_fn, Outcome.attempted_at).label("bucket"),
            func.count().label("scored_count"),
            func.count(case((Outcome.outcome == OutcomeStatus.FAILED, 1))).label("failed_count"),
        )
        .where(Outcome.tenant_id == tenant_id, Outcome.attempted_at >= cutoff)
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

    return CollectionRateResponse(data_points=points)


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
    cutoff = period_start(period)

    # Subquery: unnest factors JSONB for scores in the period that have outcomes
    # Using raw SQL for the JSONB unnest — SQLAlchemy's JSONB support for
    # array unnesting is verbose and less readable than a CTE.
    raw = text("""
        SELECT
            f.value ->> 'factor_name' AS factor_name,
            (f.value ->> 'weighted_score')::float AS weighted_score,
            CASE WHEN o.outcome = 'FAILED' THEN 1.0 ELSE 0.0 END AS is_failed
        FROM score_results sr
        CROSS JOIN LATERAL jsonb_array_elements(sr.factors -> 'evaluated') AS f(value)
        LEFT JOIN outcomes o ON o.score_result_id = sr.id
        WHERE sr.tenant_id = :tenant_id
          AND sr.created_at >= :cutoff
    """)

    sub = select(
        text("factor_name"),
        text("weighted_score"),
        text("is_failed"),
    ).select_from(text(f"({raw.text}) AS sub")).params(
        tenant_id=str(tenant_id), cutoff=cutoff
    )

    # This approach is cleaner — execute the raw SQL directly
    result = await db.execute(
        text("""
            WITH factor_data AS (
                SELECT
                    f.value ->> 'factor_name' AS factor_name,
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

    return FactorsResponse(factors=factors)


# ---- Confusion matrix ----

async def get_accuracy(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    period: str,
) -> AccuracyResponse:
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
        .where(Outcome.tenant_id == tenant_id, Outcome.created_at >= cutoff)
    )
    row = (await db.execute(q)).one()

    return AccuracyResponse(
        confusion_matrix=ConfusionMatrix(
            predicted_high_actual_failed=row.ph_af,
            predicted_high_actual_success=row.ph_as,
            predicted_medium_actual_failed=row.pm_af,
            predicted_medium_actual_success=row.pm_as,
            predicted_low_actual_failed=row.pl_af,
            predicted_low_actual_success=row.pl_as,
        )
    )
