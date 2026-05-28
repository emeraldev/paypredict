"""Tests for POST /v1/outcomes endpoint."""

import pytest

from tests.conftest import TEST_API_KEY, TEST_USER_EMAIL, TEST_USER_PASSWORD


async def _score(client, collection_id: str) -> str:
    """Helper — score a CARD collection and return the score_id."""
    r = await client.post(
        "/v1/score",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        json={
            "customer_id": "cust_link",
            "collection_id": collection_id,
            "collection_amount": 1500,
            "collection_currency": "ZAR",
            "collection_due_date": "2026-08-15",
            "collection_method": "CARD",
            "customer_data": {"total_payments": 5, "successful_payments": 3},
        },
    )
    assert r.status_code == 200, r.text
    return r.json()["score_id"]


@pytest.mark.asyncio
async def test_outcome_success(async_client, sa_tenant):
    response = await async_client.post(
        "/v1/outcomes",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        json={
            "collection_id": "col_001",
            "outcome": "SUCCESS",
            "attempted_at": "2026-04-15T08:00:00Z",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "outcome_id" in data
    assert data["linked_score_id"] is None
    assert "received_at" in data


@pytest.mark.asyncio
async def test_outcome_failed_with_reason(async_client, sa_tenant):
    response = await async_client.post(
        "/v1/outcomes",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        json={
            "collection_id": "col_002",
            "outcome": "FAILED",
            "failure_reason": "insufficient_funds",
            "attempted_at": "2026-04-15T08:00:00Z",
        },
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_outcome_no_auth(async_client):
    response = await async_client.post(
        "/v1/outcomes",
        json={
            "collection_id": "col_001",
            "outcome": "SUCCESS",
            "attempted_at": "2026-04-15T08:00:00Z",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_outcome_validation_error(async_client, sa_tenant):
    response = await async_client.post(
        "/v1/outcomes",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        json={
            "collection_id": "col_001",
            "outcome": "INVALID_STATUS",
            "attempted_at": "2026-04-15T08:00:00Z",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_outcome_auto_links_by_collection_id(async_client, sa_tenant):
    """Lender omits score_id — backend back-links to the un-outcomed score
    for the same collection_id."""
    score_id = await _score(async_client, "col_auto_001")

    r = await async_client.post(
        "/v1/outcomes",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        json={
            "collection_id": "col_auto_001",
            "outcome": "FAILED",
            "failure_reason": "insufficient_funds",
            "attempted_at": "2026-08-16T08:00:00Z",
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["linked_score_id"] == score_id


@pytest.mark.asyncio
async def test_outcome_auto_link_picks_most_recent_unoutcomed(
    async_client, sa_tenant
):
    """Two scores for the same collection_id — second outcome should link to
    the second (most recent) score, not the first that's already outcomed."""
    first_score_id = await _score(async_client, "col_dup")
    # Outcome the first score with explicit score_id
    r = await async_client.post(
        "/v1/outcomes",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        json={
            "score_id": first_score_id,
            "collection_id": "col_dup",
            "outcome": "FAILED",
            "attempted_at": "2026-08-16T08:00:00Z",
        },
    )
    assert r.status_code == 201
    assert r.json()["linked_score_id"] == first_score_id

    # Re-score the same collection
    second_score_id = await _score(async_client, "col_dup")

    # Now omit score_id — should link to second_score_id, not the already-outcomed first
    r = await async_client.post(
        "/v1/outcomes",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        json={
            "collection_id": "col_dup",
            "outcome": "SUCCESS",
            "attempted_at": "2026-08-17T08:00:00Z",
        },
    )
    assert r.status_code == 201
    assert r.json()["linked_score_id"] == second_score_id


@pytest.mark.asyncio
async def test_outcome_no_match_records_unlinked(async_client, sa_tenant):
    """No score exists for the collection_id — outcome still recorded, just
    unlinked. Doesn't crash."""
    r = await async_client.post(
        "/v1/outcomes",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        json={
            "collection_id": "col_never_scored",
            "outcome": "SUCCESS",
            "attempted_at": "2026-08-15T08:00:00Z",
        },
    )
    assert r.status_code == 201
    assert r.json()["linked_score_id"] is None


@pytest.mark.asyncio
async def test_outcome_via_dashboard_jwt(async_client, sa_admin_user):
    """The dashboard 'Report outcome' form posts with JWT (no API key)."""
    r = await async_client.post(
        "/v1/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )
    token = r.json()["token"]

    score_id = await _score(async_client, "col_jwt_outcome")

    r = await async_client.post(
        "/v1/outcomes",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "score_id": score_id,
            "collection_id": "col_jwt_outcome",
            "outcome": "FAILED",
            "failure_reason": "insufficient_funds",
            "attempted_at": "2026-08-16T08:00:00Z",
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["linked_score_id"] == score_id
    # No rate-limit headers on JWT path.
    assert "x-ratelimit-limit" not in {k.lower() for k in r.headers}
