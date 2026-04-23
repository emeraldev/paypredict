"""Backtest service — score historical collections and compute accuracy.

Uses the SAME ScoringEngine as live scoring. No duplicate scoring logic.
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.backtest import BacktestItem, BacktestRun, BacktestStatus
from app.models.factor_weight import FactorWeight
from app.models.score_request import CollectionMethod
from app.models.tenant import Tenant
from app.schemas.backtest import (
    BacktestCollectionInput,
    BacktestConfusionMatrix,
    BacktestFactorContribution,
    BacktestListItem,
    BacktestListResponse,
    BacktestResponse,
    BacktestRiskBucket,
    BacktestSummary,
)
from app.scoring.engine import ScoringEngine

_engine = ScoringEngine()


def _prediction_matched(risk_level: str, actual_outcome: str) -> bool:
    if risk_level == "HIGH" and actual_outcome == "FAILED":
        return True
    if risk_level == "LOW" and actual_outcome == "SUCCESS":
        return True
    if risk_level == "MEDIUM":
        return True
    return False


async def run_backtest(
    db: AsyncSession,
    tenant: Tenant,
    collections: list[BacktestCollectionInput],
    name: str | None = None,
) -> BacktestResponse:
    """Score each collection, compare to actual outcomes, store results."""
    now = datetime.now(timezone.utc)

    # Load tenant's current weights
    result = await db.execute(
        select(FactorWeight).where(FactorWeight.tenant_id == tenant.id)
    )
    weights_rows = result.scalars().all()
    custom_weights = {w.factor_name: w.weight for w in weights_rows}
    weights_snapshot = {w.factor_name: w.weight for w in weights_rows}

    # Create run record
    run = BacktestRun(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name=name,
        status=BacktestStatus.PROCESSING,
        total_collections=len(collections),
        factor_set_used=tenant.factor_set.value,
        weights_used=weights_snapshot,
        started_at=now,
    )
    db.add(run)

    # Score each collection
    items: list[BacktestItem] = []
    for coll in collections:
        customer_data = coll.customer_data.model_dump()
        collection_data = {
            "collection_amount": float(coll.collection_amount),
            "collection_due_date": coll.collection_date,
            "collection_method": coll.collection_method,
            "collection_currency": coll.collection_currency,
        }

        score_result = _engine.score(
            factor_set=tenant.factor_set.value,
            customer_data=customer_data,
            collection_data=collection_data,
            custom_weights=custom_weights if custom_weights else None,
            collection_method=CollectionMethod(coll.collection_method),
        )

        matched = _prediction_matched(score_result.risk_level, coll.actual_outcome)

        item = BacktestItem(
            id=uuid.uuid4(),
            backtest_run_id=run.id,
            external_customer_id=coll.external_customer_id,
            external_collection_id=coll.external_collection_id,
            collection_amount=coll.collection_amount,
            collection_method=coll.collection_method,
            predicted_score=score_result.score,
            predicted_risk_level=score_result.risk_level,
            actual_outcome=coll.actual_outcome,
            failure_reason=coll.failure_reason,
            factors={
                "evaluated": [
                    {
                        "factor_name": f.factor_name,
                        "raw_score": f.raw_score,
                        "weight": f.weight,
                        "weighted_score": f.weighted_score,
                        "explanation": f.explanation,
                    }
                    for f in score_result.factors
                ],
                "skipped": score_result.skipped_factors,
            },
            prediction_matched=matched,
        )
        items.append(item)
        db.add(item)

    # Compute summary stats
    summary = _compute_summary(items)
    confusion = _compute_confusion_matrix(items)
    top_factors = _compute_top_failure_factors(items)
    risk_dist = _compute_risk_distribution(items)

    run.summary = summary.model_dump()
    run.confusion_matrix = confusion.model_dump()
    run.top_failure_factors = [f.model_dump() for f in top_factors]
    run.status = BacktestStatus.COMPLETED
    run.completed_at = datetime.now(timezone.utc)

    await db.flush()

    return BacktestResponse(
        backtest_id=run.id,
        name=run.name,
        total_collections=run.total_collections,
        status=run.status.value,
        started_at=run.started_at,
        completed_at=run.completed_at,
        summary=summary,
        risk_distribution=risk_dist,
        top_failure_factors=top_factors,
        confusion_matrix=confusion,
    )


def _compute_summary(items: list[BacktestItem]) -> BacktestSummary:
    total = len(items)
    matched = sum(1 for i in items if i.prediction_matched)
    failed = [i for i in items if i.actual_outcome == "FAILED"]
    succeeded = [i for i in items if i.actual_outcome == "SUCCESS"]

    total_failed_value = float(sum(i.collection_amount for i in failed))
    high_risk_failed = [
        i for i in failed if i.predicted_risk_level == "HIGH"
    ]
    flagged_value = float(sum(i.collection_amount for i in high_risk_failed))

    actual_rate = len(succeeded) / total if total > 0 else 0
    # "If acted" rate: assume we'd have recovered 60% of high-risk flagged failures
    recovered = flagged_value * 0.6
    acted_successes = len(succeeded) + len(high_risk_failed) * 0.6
    acted_rate = acted_successes / total if total > 0 else 0

    # Annualise: scale the recovery based on the backtest period
    # Simple estimate: multiply monthly by 12
    annual_recovery = recovered * 12

    return BacktestSummary(
        overall_accuracy=round(matched / total, 3) if total > 0 else 0,
        collection_rate_actual=round(actual_rate, 3),
        collection_rate_if_acted=round(min(acted_rate, 1.0), 3),
        estimated_annual_recovery=round(annual_recovery, 2),
        total_failed_value=round(total_failed_value, 2),
        flagged_in_advance_value=round(flagged_value, 2),
    )


def _compute_confusion_matrix(items: list[BacktestItem]) -> BacktestConfusionMatrix:
    cm = {
        "predicted_high_actual_failed": 0,
        "predicted_high_actual_success": 0,
        "predicted_medium_actual_failed": 0,
        "predicted_medium_actual_success": 0,
        "predicted_low_actual_failed": 0,
        "predicted_low_actual_success": 0,
    }
    for i in items:
        key = f"predicted_{i.predicted_risk_level.lower()}_actual_{'failed' if i.actual_outcome == 'FAILED' else 'success'}"
        if key in cm:
            cm[key] += 1
    return BacktestConfusionMatrix(**cm)


def _compute_risk_distribution(
    items: list[BacktestItem],
) -> dict[str, BacktestRiskBucket]:
    buckets: dict[str, list[BacktestItem]] = defaultdict(list)
    for i in items:
        buckets[i.predicted_risk_level.lower()].append(i)

    result = {}
    for level in ("high", "medium", "low"):
        bucket = buckets.get(level, [])
        count = len(bucket)
        actually_failed = sum(1 for i in bucket if i.actual_outcome == "FAILED")
        if count > 0:
            if level == "high":
                accuracy = actually_failed / count  # high = we want them to fail
            elif level == "low":
                accuracy = (count - actually_failed) / count  # low = we want them to succeed
            else:
                accuracy = 0.5  # medium is uncertain by definition
        else:
            accuracy = 0
        result[level] = BacktestRiskBucket(
            count=count,
            actually_failed=actually_failed,
            accuracy=round(accuracy, 3),
        )
    return result


def _compute_top_failure_factors(
    items: list[BacktestItem],
) -> list[BacktestFactorContribution]:
    """For items that actually failed, compute average factor scores."""
    failed = [i for i in items if i.actual_outcome == "FAILED"]
    if not failed:
        return []

    factor_scores: dict[str, list[float]] = defaultdict(list)
    factor_weighted: dict[str, list[float]] = defaultdict(list)

    for item in failed:
        for f in item.factors.get("evaluated", []):
            factor_scores[f["factor_name"]].append(f["raw_score"])
            factor_weighted[f["factor_name"]].append(f["weighted_score"])

    # Total weighted contribution across all factors
    total_weighted = sum(
        sum(scores) for scores in factor_weighted.values()
    )

    contributions = []
    for factor_name, scores in factor_scores.items():
        avg_score = sum(scores) / len(scores)
        weighted_sum = sum(factor_weighted[factor_name])
        contribution = weighted_sum / total_weighted if total_weighted > 0 else 0

        contributions.append(
            BacktestFactorContribution(
                factor=factor_name,
                avg_score_in_failures=round(avg_score, 4),
                contribution=round(contribution, 4),
            )
        )

    contributions.sort(key=lambda x: x.contribution, reverse=True)
    return contributions[:8]  # Top 8 factors


async def get_backtest(
    db: AsyncSession, tenant_id: uuid.UUID, backtest_id: uuid.UUID
) -> BacktestResponse | None:
    """Load a backtest run by ID."""
    result = await db.execute(
        select(BacktestRun).where(
            BacktestRun.id == backtest_id,
            BacktestRun.tenant_id == tenant_id,
        )
    )
    run = result.scalar_one_or_none()
    if run is None:
        return None

    summary = BacktestSummary(**run.summary) if run.summary else None
    confusion = BacktestConfusionMatrix(**run.confusion_matrix) if run.confusion_matrix else None
    top_factors = (
        [BacktestFactorContribution(**f) for f in run.top_failure_factors]
        if run.top_failure_factors
        else None
    )

    # Compute risk distribution from summary if available
    risk_dist = None
    if run.confusion_matrix:
        cm = run.confusion_matrix
        risk_dist = {
            "high": BacktestRiskBucket(
                count=cm["predicted_high_actual_failed"] + cm["predicted_high_actual_success"],
                actually_failed=cm["predicted_high_actual_failed"],
                accuracy=round(
                    cm["predicted_high_actual_failed"]
                    / max(cm["predicted_high_actual_failed"] + cm["predicted_high_actual_success"], 1),
                    3,
                ),
            ),
            "medium": BacktestRiskBucket(
                count=cm["predicted_medium_actual_failed"] + cm["predicted_medium_actual_success"],
                actually_failed=cm["predicted_medium_actual_failed"],
                accuracy=0.5,
            ),
            "low": BacktestRiskBucket(
                count=cm["predicted_low_actual_failed"] + cm["predicted_low_actual_success"],
                actually_failed=cm["predicted_low_actual_failed"],
                accuracy=round(
                    cm["predicted_low_actual_success"]
                    / max(cm["predicted_low_actual_failed"] + cm["predicted_low_actual_success"], 1),
                    3,
                ),
            ),
        }

    return BacktestResponse(
        backtest_id=run.id,
        name=run.name,
        total_collections=run.total_collections,
        status=run.status.value,
        started_at=run.started_at,
        completed_at=run.completed_at,
        summary=summary,
        risk_distribution=risk_dist,
        top_failure_factors=top_factors,
        confusion_matrix=confusion,
    )


async def list_backtests(
    db: AsyncSession, tenant_id: uuid.UUID
) -> BacktestListResponse:
    """List all backtest runs for a tenant."""
    result = await db.execute(
        select(BacktestRun)
        .where(BacktestRun.tenant_id == tenant_id)
        .order_by(BacktestRun.created_at.desc())
    )
    runs = result.scalars().all()

    items = []
    for run in runs:
        accuracy = None
        if run.summary and "overall_accuracy" in run.summary:
            accuracy = run.summary["overall_accuracy"]
        items.append(
            BacktestListItem(
                backtest_id=run.id,
                name=run.name,
                total_collections=run.total_collections,
                status=run.status.value,
                overall_accuracy=accuracy,
                created_at=run.created_at,
            )
        )

    return BacktestListResponse(items=items)
