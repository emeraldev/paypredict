"""Tests for GET /v1/scores and GET /v1/scores/{score_id}."""
import pytest

from tests.conftest import TEST_API_KEY, TEST_USER_EMAIL, TEST_USER_PASSWORD


async def _login(client) -> str:
    """Log in and return the JWT token."""
    r = await client.post(
        "/v1/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )
    return r.json()["token"]


async def _create_score(client, *, customer_id: str = "cust_001", amount: float = 1500.0):
    """Create a score via the lender-facing POST endpoint and return the response."""
    r = await client.post(
        "/v1/score",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        json={
            "external_customer_id": customer_id,
            "external_collection_id": f"col_{customer_id}",
            "collection_amount": amount,
            "collection_currency": "ZAR",
            "collection_due_date": "2026-04-15",
            "collection_method": "CARD",
            "customer_data": {
                "total_payments": 10,
                "successful_payments": 7,
                "card_type": "debit",
                "instalment_number": 3,
                "total_instalments": 6,
            },
        },
    )
    assert r.status_code == 200
    return r.json()


# ---- List ----


@pytest.mark.asyncio
async def test_list_scores_empty(async_client, sa_admin_user):
    """No scores → empty list with zeroed summary."""
    token = await _login(async_client)
    r = await async_client.get(
        "/v1/scores",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["items"] == []
    assert data["pagination"]["total_items"] == 0
    assert data["summary"]["high_risk"] == 0


@pytest.mark.asyncio
async def test_list_scores_returns_items(async_client, sa_admin_user):
    """Create scores then list them."""
    token = await _login(async_client)

    # Create 3 scores
    for i in range(3):
        await _create_score(async_client, customer_id=f"cust_{i:03d}", amount=1000 + i)

    r = await async_client.get(
        "/v1/scores",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) == 3
    assert data["pagination"]["total_items"] == 3
    # Items should have expected fields
    item = data["items"][0]
    assert "score_id" in item
    assert "score" in item
    assert "risk_level" in item
    assert "collection_method" in item
    assert "instalment_number" in item


@pytest.mark.asyncio
async def test_list_scores_pagination(async_client, sa_admin_user):
    """Pagination returns correct page counts."""
    token = await _login(async_client)

    for i in range(5):
        await _create_score(async_client, customer_id=f"cust_{i:03d}")

    r = await async_client.get(
        "/v1/scores?page=1&page_size=2",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = r.json()
    assert len(data["items"]) == 2
    assert data["pagination"]["total_items"] == 5
    assert data["pagination"]["total_pages"] == 3
    assert data["pagination"]["page"] == 1

    # Page 3 should have 1 item
    r2 = await async_client.get(
        "/v1/scores?page=3&page_size=2",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert len(r2.json()["items"]) == 1


@pytest.mark.asyncio
async def test_list_scores_search(async_client, sa_admin_user):
    """Search by customer ID."""
    token = await _login(async_client)
    await _create_score(async_client, customer_id="alice_123")
    await _create_score(async_client, customer_id="bob_456")

    r = await async_client.get(
        "/v1/scores?search=alice",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = r.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["external_customer_id"] == "alice_123"


@pytest.mark.asyncio
async def test_list_scores_sort(async_client, sa_admin_user):
    """Sort by collection_amount ascending."""
    token = await _login(async_client)
    await _create_score(async_client, customer_id="c1", amount=3000)
    await _create_score(async_client, customer_id="c2", amount=500)
    await _create_score(async_client, customer_id="c3", amount=1500)

    r = await async_client.get(
        "/v1/scores?sort_by=collection_amount&sort_order=asc",
        headers={"Authorization": f"Bearer {token}"},
    )
    amounts = [float(i["collection_amount"]) for i in r.json()["items"]]
    assert amounts == sorted(amounts)


@pytest.mark.asyncio
async def test_list_scores_no_auth(async_client, sa_tenant):
    """No JWT → 401."""
    r = await async_client.get("/v1/scores")
    assert r.status_code == 401


# ---- Detail ----


@pytest.mark.asyncio
async def test_score_detail(async_client, sa_admin_user):
    """GET /scores/{id} returns full breakdown."""
    token = await _login(async_client)
    score = await _create_score(async_client, customer_id="detail_test")

    r = await async_client.get(
        f"/v1/scores/{score['score_id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["score_id"] == score["score_id"]
    assert len(data["factors"]) > 0
    assert "customer_context" in data
    assert data["customer_context"]["total_payments"] == 10
    assert data["outcome"] is None  # no outcome linked yet


@pytest.mark.asyncio
async def test_score_detail_not_found(async_client, sa_admin_user):
    """Non-existent score → 404."""
    token = await _login(async_client)
    r = await async_client.get(
        "/v1/scores/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_summary_counts_reflect_filters(async_client, sa_admin_user):
    """Summary counts should reflect active filters, not all data."""
    token = await _login(async_client)

    # Create scores (different amounts so they might land in different risk buckets)
    for i in range(5):
        await _create_score(async_client, customer_id=f"sf_{i:03d}", amount=200 + i * 100)

    # Get unfiltered
    r1 = await async_client.get(
        "/v1/scores",
        headers={"Authorization": f"Bearer {token}"},
    )
    total_unfiltered = r1.json()["pagination"]["total_items"]

    # Get filtered by due_date (all our scores are due 2026-04-15)
    r2 = await async_client.get(
        "/v1/scores?due_date_from=2030-01-01",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.json()["pagination"]["total_items"] == 0
    # Summary should also be zeroed
    s = r2.json()["summary"]
    assert s["high_risk"] + s["medium_risk"] + s["low_risk"] == 0
