"""Bulk scoring service — score multiple collections in one call.

<= 50 items: processed synchronously, results returned inline.
> 50 items: queued to Celery, returns job_id for polling.

Uses the SAME ScoringEngine as single scoring. No duplicate logic.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import redis

from app.config import settings
from app.models.score_request import CollectionCurrency, CollectionMethod, ScoreRequest
from app.models.score_result import RiskLevel, ScoreResult
from app.models.tenant import Tenant
from app.schemas.score import FactorBreakdown, ScoreResponse
from app.scoring.engine import ScoringEngine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.factor_weight import FactorWeight

_engine = ScoringEngine()
_redis = redis.from_url(settings.redis_url, decode_responses=True)


def _to_json_safe(obj: dict) -> dict:
    """Convert a dict with Decimal/date values to JSON-serializable types."""
    import json
    from datetime import date as _date

    def _default(o: object) -> object:
        if isinstance(o, Decimal):
            return float(o)
        if isinstance(o, _date):
            return o.isoformat()
        raise TypeError(f"Not serializable: {type(o)}")

    return json.loads(json.dumps(obj, default=_default))

SYNC_THRESHOLD = 50
JOB_TTL = 3600  # 1 hour


def _score_one(
    tenant: Tenant,
    item: dict,
    custom_weights: dict[str, float],
) -> dict:
    """Score a single collection and return the result dict (not persisted)."""
    customer_data = item.get("customer_data", {})
    collection_method = CollectionMethod(item["collection_method"])

    # Ensure date is a date object (Celery path sends strings, sync sends dates)
    due_date = item["collection_due_date"]
    if isinstance(due_date, str):
        from datetime import date as _date
        due_date = _date.fromisoformat(due_date)

    result = _engine.score(
        factor_set=tenant.factor_set.value,
        customer_data=customer_data,
        collection_data={
            "collection_amount": float(item["collection_amount"]),
            "collection_due_date": due_date,
            "collection_method": item["collection_method"],
            "collection_currency": item["collection_currency"],
        },
        custom_weights=custom_weights or None,
        collection_method=collection_method,
    )

    return {
        "external_customer_id": item["external_customer_id"],
        "external_collection_id": item["external_collection_id"],
        "score": result.score,
        "risk_level": result.risk_level,
        "recommended_action": result.recommended_action,
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
    }


async def score_bulk_sync(
    db: AsyncSession,
    tenant: Tenant,
    collections: list[dict],
) -> dict:
    """Score a batch synchronously and persist results."""
    weights = await _load_weights(db, tenant.id)

    results = []
    summary = {"high_risk": 0, "medium_risk": 0, "low_risk": 0, "total_value_at_risk": 0.0}

    for item in collections:
        scored = _score_one(tenant, item, weights)

        # Persist ScoreRequest + ScoreResult
        # Build JSON-safe payload for the JSONB column
        payload = _to_json_safe(item)
        req = ScoreRequest(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            external_customer_id=item["external_customer_id"],
            external_collection_id=item["external_collection_id"],
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
                "evaluated": scored["factors"],
                "skipped": scored["skipped_factors"],
            },
            recommended_action=scored["recommended_action"],
            model_version=scored["model_version"],
            scoring_duration_ms=scored["scoring_duration_ms"],
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

    # Evaluate alert threshold after scoring
    from app.services.alert_service import evaluate_alerts
    await evaluate_alerts(tenant, summary, db)

    return {
        "status": "completed",
        "total_items": len(results),
        "completed_items": len(results),
        "summary": summary,
        "results": results,
    }


def queue_bulk_job(
    tenant_id: str,
    factor_set: str,
    collections: list[dict],
    weights: dict[str, float],
) -> dict:
    """Queue a bulk scoring job to Celery and return the job_id."""
    job_id = str(uuid.uuid4())

    # Store initial status in Redis
    _redis.setex(f"bulk_job:{job_id}:status", JOB_TTL, "processing")
    _redis.setex(f"bulk_job:{job_id}:total", JOB_TTL, str(len(collections)))
    _redis.setex(f"bulk_job:{job_id}:completed", JOB_TTL, "0")

    # Queue the Celery task
    from app.tasks.bulk_scoring import score_bulk_task
    score_bulk_task.delay(job_id, tenant_id, factor_set, collections, weights)

    return {
        "job_id": job_id,
        "status": "processing",
        "total_items": len(collections),
        "estimated_completion_seconds": max(1, len(collections) // 20),
    }


def get_job_status(job_id: str) -> dict | None:
    """Get the status of a bulk scoring job from Redis."""
    status = _redis.get(f"bulk_job:{job_id}:status")
    if status is None:
        return None

    total = int(_redis.get(f"bulk_job:{job_id}:total") or "0")
    completed = int(_redis.get(f"bulk_job:{job_id}:completed") or "0")

    result: dict = {
        "job_id": job_id,
        "status": status,
        "total_items": total,
        "completed_items": completed,
    }

    if status == "completed":
        raw = _redis.get(f"bulk_job:{job_id}:results")
        if raw:
            data = json.loads(raw)
            result["summary"] = data.get("summary")
            result["results"] = data.get("results")

    return result


async def _load_weights(db: AsyncSession, tenant_id: uuid.UUID) -> dict[str, float]:
    result = await db.execute(
        select(FactorWeight).where(FactorWeight.tenant_id == tenant_id)
    )
    return {w.factor_name: w.weight for w in result.scalars().all()}
