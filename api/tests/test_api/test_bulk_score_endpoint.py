"""Tests for POST /v1/score/bulk (sync path, <= 50 items)."""
import pytest

from tests.conftest import TEST_API_KEY


def _sample_items(count: int = 5) -> list[dict]:
    return [
        {
            "external_customer_id": f"cust_{i:03d}",
            "external_collection_id": f"col_{i:03d}",
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
                    "external_customer_id": "c1",
                    "external_collection_id": "col1",
                    "collection_amount": -100,  # invalid
                    "collection_currency": "INVALID",
                    "collection_due_date": "2026-04-15",
                    "collection_method": "CARD",
                }
            ]
        },
    )
    assert r.status_code == 422
