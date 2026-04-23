"""Tests for GET /v1/outcomes (dashboard outcomes list)."""
import pytest

from tests.conftest import TEST_API_KEY, TEST_USER_EMAIL, TEST_USER_PASSWORD


async def _login(client) -> str:
    r = await client.post(
        "/v1/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )
    return r.json()["token"]


async def _create_score(client, *, customer_id: str = "cust_001") -> dict:
    """Create a score and return the response."""
    r = await client.post(
        "/v1/score",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        json={
            "external_customer_id": customer_id,
            "external_collection_id": f"col_{customer_id}",
            "collection_amount": 1500.00,
            "collection_currency": "ZAR",
            "collection_due_date": "2026-04-15",
            "collection_method": "CARD",
            "customer_data": {"total_payments": 10, "successful_payments": 7, "card_type": "debit"},
        },
    )
    assert r.status_code == 200
    return r.json()


async def _report_outcome(
    client,
    *,
    collection_id: str,
    outcome: str = "SUCCESS",
    score_id: str | None = None,
    failure_reason: str | None = None,
) -> dict:
    """Report an outcome via POST /v1/outcomes."""
    body: dict = {
        "external_collection_id": collection_id,
        "outcome": outcome,
        "attempted_at": "2026-04-15T08:00:00Z",
    }
    if score_id:
        body["score_id"] = score_id
    if failure_reason:
        body["failure_reason"] = failure_reason

    r = await client.post(
        "/v1/outcomes",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        json=body,
    )
    assert r.status_code == 201
    return r.json()


# ---- Tests ----


@pytest.mark.asyncio
async def test_list_outcomes_empty(async_client, sa_admin_user):
    """No outcomes → empty list with zeroed stats."""
    token = await _login(async_client)
    r = await async_client.get(
        "/v1/outcomes",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["items"] == []
    assert data["stats"]["total_outcomes"] == 0
    assert data["stats"]["success_rate"] == 0.0


@pytest.mark.asyncio
async def test_list_outcomes_with_linked_scores(async_client, sa_admin_user):
    """Outcomes linked to scores show prediction_matched."""
    token = await _login(async_client)

    # Create a score then report a SUCCESS outcome linked to it
    score = await _create_score(async_client, customer_id="linked_001")
    await _report_outcome(
        async_client,
        collection_id="col_linked_001",
        outcome="SUCCESS",
        score_id=score["score_id"],
    )

    r = await async_client.get(
        "/v1/outcomes",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["outcome"] == "SUCCESS"
    assert item["risk_level"] is not None
    assert item["score"] is not None
    assert item["prediction_matched"] is not None
    assert item["collection_method"] == "CARD"


@pytest.mark.asyncio
async def test_list_outcomes_unlinked(async_client, sa_admin_user):
    """Outcomes without a linked score have null prediction fields."""
    token = await _login(async_client)
    await _report_outcome(
        async_client, collection_id="col_no_link", outcome="FAILED", failure_reason="insufficient_funds"
    )

    r = await async_client.get(
        "/v1/outcomes",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = r.json()
    item = data["items"][0]
    assert item["risk_level"] is None
    assert item["prediction_matched"] is None
    assert item["failure_reason"] == "insufficient_funds"


@pytest.mark.asyncio
async def test_list_outcomes_filter_by_outcome(async_client, sa_admin_user):
    """Filter by outcome=SUCCESS shows only successes."""
    token = await _login(async_client)
    await _report_outcome(async_client, collection_id="f_s1", outcome="SUCCESS")
    await _report_outcome(async_client, collection_id="f_f1", outcome="FAILED")

    r = await async_client.get(
        "/v1/outcomes?outcome=SUCCESS",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = r.json()
    assert all(i["outcome"] == "SUCCESS" for i in data["items"])
    assert len(data["items"]) == 1


@pytest.mark.asyncio
async def test_list_outcomes_pagination(async_client, sa_admin_user):
    """Pagination works correctly."""
    token = await _login(async_client)
    for i in range(5):
        await _report_outcome(async_client, collection_id=f"pg_{i:03d}", outcome="SUCCESS")

    r = await async_client.get(
        "/v1/outcomes?page=1&page_size=2",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = r.json()
    assert len(data["items"]) == 2
    assert data["pagination"]["total_items"] == 5
    assert data["pagination"]["total_pages"] == 3


@pytest.mark.asyncio
async def test_list_outcomes_stats(async_client, sa_admin_user):
    """Stats block reflects the full filtered dataset."""
    token = await _login(async_client)

    # Create score + outcome pairs for prediction matching
    score1 = await _create_score(async_client, customer_id="stats_001")
    score2 = await _create_score(async_client, customer_id="stats_002")

    # Report outcomes linked to scores
    await _report_outcome(
        async_client, collection_id="col_stats_001",
        outcome="FAILED", score_id=score1["score_id"], failure_reason="insufficient_funds"
    )
    await _report_outcome(
        async_client, collection_id="col_stats_002",
        outcome="SUCCESS", score_id=score2["score_id"],
    )

    r = await async_client.get(
        "/v1/outcomes",
        headers={"Authorization": f"Bearer {token}"},
    )
    stats = r.json()["stats"]
    assert stats["total_outcomes"] == 2
    assert stats["success_count"] + stats["failed_count"] == 2
    assert 0.0 <= stats["success_rate"] <= 1.0
    assert 0.0 <= stats["match_rate"] <= 1.0


@pytest.mark.asyncio
async def test_list_outcomes_no_auth(async_client, sa_tenant):
    """No JWT → 401."""
    r = await async_client.get("/v1/outcomes")
    assert r.status_code == 401
