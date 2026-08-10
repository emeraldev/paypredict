"""Tests for POST /v1/score/bulk (sync path, <= 50 items)."""
import uuid

import pytest
from sqlalchemy import select

from app.models.score_result import ScoreResult
from tests.conftest import TEST_API_KEY


def _sample_items(count: int = 5) -> list[dict]:
    return [
        {
            "customer_id": f"cust_{i:03d}",
            "collection_id": f"col_{i:03d}",
            "collection_amount": 1000 + i * 100,
            "collection_currency": "ZAR",
            "collection_due_date": "2026-04-15",
            "collection_method": "CARD",
            "customer_data": {
                "total_payments": 10,
                "successful_payments": 7 if i % 2 == 0 else 3,
                "card_type": "debit",
            },
        }
        for i in range(count)
    ]


@pytest.mark.asyncio
async def test_bulk_score_sync(async_client, sa_tenant):
    """Sync bulk scoring (<=50 items) returns results inline."""
    r = await async_client.post(
        "/v1/score/bulk",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        json={"collections": _sample_items(5)},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "completed"
    assert data["total_items"] == 5
    assert data["completed_items"] == 5
    assert len(data["results"]) == 5

    # Each result has a score_id (persisted)
    for result in data["results"]:
        assert "score_id" in result
        assert 0.0 <= result["score"] <= 1.0
        assert result["risk_level"] in ("LOW", "MEDIUM", "HIGH")
        assert len(result["factors"]) > 0

    # Summary counts
    s = data["summary"]
    assert s["high_risk"] + s["medium_risk"] + s["low_risk"] == 5


@pytest.mark.asyncio
async def test_bulk_score_single_item(async_client, sa_tenant):
    """Bulk with 1 item works."""
    r = await async_client.post(
        "/v1/score/bulk",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        json={"collections": _sample_items(1)},
    )
    assert r.status_code == 200
    assert r.json()["total_items"] == 1


@pytest.mark.asyncio
async def test_bulk_score_max_sync(async_client, sa_tenant):
    """50 items still processes synchronously."""
    r = await async_client.post(
        "/v1/score/bulk",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        json={"collections": _sample_items(50)},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "completed"
    assert r.json()["total_items"] == 50


@pytest.mark.asyncio
async def test_bulk_score_persists_factor_name_key(async_client, sa_tenant, db_session):
    """Bulk-scored rows must persist with the canonical 'factor_name' JSONB
    key (not 'factor'). Analytics reads 'factor_name'; the legacy 'factor'
    key was a bug that produced blank Top Failure Contributors charts."""
    r = await async_client.post(
        "/v1/score/bulk",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        json={"collections": _sample_items(2)},
    )
    assert r.status_code == 200
    score_ids = [uuid.UUID(item["score_id"]) for item in r.json()["results"]]

    # Read back the persisted JSONB shape.
    rows = (
        await db_session.execute(
            select(ScoreResult.factors).where(ScoreResult.id.in_(score_ids))
        )
    ).all()
    assert len(rows) == 2
    for (factors,) in rows:
        evaluated = factors["evaluated"]
        assert evaluated, "evaluated list must not be empty"
        for entry in evaluated:
            assert "factor_name" in entry, (
                f"DB row uses legacy 'factor' key instead of 'factor_name': {entry}"
            )
            assert "factor" not in entry


@pytest.mark.asyncio
async def test_bulk_score_no_auth(async_client):
    """No API key → 401."""
    r = await async_client.post(
        "/v1/score/bulk",
        json={"collections": _sample_items(1)},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_bulk_score_empty(async_client, sa_tenant):
    """Empty collections → 422."""
    r = await async_client.post(
        "/v1/score/bulk",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        json={"collections": []},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_bulk_score_validation_error(async_client, sa_tenant):
    """Invalid collection data → 422."""
    r = await async_client.post(
        "/v1/score/bulk",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        json={
            "collections": [
                {
                    "customer_id": "c1",
                    "collection_id": "col1",
                    "collection_amount": -100,  # invalid
                    "collection_currency": "INVALID",
                    "collection_due_date": "2026-04-15",
                    "collection_method": "CARD",
                }
            ]
        },
    )
    assert r.status_code == 422


# ==================== H1: bulk-job cross-tenant leak ====================

@pytest.mark.asyncio
async def test_bulk_job_poll_scoped_by_tenant(async_client, sa_tenant, zm_tenant):
    """Regression for H1. Tenant A queues a job; tenant B polling that
    job_id must get 404 (identical shape to "not found or expired" —
    do NOT differentiate or existence leaks). The Redis key namespace
    `bulk_job:{tenant_id}:{job_id}` makes this a structural guarantee
    rather than a runtime check."""
    from app.services.bulk_scoring_service import queue_bulk_job, get_job_status

    # Tenant A queues a job — we only need the job_id, not real Celery.
    weights_by_method: dict[str, dict[str, float]] = {}
    job = queue_bulk_job(
        tenant_id=str(sa_tenant.id),
        collections=_sample_items(1),
        weights_by_method=weights_by_method,
    )
    job_id = job["job_id"]

    # Same tenant sees status.
    same_tenant = get_job_status(str(sa_tenant.id), job_id)
    assert same_tenant is not None, "owner must see their own job"
    assert same_tenant["status"] == "processing"

    # Different tenant sees nothing — indistinguishable from "not found".
    other_tenant = get_job_status(str(zm_tenant.id), job_id)
    assert other_tenant is None, "cross-tenant poll must return None"

    # Cleanup so the fake Redis job doesn't hang around for another test.
    from app.services.bulk_scoring_service import _redis, _job_key
    for suffix in ("status", "total", "completed", "results"):
        _redis.delete(_job_key(str(sa_tenant.id), job_id, suffix))
