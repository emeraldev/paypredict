"""Celery task for async bulk scoring (> 50 items)."""
import asyncio
import json
import logging
import uuid
from datetime import date as _date
from decimal import Decimal

import redis
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models.score_request import CollectionCurrency, CollectionMethod, ScoreRequest
from app.models.score_result import RiskLevel, ScoreResult
from app.scoring.engine import ScoringEngine
from app.services.bulk_scoring_service import (
    JOB_TTL,
    _factor_to_db_shape,
    _job_key,
    _score_one,
    _to_json_safe,
)
from app.tasks.celery_app import celery_app

_engine = ScoringEngine()
_redis = redis.from_url(settings.redis_url, decode_responses=True)
_logger = logging.getLogger(__name__)


# Narrow allowlist of errors that indicate a transient infrastructure blip
# rather than a logic bug. Retrying a bad `_score_one` payload just fails
# again three times — retrying a cold DB connection pool usually works
# the second time.
_TRANSIENT_ERRORS: tuple[type[BaseException], ...] = (
    OperationalError,
    redis.exceptions.ConnectionError,
    redis.exceptions.TimeoutError,
)


# Trim exception text before it reaches Redis (and eventually the
# customer's polling response). SQLAlchemy messages include query text
# and bound params; full traceback stays in the worker log.
_ERROR_MSG_MAX = 500


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
                    external_customer_id=item["customer_id"],
                    external_collection_id=item["collection_id"],
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


class _ScoreBulkTask(celery_app.Task):
    """Base class exposing `on_failure` so a terminal (post-retry) failure
    surfaces to the polling endpoint via a `status=failed` Redis write.

    The write itself is wrapped in its own try/except: if the failure
    that killed the task was `redis.ConnectionError`, letting the
    recorder raise would swallow the original traceback.
    """

    def on_failure(self, exc, task_id, args, kwargs, einfo):  # type: ignore[override]
        job_id = kwargs.get("job_id")
        tenant_id = kwargs.get("tenant_id")
        if not job_id or not tenant_id:
            _logger.exception(
                "score_bulk_task failed but couldn't locate job/tenant "
                "kwargs — cannot record failure to Redis"
            )
            return
        # Truncate the exception message before it lands in Redis:
        # SQLAlchemy error strings include query text and bound params,
        # neither of which should reach a customer's polling response.
        error_msg = repr(exc)[:_ERROR_MSG_MAX]
        try:
            # Status + error keys share JOB_TTL so a poller cannot hit a
            # window where one exists and the other is gone.
            _redis.setex(_job_key(tenant_id, job_id, "status"), JOB_TTL, "failed")
            _redis.setex(_job_key(tenant_id, job_id, "error"), JOB_TTL, error_msg)
        except Exception:
            _logger.exception(
                "score_bulk_task on_failure could not record failure to Redis"
            )
        _logger.exception(
            "score_bulk_task failed: job_id=%s tenant_id=%s", job_id, tenant_id
        )


@celery_app.task(
    bind=True,
    base=_ScoreBulkTask,
    name="paypredict.score_bulk.v1",
    max_retries=1,
)
def score_bulk_task(
    self,
    *,
    job_id: str,
    tenant_id: str,
    collections: list[dict],
    weights_by_method: dict[str, dict[str, float]],
) -> None:
    """Score a batch of collections asynchronously.

    Persists ScoreRequest + ScoreResult to the DB and writes progress +
    final results to Redis under per-tenant keys. Signature is
    keyword-only: positional dispatch raises TypeError, so an old
    positionally-queued message can't silently misbind across a deploy.

    Retry policy: `_persist_batch` is not idempotent (a retry restarts
    at row 0 and would double-persist any rows the failed attempt
    committed), so retries are gated on `persisted=False` — only
    pre-persistence transient blips retry. Anything after
    `_persist_batch` commits propagates to `on_failure` and lands as
    `status=failed`.
    """
    results = []
    summary = {"high_risk": 0, "medium_risk": 0, "low_risk": 0, "total_value_at_risk": 0.0}
    items_with_scores: list[tuple[dict, dict]] = []

    persisted = False
    try:
        for i, item in enumerate(collections):
            scored = _score_one(item, weights_by_method)
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

            _redis.setex(_job_key(tenant_id, job_id, "completed"), JOB_TTL, str(i + 1))

        score_ids = asyncio.run(
            _persist_batch(uuid.UUID(tenant_id), items_with_scores)
        )
        persisted = True

        for result_row, score_id in zip(results, score_ids):
            result_row["score_id"] = score_id

        _redis.setex(
            _job_key(tenant_id, job_id, "results"),
            JOB_TTL,
            json.dumps({"summary": summary, "results": results}),
        )
        _redis.setex(_job_key(tenant_id, job_id, "status"), JOB_TTL, "completed")
    except _TRANSIENT_ERRORS as exc:
        # Retry only when nothing has been written to Postgres. Post-persist
        # transient failures propagate to `on_failure` to avoid double-persistence.
        if not persisted:
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)
        raise
