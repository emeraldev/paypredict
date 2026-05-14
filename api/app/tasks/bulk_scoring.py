"""Celery task for async bulk scoring (> 50 items)."""
import asyncio
import json
import uuid
from datetime import date as _date
from decimal import Decimal

import redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models.score_request import CollectionCurrency, CollectionMethod, ScoreRequest
from app.models.score_result import RiskLevel, ScoreResult
from app.models.tenant import FactorSet
from app.scoring.engine import ScoringEngine
from app.services.bulk_scoring_service import _factor_to_db_shape, _score_one, _to_json_safe, JOB_TTL
from app.tasks.celery_app import celery_app

_engine = ScoringEngine()
_redis = redis.from_url(settings.redis_url, decode_responses=True)


async def _persist_batch(
    tenant_id: uuid.UUID,
    items_with_scores: list[tuple[dict, dict]],
) -> list[str]:
    """Persist ScoreRequest + ScoreResult rows in a single transaction.
    Returns the list of score_ids in order."""
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    score_ids: list[str] = []

    try:
        async with session_factory() as db:
            for item, scored in items_with_scores:
                payload = _to_json_safe(item)
                due_date = item["collection_due_date"]
                if isinstance(due_date, str):
                    due_date = _date.fromisoformat(due_date)

                req = ScoreRequest(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    external_customer_id=item["external_customer_id"],
                    external_collection_id=item["external_collection_id"],
                    collection_amount=Decimal(str(item["collection_amount"])),
                    collection_currency=CollectionCurrency(item["collection_currency"]),
                    collection_due_date=due_date,
                    collection_method=CollectionMethod(item["collection_method"]),
                    request_payload=payload,
                )
                db.add(req)

                res = ScoreResult(
                    id=uuid.uuid4(),
                    score_request_id=req.id,
                    tenant_id=tenant_id,
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
                )
                db.add(res)
                score_ids.append(str(res.id))

            await db.commit()
    finally:
        await engine.dispose()

    return score_ids


@celery_app.task(bind=True)
def score_bulk_task(
    self,
    job_id: str,
    tenant_id: str,
    factor_set: str,
    collections: list[dict],
    weights: dict[str, float],
) -> None:
    """Score a batch of collections asynchronously.

    Persists ScoreRequest + ScoreResult to the DB (same as sync path).
    Stores progress in Redis so the polling endpoint can report it.
    Final results stored in Redis with a 1-hour TTL.
    """
    # Build a minimal tenant-like object for _score_one
    class _TenantStub:
        def __init__(self, fs: str):
            self.factor_set = FactorSet(fs)

    tenant_stub = _TenantStub(factor_set)

    results = []
    summary = {"high_risk": 0, "medium_risk": 0, "low_risk": 0, "total_value_at_risk": 0.0}
    items_with_scores: list[tuple[dict, dict]] = []

    for i, item in enumerate(collections):
        scored = _score_one(tenant_stub, item, weights)  # type: ignore[arg-type]
        results.append(scored)
        items_with_scores.append((item, scored))

        level = scored["risk_level"].lower()
        if level == "high":
            summary["high_risk"] += 1
            summary["total_value_at_risk"] += float(item.get("collection_amount", 0))
        elif level == "medium":
            summary["medium_risk"] += 1
        else:
            summary["low_risk"] += 1

        # Update progress for the polling endpoint
        _redis.setex(f"bulk_job:{job_id}:completed", JOB_TTL, str(i + 1))

    # Persist all rows to the DB in a single transaction
    score_ids = asyncio.run(
        _persist_batch(uuid.UUID(tenant_id), items_with_scores)
    )

    # Attach score_ids to the inline results so the polling response matches
    # the shape of the sync path
    for result_row, score_id in zip(results, score_ids):
        result_row["score_id"] = score_id

    # Store final results
    _redis.setex(
        f"bulk_job:{job_id}:results",
        JOB_TTL,
        json.dumps({"summary": summary, "results": results}),
    )
    _redis.setex(f"bulk_job:{job_id}:status", JOB_TTL, "completed")
