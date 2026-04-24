"""Celery task for async bulk scoring (> 50 items)."""
import json
import uuid
from decimal import Decimal

import redis

from app.config import settings
from app.models.score_request import CollectionCurrency, CollectionMethod
from app.models.tenant import Tenant, FactorSet
from app.scoring.engine import ScoringEngine
from app.services.bulk_scoring_service import _score_one, JOB_TTL
from app.tasks.celery_app import celery_app

_engine = ScoringEngine()
_redis = redis.from_url(settings.redis_url, decode_responses=True)


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

    Stores progress in Redis so the polling endpoint can report it.
    Results are stored in Redis with a 1-hour TTL.

    Note: DB persistence of ScoreRequest/ScoreResult is skipped for async
    bulk jobs for now — the results are returned via the polling endpoint.
    Full DB persistence can be added when needed.
    """
    # Build a minimal tenant-like object for _score_one
    class _TenantStub:
        def __init__(self, fs: str):
            self.factor_set = FactorSet(fs)

    tenant_stub = _TenantStub(factor_set)

    results = []
    summary = {"high_risk": 0, "medium_risk": 0, "low_risk": 0, "total_value_at_risk": 0.0}

    for i, item in enumerate(collections):
        scored = _score_one(tenant_stub, item, weights)  # type: ignore[arg-type]
        results.append(scored)

        level = scored["risk_level"].lower()
        if level == "high":
            summary["high_risk"] += 1
            summary["total_value_at_risk"] += float(item.get("collection_amount", 0))
        elif level == "medium":
            summary["medium_risk"] += 1
        else:
            summary["low_risk"] += 1

        # Update progress
        _redis.setex(f"bulk_job:{job_id}:completed", JOB_TTL, str(i + 1))

    # Store final results
    _redis.setex(
        f"bulk_job:{job_id}:results",
        JOB_TTL,
        json.dumps({"summary": summary, "results": results}),
    )
    _redis.setex(f"bulk_job:{job_id}:status", JOB_TTL, "completed")
