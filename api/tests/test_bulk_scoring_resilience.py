"""Regression tests for the bulk resilience fixes (H3, H4, H5).

Kept in a dedicated file because they exercise Celery task internals
(`_ScoreBulkTask.on_failure`, retry gating) and the notification
template-formatter, none of which fit cleanly into the existing
endpoint-level test files.
"""
from __future__ import annotations

import pytest

from app.services.bulk_scoring_service import _job_key, _redis, get_job_status
from app.services.notification_service import EventType, _TEMPLATES


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
        # `run` invokes the task synchronously with the same signature
        # a worker would use.
        score_bulk_task.run("job", "tenant", [], {})


def test_score_bulk_task_has_stable_name():
    """Explicit `name=` prevents a rename or file move from orphaning
    queued messages with NotRegistered."""
    from app.tasks.bulk_scoring import score_bulk_task

    assert score_bulk_task.name == "paypredict.score_bulk.v1"


# ---------------------------------------------------------------------------
# H4 — on_failure records status + short error to Redis
# ---------------------------------------------------------------------------


def test_on_failure_writes_failed_status_and_error():
    """Terminal failure surfaces to the polling endpoint via `status=failed`
    + a short `error` message. Full traceback lives in the worker log,
    not in Redis (SQLAlchemy exceptions leak query text + params)."""
    from app.tasks.bulk_scoring import score_bulk_task

    tenant_id = "on-failure-tenant"
    job_id = "on-failure-job"
    exc = RuntimeError("db exploded" + "x" * 1000)

    try:
        score_bulk_task.on_failure(
            exc=exc,
            task_id="task-id-1",
            args=(),
            kwargs={"job_id": job_id, "tenant_id": tenant_id},
            einfo=None,
        )

        state = get_job_status(tenant_id, job_id)
        assert state is not None
        assert state["status"] == "failed"
        assert "error" in state
        assert len(state["error"]) <= 500, "error message must be truncated"
        assert "db exploded" in state["error"]
    finally:
        for suffix in ("status", "error"):
            _redis.delete(_job_key(tenant_id, job_id, suffix))


def test_on_failure_when_redis_write_fails_does_not_raise(monkeypatch):
    """If the failure that killed the task was `redis.ConnectionError`,
    letting the recorder raise would swallow the real traceback under
    a spurious one. `on_failure` must swallow the recorder's own error."""
    from app.tasks import bulk_scoring as task_module

    def _boom(*args, **kwargs):
        raise ConnectionError("redis down too")

    monkeypatch.setattr(task_module._redis, "setex", _boom)

    # Should not raise.
    task_module.score_bulk_task.on_failure(
        exc=RuntimeError("original"),
        task_id="task-id-2",
        args=(),
        kwargs={"job_id": "j", "tenant_id": "t"},
        einfo=None,
    )


def test_on_failure_with_missing_kwargs_logs_and_returns():
    """A malformed task invocation with no job_id/tenant_id shouldn't
    crash the failure handler — just log and return."""
    from app.tasks.bulk_scoring import score_bulk_task

    # No kwargs at all — handler should log the exception then return.
    score_bulk_task.on_failure(
        exc=RuntimeError("orphan"),
        task_id="task-id-3",
        args=(),
        kwargs={},
        einfo=None,
    )


# ---------------------------------------------------------------------------
# H4 — get_job_status returns failed + error to the poller
# ---------------------------------------------------------------------------


def test_get_job_status_surfaces_failed_and_error():
    """A completed 'failed' job should return status=failed with the
    error message so the polling client sees a terminal state rather
    than eternal 'processing'."""
    tenant_id = "get-status-tenant"
    job_id = "get-status-job"
    try:
        _redis.setex(_job_key(tenant_id, job_id, "status"), 60, "failed")
        _redis.setex(_job_key(tenant_id, job_id, "total"), 60, "10")
        _redis.setex(_job_key(tenant_id, job_id, "completed"), 60, "3")
        _redis.setex(_job_key(tenant_id, job_id, "error"), 60, "short message")

        state = get_job_status(tenant_id, job_id)
        assert state == {
            "job_id": job_id,
            "status": "failed",
            "total_items": 10,
            "completed_items": 3,
            "error": "short message",
        }
    finally:
        for suffix in ("status", "total", "completed", "error"):
            _redis.delete(_job_key(tenant_id, job_id, suffix))


# ---------------------------------------------------------------------------
# H5 — notification template formatter tolerates broken templates
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_notification_swallows_format_typeerror(db_session, sa_tenant):
    """Templates like `{percentage:.0%}` raise TypeError (not KeyError)
    when the metadata carries a non-numeric value. Pre-fix this bubbled
    out of `create_notification` and would abort the caller's
    transaction — for bulk scoring, wiping every scored row (H5).
    """
    from app.services.notification_service import create_notification

    # HIGH_RISK_BATCH template uses `{percentage:.0%}`. Handing it a
    # string triggers TypeError inside `.format()`.
    notif = await create_notification(
        db_session,
        sa_tenant.id,
        EventType.HIGH_RISK_BATCH,
        metadata={
            "high_risk_count": 5,
            "total_count": 10,
            "percentage": "not-a-number",  # would blow up .0% formatting
            "threshold": 0.2,
        },
    )

    # Notification was still created, message fell back to the raw template.
    assert notif is not None
    assert notif.message == _TEMPLATES[EventType.HIGH_RISK_BATCH]["message"]


@pytest.mark.asyncio
async def test_create_notification_swallows_link_format_error(
    db_session, sa_tenant, monkeypatch
):
    """Same defense for `link_to`. No shipped template contains a
    placeholder in `link_to` today, so we inject one temporarily to
    keep the branch exercised — the defense needs to survive the day
    someone adds a templated link and forgets the missing-metadata
    case."""
    from app.services import notification_service
    from app.services.notification_service import create_notification

    injected = dict(notification_service._TEMPLATES[EventType.BACKTEST_COMPLETE])
    injected["link_to"] = "/dashboard/backtest/{backtest_id}"
    monkeypatch.setitem(
        notification_service._TEMPLATES, EventType.BACKTEST_COMPLETE, injected
    )

    # backtest_id deliberately omitted from metadata.
    notif = await create_notification(
        db_session,
        sa_tenant.id,
        EventType.BACKTEST_COMPLETE,
        metadata={"total_collections": 100, "accuracy": 0.85},
    )

    assert notif is not None
    # Link fell back to the raw template — placeholder still literal.
    assert notif.link_to == "/dashboard/backtest/{backtest_id}"
