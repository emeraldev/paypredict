"""Regression tests for the bulk-scoring task's resilience surface.

Covers H3 (keyword-only signature + stable task name), H4 (terminal
state surfaces to the polling client even when things fail), and the
Stage-2 followup that moved job state from Redis to Postgres — so a
Redis outage during processing no longer leaves a job stuck on
`processing` until 1h TTL. The polling client always sees terminal
state as long as Postgres is reachable.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.models.bulk_scoring_job import BulkScoringJob, BulkScoringJobStatus
from app.services.bulk_scoring_service import get_job_status


# ---------------------------------------------------------------------------
# H3 — keyword-only signature + explicit task name
# ---------------------------------------------------------------------------


def test_score_bulk_task_is_keyword_only():
    """A positional `.delay(job_id, tenant_id, ...)` call must raise
    TypeError at dispatch — that's what prevents an old positionally-
    queued message from silently misbinding args after a signature
    change. Direct call because `.delay()` swallows args into a Celery
    envelope; the actual bind happens on the worker.
    """
    from app.tasks.bulk_scoring import score_bulk_task

    with pytest.raises(TypeError, match="positional"):
        score_bulk_task.run("job", "tenant", [], {})


def test_score_bulk_task_has_stable_name():
    """Explicit `name=` prevents a rename or file move from orphaning
    queued messages with NotRegistered."""
    from app.tasks.bulk_scoring import score_bulk_task

    assert score_bulk_task.name == "paypredict.score_bulk.v1"


# ---------------------------------------------------------------------------
# H4 — on_failure records terminal state in Postgres
# ---------------------------------------------------------------------------


def test_on_failure_writes_failed_status_and_error(sa_tenant_id_for_sync, monkeypatch):
    """Terminal failure surfaces to the polling endpoint via the
    `bulk_scoring_jobs` row (`status='failed'` + short `error`). Full
    traceback lives in the worker log, not in the row (SQLAlchemy
    exceptions leak query text + params).

    Runs synchronously via a fresh sync engine because Celery's
    `on_failure` uses `asyncio.run(...)` internally — that call
    crashes if we're already inside pytest-asyncio's event loop.
    Matches how a real Celery worker (a sync process) invokes it.
    """
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker

    from app.config import settings
    from app.tasks.bulk_scoring import score_bulk_task

    # The task's on_failure opens its own async engine keyed on
    # settings.database_url — point it at the test DB for this test
    # so it doesn't drop by-hand rows into dev.
    monkeypatch.setattr(settings, "database_url", settings.database_url_test)

    sync_dsn = settings.database_url_test.replace("+asyncpg", "+psycopg2")
    engine = create_engine(sync_dsn)
    Session = sessionmaker(engine)

    tenant_id, job_id = sa_tenant_id_for_sync
    try:
        # Seed the processing-state row via a straight sync insert; the
        # test's async_session fixture would need to commit through its
        # transaction wrapper, which conflicts with on_failure opening
        # its own connection to write.
        with Session() as db:
            db.execute(text(
                "INSERT INTO bulk_scoring_jobs "
                "(id, tenant_id, job_id, status, total_items, completed_items) "
                "VALUES (gen_random_uuid(), :tid, :jid, 'processing', 5, 0)"
            ), {"tid": str(tenant_id), "jid": str(job_id)})
            db.commit()

        exc = RuntimeError("db exploded" + "x" * 1000)
        score_bulk_task.on_failure(
            exc=exc,
            task_id="task-id-1",
            args=(),
            kwargs={"job_id": str(job_id), "tenant_id": str(tenant_id)},
            einfo=None,
        )

        with Session() as db:
            row = db.execute(text(
                "SELECT status, error FROM bulk_scoring_jobs WHERE job_id = :jid"
            ), {"jid": str(job_id)}).one()
        assert row.status == "failed"
        assert row.error is not None
        assert len(row.error) <= 500
        assert "db exploded" in row.error
    finally:
        # Clean up — this test bypasses the txn-rollback fixture.
        with Session() as db:
            db.execute(text("DELETE FROM bulk_scoring_jobs WHERE job_id = :jid"),
                       {"jid": str(job_id)})
            db.execute(text("DELETE FROM tenants WHERE id = :tid"),
                       {"tid": str(tenant_id)})
            db.commit()
        engine.dispose()


@pytest.fixture
def sa_tenant_id_for_sync():
    """Insert a real tenant via a sync engine (bypasses the txn
    fixture) for tests that need on_failure's separate-connection
    write to see it. Returns (tenant_id, job_id). Both are cleaned up
    by the caller."""
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker

    from app.config import settings

    sync_dsn = settings.database_url_test.replace("+asyncpg", "+psycopg2")
    engine = create_engine(sync_dsn)
    Session = sessionmaker(engine)
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()
    with Session() as db:
        db.execute(text(
            "INSERT INTO tenants (id, name, market, factor_set, plan, "
            "is_active, alert_threshold, webhook_secret, email_recipients) "
            "VALUES (:id, 'onfailure-test', 'ZM', 'CUSTOM', 'PILOT', true, "
            "0.2, 'x', '{}')"
        ), {"id": str(tenant_id)})
        db.commit()
    engine.dispose()
    return tenant_id, job_id


def test_on_failure_when_postgres_write_fails_does_not_raise(monkeypatch):
    """If the failure that killed the task was `OperationalError`
    (connection blip), letting the recorder raise would swallow the
    real traceback under a spurious one. `on_failure` must swallow
    the recorder's own error."""
    from app.tasks import bulk_scoring as task_module

    async def _boom(*args, **kwargs):
        raise ConnectionError("postgres down too")

    monkeypatch.setattr(task_module, "_record_failure", _boom)

    task_module.score_bulk_task.on_failure(
        exc=RuntimeError("original"),
        task_id="task-id-2",
        args=(),
        kwargs={"job_id": str(uuid.uuid4()), "tenant_id": str(uuid.uuid4())},
        einfo=None,
    )


