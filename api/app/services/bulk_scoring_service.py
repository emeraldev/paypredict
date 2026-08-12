"""Bulk scoring service — score multiple collections in one call.

<= 50 items: processed synchronously, results returned inline.
> 50 items: queued to Celery, returns job_id for polling.

Uses the SAME ScoringEngine as single scoring. No duplicate logic.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal


_logger = logging.getLogger(__name__)

from app.models.score_request import CollectionCurrency, CollectionMethod, ScoreRequest
from app.models.score_result import RiskLevel, ScoreResult
from app.models.tenant import Tenant
from app.schemas.score import FactorBreakdown, ScoreResponse
from app.scoring.engine import ScoringEngine
from app.scoring.timing_optimiser import optimise_collection_date
from app.services.weights_service import load_all_weights_by_method
from sqlalchemy.ext.asyncio import AsyncSession

_engine = ScoringEngine()


def _to_json_safe(obj: dict) -> dict:
    """Convert a dict with Decimal/date values to JSON-serializable types."""
    from datetime import date as _date

    def _default(o: object) -> object:
        if isinstance(o, Decimal):
            return float(o)
        if isinstance(o, _date):
            return o.isoformat()
        raise TypeError(f"Not serializable: {type(o)}")

    return json.loads(json.dumps(obj, default=_default))

SYNC_THRESHOLD = 50


def _factor_to_db_shape(f: dict) -> dict:
    """Translate a response-shape factor entry ({"factor": ...}) to the
    DB JSONB shape ({"factor_name": ...}) that matches the single-score
    path and what analytics_service.get_factor_contributions reads.
    """
    return {
        "factor_name": f["factor"],
        "raw_score": f["raw_score"],
        "weight": f["weight"],
        "weighted_score": f["weighted_score"],
        "explanation": f["explanation"],
    }


# customer_data fields whose schema default carries no signal. A populated
# count below ~3 means scoring relied almost entirely on factor defaults —
# the dashboard surfaces a "limited data" hint in that case.
_SCHEMA_DEFAULTS_BY_FIELD = {
    "total_payments": 0,
    "successful_payments": 0,
    "debit_order_returns": [],
}


def _count_populated_optional_fields(customer_data: dict) -> int:
    """Count customer_data fields that carry real signal (not schema default).

    Used to flag scores produced with thin data so non-technical lenders know
    when to add more columns vs. trust the prediction. Excludes the 6 required
    collection-level columns (which aren't in customer_data).
    """
    count = 0
    for key, value in customer_data.items():
        if value is None or value == "":
            continue
        default = _SCHEMA_DEFAULTS_BY_FIELD.get(key)
        if default is not None and value == default:
            continue
        count += 1
    return count


def _score_one(
    item: dict,
    weights_by_method: dict[str, dict[str, float]],
) -> dict:
    """Score a single collection and return the result dict (not persisted).

    `weights_by_method` maps collection_method string -> factor_name ->
    weight. The row's method decides which sub-dict is applied — cross-
    method weight rows on the same tenant never mix.
    """
    customer_data = item.get("customer_data", {})
    collection_method = CollectionMethod(item["collection_method"])

    # Ensure date is a date object (Celery path sends strings, sync sends dates)
    due_date = item["collection_due_date"]
    if isinstance(due_date, str):
        from datetime import date as _date
        due_date = _date.fromisoformat(due_date)

    collection_data = {
        "collection_amount": float(item["collection_amount"]),
        "collection_due_date": due_date,
        "collection_method": item["collection_method"],
        "collection_currency": item["collection_currency"],
    }
    custom_weights = weights_by_method.get(collection_method.value, {}) or None

    result = _engine.score(
        customer_data=customer_data,
        collection_data=collection_data,
        custom_weights=custom_weights,
        collection_method=collection_method,
    )

    # Run the timing optimiser for the same candidate. Same rules as the
    # single-score path — `shift_date` action overrides the risk-level
    # action when a meaningful improvement exists.
    timing = optimise_collection_date(
        _engine,
        customer_data=customer_data,
        collection_data=collection_data,
        collection_method=collection_method,
        original_score=result.score,
        custom_weights=custom_weights,
    )
    recommended_action = (
        "shift_date" if timing.should_shift else result.recommended_action
    )

    return {
        "customer_id": item["customer_id"],
        "collection_id": item["collection_id"],
        # Collection metadata echoed back so the dashboard can render and
        # export the scored rows without a round-trip to /v1/scores.
        "collection_amount": float(item["collection_amount"]),
        "collection_currency": item["collection_currency"],
        "collection_due_date": (
            item["collection_due_date"].isoformat()
            if hasattr(item["collection_due_date"], "isoformat")
            else item["collection_due_date"]
        ),
        "collection_method": item["collection_method"],
        # How many optional customer_data fields the lender actually filled —
        # surfaced in the dashboard so low-data rows don't look as confident as
        # full-data rows scoring the same number.
        "populated_optional_fields": _count_populated_optional_fields(customer_data),
        "score": result.score,
        "risk_level": result.risk_level,
        "recommended_action": recommended_action,
        "recommended_collection_date": timing.recommended_date,
        "recommended_score": timing.recommended_score,
        "score_improvement": timing.score_improvement if timing.should_shift else None,
        "model_version": result.model_version,
        "scoring_duration_ms": result.scoring_duration_ms,
        "factors": [
            {
                "factor": f.factor_name,
                "raw_score": f.raw_score,
                "weight": f.weight,
                "weighted_score": f.weighted_score,
                "explanation": f.explanation,
            }
            for f in result.factors
        ],
        "skipped_factors": result.skipped_factors,
        # Full effective weight vector (pre-normalisation) — persisted on
        # ScoreResult for exact-config reproducibility.
        "weights_snapshot": result.weights_snapshot,
    }


async def score_bulk_sync(
    db: AsyncSession,
    tenant: Tenant,
    collections: list[dict],
) -> dict:
    """Score a batch synchronously and persist results."""
    weights_by_method = await load_all_weights_by_method(db, tenant.id)

    results = []
    summary = {"high_risk": 0, "medium_risk": 0, "low_risk": 0, "total_value_at_risk": 0.0}

    for item in collections:
        scored = _score_one(item, weights_by_method)

        # Persist ScoreRequest + ScoreResult
        # Build JSON-safe payload for the JSONB column
        payload = _to_json_safe(item)
        req = ScoreRequest(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            external_customer_id=item["customer_id"],
            external_collection_id=item["collection_id"],
            collection_amount=Decimal(str(item["collection_amount"])),
            collection_currency=CollectionCurrency(item["collection_currency"]),
            collection_due_date=item["collection_due_date"],
            collection_method=CollectionMethod(item["collection_method"]),
            request_payload=payload,
        )
        db.add(req)

        res = ScoreResult(
            id=uuid.uuid4(),
            score_request_id=req.id,
            tenant_id=tenant.id,
            score=scored["score"],
            risk_level=RiskLevel(scored["risk_level"]),
            factors={
                "evaluated": [_factor_to_db_shape(f) for f in scored["factors"]],
                "skipped": scored["skipped_factors"],
            },
            recommended_action=scored["recommended_action"],
            recommended_collection_date=scored.get("recommended_collection_date"),
            recommended_score=scored.get("recommended_score"),
            score_improvement=scored.get("score_improvement"),
            model_version=scored["model_version"],
            scoring_duration_ms=scored["scoring_duration_ms"],
            weights_snapshot=scored.get("weights_snapshot"),
        )
        db.add(res)

        scored["score_id"] = str(res.id)
        results.append(scored)

        # Update summary
        level = scored["risk_level"].lower()
        if level == "high":
            summary["high_risk"] += 1
            summary["total_value_at_risk"] += float(item["collection_amount"])
        elif level == "medium":
            summary["medium_risk"] += 1
        else:
            summary["low_risk"] += 1

    await db.flush()

    # SAVEPOINT around alert evaluation so a failure inside — Python
    # exception OR a DB error that marks the outer txn for rollback —
    # doesn't cascade into losing every scored row. A plain try/except
    # would catch the exception but leave the session unusable, and the
    # endpoint's `db.commit()` would then raise `PendingRollbackError`.
    # Alert loss becomes silent by design; the WARNING is the only
    # observable signal that a compliance-critical alert didn't fire.
    from app.services.alert_service import evaluate_alerts
    try:
        async with db.begin_nested():
            await evaluate_alerts(tenant, summary, db)
    except Exception:
        _logger.exception(
            "alert evaluation failed for tenant %s (scoring rows retained)",
            tenant.id,
        )

    return {
        "status": "completed",
        "total_items": len(results),
        "completed_items": len(results),
        "summary": summary,
        "results": results,
    }


async def queue_bulk_job(
    db: AsyncSession,
    tenant_id: str,
    collections: list[dict],
    weights_by_method: dict[str, dict[str, float]],
) -> dict:
    """Queue a bulk scoring job to Celery, return the job_id.

    Writes a `bulk_scoring_jobs` row as the source of truth for job
    state (Postgres survives Redis outages that would otherwise leave
    a polling client stuck on `processing` — see the H4 limitation
    the roadmap tracked as Stage 2 #18).

    `weights_by_method` is a nested dict: collection_method value ->
    factor_name -> weight. The worker picks the right sub-dict per row.
    """
    from app.models.bulk_scoring_job import BulkScoringJob, BulkScoringJobStatus

    job_id = uuid.uuid4()
    job_row = BulkScoringJob(
        tenant_id=uuid.UUID(tenant_id),
        job_id=job_id,
        status=BulkScoringJobStatus.PROCESSING,
        total_items=len(collections),
        completed_items=0,
    )
    db.add(job_row)
    await db.flush()

    from app.tasks.bulk_scoring import score_bulk_task
    score_bulk_task.delay(
        job_id=str(job_id),
        tenant_id=tenant_id,
        collections=collections,
        weights_by_method=weights_by_method,
    )

    return {
        "job_id": str(job_id),
        "status": "processing",
        "total_items": len(collections),
        "estimated_completion_seconds": max(1, len(collections) // 20),
    }


async def get_job_status(
    db: AsyncSession, tenant_id: str, job_id: str
) -> dict | None:
    """Look up a bulk-scoring job by (tenant_id, job_id).

    Returns None when the pair doesn't exist — indistinguishable from
    "not found or expired". The `(tenant_id, job_id)` unique constraint
    on the table makes cross-tenant reads structurally impossible.

    Status values:
      - `processing`  — task queued/running
      - `completed`   — task finished; `summary` + `results` populated
      - `failed`      — task raised past retries; `error` carries a
                        short sanitized message (full traceback is in
                        the worker log, not returned here)
    """
    from sqlalchemy import select

    from app.models.bulk_scoring_job import BulkScoringJob

    result = await db.execute(
        select(BulkScoringJob).where(
            BulkScoringJob.tenant_id == uuid.UUID(tenant_id),
            BulkScoringJob.job_id == uuid.UUID(job_id),
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        return None

    response: dict = {
        "job_id": job_id,
        "status": row.status.value,
        "total_items": row.total_items,
        "completed_items": row.completed_items,
    }
    if row.status.value == "completed":
        if row.summary is not None:
            response["summary"] = row.summary
        if row.results is not None:
            response["results"] = row.results
    elif row.status.value == "failed" and row.error is not None:
        response["error"] = row.error
    return response


