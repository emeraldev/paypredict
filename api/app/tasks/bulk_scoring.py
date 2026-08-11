"""Celery task for async bulk scoring (> 50 items).

Job state (status, progress, results, error) lives in Postgres —
the `bulk_scoring_jobs` table is the source of truth. This replaced
the previous Redis-only design after PR #37 (H4) surfaced the failure
mode where Redis being down at the moment `on_failure` fired lost the
failure record entirely. Postgres survives Redis outages, so terminal
transitions always land somewhere the customer can observe.

Celery still uses Redis as the broker + result backend, so a real
Redis outage still stops NEW tasks from being queued. This task's
resilience improvement is specifically about the observability of
tasks that are ALREADY running when Redis blips.
"""
import asyncio
import json
import logging
import uuid
from datetime import date as _date, datetime, timezone
from decimal import Decimal

import redis
from sqlalchemy import update
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models.bulk_scoring_job import BulkScoringJob, BulkScoringJobStatus
from app.models.score_request import CollectionCurrency, CollectionMethod, ScoreRequest
from app.models.score_result import RiskLevel, ScoreResult
from app.scoring.engine import ScoringEngine
from app.services.bulk_scoring_service import (
    _factor_to_db_shape,
    _score_one,
    _to_json_safe,
)
from app.tasks.celery_app import celery_app

_engine = ScoringEngine()
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


# Trim exception text before it reaches Postgres (and eventually the
# customer's polling response). SQLAlchemy messages include query text
# and bound params; full traceback stays in the worker log.
_ERROR_MSG_MAX = 500


async def _update_job_progress(
    engine, tenant_id: str, job_id: str, completed_items: int
) -> None:
    """Bump `completed_items` on the job row. Called once per scored
    item — cheap Postgres write, keeps the polling client's progress
    counter live during processing."""
    async with async_sessionmaker(engine, expire_on_commit=False)() as db:
        await db.execute(
            update(BulkScoringJob)
            .where(
                BulkScoringJob.tenant_id == uuid.UUID(tenant_id),
                BulkScoringJob.job_id == uuid.UUID(job_id),
            )
            .values(completed_items=completed_items)
        )
        await db.commit()


async def _persist_batch_and_finalize(
    tenant_id: str,
    job_id: str,
    items_with_scores: list[tuple[dict, dict]],
    summary: dict,
    results: list[dict],
) -> None:
    """Insert every ScoreRequest+ScoreResult row AND write the terminal
    job state, all in one transaction.

    Coupling the two writes means a crash between "rows persisted" and
    "job marked complete" can't leave a job stuck on `processing` with
    all its data already in Postgres. Either both land or both roll
    back — the retry gate outside catches the rollback case cleanly.
    """
    engine = create_async_engine(settings.database_url, echo=False)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            tenant_uuid = uuid.UUID(tenant_id)
            score_ids: list[str] = []
            for item, scored in items_with_scores:
                payload = _to_json_safe(item)
                due_date = item["collection_due_date"]
                if isinstance(due_date, str):
                    due_date = _date.fromisoformat(due_date)

                req = ScoreRequest(
                    id=uuid.uuid4(),
                    tenant_id=tenant_uuid,
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
                    tenant_id=tenant_uuid,
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

            # Attach score_ids to inline results in-place so the poller
            # response matches the sync path's shape.
            for result_row, score_id in zip(results, score_ids):
                result_row["score_id"] = score_id

            # Terminal state written in the SAME transaction as the
            # score rows. All-or-nothing.
            await db.execute(
                update(BulkScoringJob)
                .where(
                    BulkScoringJob.tenant_id == tenant_uuid,
                    BulkScoringJob.job_id == uuid.UUID(job_id),
                )
                .values(
                    status=BulkScoringJobStatus.COMPLETED,
                    completed_items=len(results),
                    summary=summary,
                    # JSON-serialisable copy — the inline result dicts contain
                    # date and UUID values that would confuse asyncpg's JSONB
                    # encoder if handed directly.
                    results=json.loads(json.dumps(results, default=str)),
                    completed_at=datetime.now(timezone.utc),
                )
            )

            await db.commit()
    finally:
        await engine.dispose()


class _ScoreBulkTask(celery_app.Task):
    """Base class exposing `on_failure` so a terminal (post-retry) failure
    surfaces to the polling endpoint via a Postgres write.

    Runs in its own connection lifecycle: the task body's session may
    already be gone by the time we get here (that's the whole point of
    `on_failure` — the body failed). Open a fresh short-lived engine,
    do one UPDATE, dispose. The write is also wrapped in try/except so
    a Postgres outage during failure recording doesn't hide the
    original traceback.
    """

    def on_failure(self, exc, task_id, args, kwargs, einfo):  # type: ignore[override]
        job_id = kwargs.get("job_id")
        tenant_id = kwargs.get("tenant_id")
        if not job_id or not tenant_id:
            _logger.exception(
                "score_bulk_task failed but couldn't locate job/tenant "
                "kwargs — cannot record failure to Postgres"
            )
            return
        error_msg = repr(exc)[:_ERROR_MSG_MAX]
        try:
            asyncio.run(_record_failure(tenant_id, job_id, error_msg))
        except Exception:
            _logger.exception(
                "score_bulk_task on_failure could not record failure to Postgres"
            )
        _logger.exception(
            "score_bulk_task failed: job_id=%s tenant_id=%s", job_id, tenant_id
        )


async def _record_failure(tenant_id: str, job_id: str, error_msg: str) -> None:
    engine = create_async_engine(settings.database_url, echo=False)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            await db.execute(
                update(BulkScoringJob)
                .where(
                    BulkScoringJob.tenant_id == uuid.UUID(tenant_id),
                    BulkScoringJob.job_id == uuid.UUID(job_id),
                )
                .values(
                    status=BulkScoringJobStatus.FAILED,
                    error=error_msg,
                    completed_at=datetime.now(timezone.utc),
                )
            )
            await db.commit()
    finally:
        await engine.dispose()


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

    Persists ScoreRequest + ScoreResult rows AND the terminal
    `bulk_scoring_jobs` transition in one Postgres transaction.
    Progress (`completed_items`) is bumped per row so a polling
    client sees live progress.

    Retry policy: `_persist_batch_and_finalize` isn't idempotent (a
    retry restarts at row 0 and would double-persist any rows the
    failed attempt committed), so retries are gated on
    `persisted=False` — only pre-persistence transient blips retry.
    Anything after the terminal commit propagates to `on_failure` and
    lands as `status=failed`.
    """
    progress_engine = create_async_engine(settings.database_url, echo=False)

    results: list[dict] = []
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

            asyncio.run(_update_job_progress(progress_engine, tenant_id, job_id, i + 1))

        asyncio.run(
            _persist_batch_and_finalize(
                tenant_id, job_id, items_with_scores, summary, results,
            )
        )
        persisted = True
    except _TRANSIENT_ERRORS as exc:
        # Retry only when nothing has been written to Postgres. Post-persist
        # transient failures propagate to `on_failure` to avoid double-persistence.
        if not persisted:
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)
        raise
    finally:
        asyncio.run(progress_engine.dispose())