def test_on_failure_with_missing_kwargs_logs_and_returns():
    """A malformed task invocation with no job_id/tenant_id shouldn't
    crash the failure handler — just log and return."""
    from app.tasks.bulk_scoring import score_bulk_task

    score_bulk_task.on_failure(
        exc=RuntimeError("orphan"),
        task_id="task-id-3",
        args=(),
        kwargs={},
        einfo=None,
    )


# ---------------------------------------------------------------------------
# get_job_status is Postgres-backed and tenant-scoped
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_job_status_returns_row_for_owning_tenant(db_session, sa_tenant):
    job_id = uuid.uuid4()
    db_session.add(BulkScoringJob(
        tenant_id=sa_tenant.id,
        job_id=job_id,
        status=BulkScoringJobStatus.FAILED,
        total_items=10,
        completed_items=3,
        error="short message",
    ))
    await db_session.commit()

    state = await get_job_status(db_session, str(sa_tenant.id), str(job_id))
    assert state == {
        "job_id": str(job_id),
        "status": "failed",
        "total_items": 10,
        "completed_items": 3,
        "error": "short message",
    }


@pytest.mark.asyncio
async def test_get_job_status_returns_none_for_other_tenant(
    db_session, sa_tenant, zm_tenant
):
    """Structural cross-tenant guarantee: UNIQUE (tenant_id, job_id)
    means a caller cannot construct a matching row from their own
    tenant_id + a leaked job_id. get_job_status returns None,
    indistinguishable from `not found or expired`."""
    job_id = uuid.uuid4()
    db_session.add(BulkScoringJob(
        tenant_id=sa_tenant.id,
        job_id=job_id,
        status=BulkScoringJobStatus.COMPLETED,
        total_items=5,
        completed_items=5,
    ))
    await db_session.commit()

    state = await get_job_status(db_session, str(zm_tenant.id), str(job_id))
    assert state is None
