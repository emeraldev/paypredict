"""Tests for POST /v1/score endpoint."""

import pytest

from tests.conftest import TEST_API_KEY


@pytest.mark.asyncio
async def test_score_success(async_client, sa_tenant):
    response = await async_client.post(
        "/v1/score",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        json={
            "external_customer_id": "cust_001",
            "external_collection_id": "col_001",
            "collection_amount": 1500.00,
            "collection_currency": "ZAR",
            "collection_due_date": "2026-04-15",
            "collection_method": "CARD",
            "customer_data": {
                "total_payments": 10,
                "successful_payments": 7,
                "card_type": "debit",
            },
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "score_id" in data
    assert 0.0 <= data["score"] <= 1.0
    assert data["risk_level"] in ("LOW", "MEDIUM", "HIGH")
    assert len(data["factors"]) == 7  # CARD skips debit_order_return_history
    assert "debit_order_return_history" in data["skipped_factors"]
    assert data["model_version"] == "heuristic_card_v1"
    assert data["scoring_duration_ms"] >= 1


@pytest.mark.asyncio
async def test_score_no_auth(async_client):
    response = await async_client.post(
        "/v1/score",
        json={
            "external_customer_id": "cust_001",
            "external_collection_id": "col_001",
            "collection_amount": 1500.00,
            "collection_currency": "ZAR",
            "collection_due_date": "2026-04-15",
            "collection_method": "CARD",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_score_invalid_key(async_client, sa_tenant):
    response = await async_client.post(
        "/v1/score",
        headers={"Authorization": "Bearer pk_test_totally_invalid_key_here!!"},
        json={
            "external_customer_id": "cust_001",
            "external_collection_id": "col_001",
            "collection_amount": 1500.00,
            "collection_currency": "ZAR",
            "collection_due_date": "2026-04-15",
            "collection_method": "CARD",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_score_validation_error(async_client, sa_tenant):
    response = await async_client.post(
        "/v1/score",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        json={
            "external_customer_id": "cust_001",
            # Missing required fields
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_score_minimal_customer_data(async_client, sa_tenant):
    """Score with no customer_data — all factors should use defaults."""
    response = await async_client.post(
        "/v1/score",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        json={
            "external_customer_id": "cust_002",
            "external_collection_id": "col_002",
            "collection_amount": 500.00,
            "collection_currency": "ZAR",
            "collection_due_date": "2026-04-10",
            "collection_method": "CARD",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["factors"]) == 7  # CARD skips debit_order_return_history


@pytest.mark.asyncio
async def test_score_response_includes_timing_optimiser_fields(async_client, sa_tenant):
    """The new timing-optimiser fields are present on every response.
    For a request that doesn't warrant a shift, they are null and the
    action is the standard risk-level mapping."""
    response = await async_client.post(
        "/v1/score",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        json={
            "external_customer_id": "cust_no_shift",
            "external_collection_id": "col_no_shift",
            "collection_amount": 1500.00,
            "collection_currency": "ZAR",
            # No known_salary_day; due date in the lowest-risk window per
            # SA defaults (day <= 5 → 0.1).
            "collection_due_date": "2027-04-03",
            "collection_method": "CARD",
            "customer_data": {
                "total_payments": 20,
                "successful_payments": 19,
                "card_type": "debit",
            },
        },
    )
    assert response.status_code == 200
    data = response.json()
    # New fields are present on the response shape, even when not used.
    assert "recommended_collection_date" in data
    assert "recommended_score" in data
    assert "score_improvement" in data
    # No shift warranted → all three are null, action is the risk-level default.
    assert data["recommended_collection_date"] is None
    assert data["recommended_score"] is None
    assert data["score_improvement"] is None
    assert data["recommended_action"] != "shift_date"


@pytest.mark.asyncio
async def test_score_recommends_shift_when_timing_is_bad(async_client, sa_tenant):
    """A collection due the day BEFORE the customer's payday should
    trigger a shift recommendation to the payday window."""
    response = await async_client.post(
        "/v1/score",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        json={
            "external_customer_id": "cust_shift",
            "external_collection_id": "col_shift",
            "collection_amount": 1500.00,
            "collection_currency": "ZAR",
            # Salary day 25, due date 24 → days_after = 30 → worst window.
            "collection_due_date": "2027-04-24",
            "collection_method": "CARD",
            "customer_data": {
                "total_payments": 10,
                "successful_payments": 8,
                "card_type": "debit",
                "known_salary_day": 25,
            },
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["recommended_action"] == "shift_date"
    assert data["recommended_collection_date"] is not None
    assert data["score_improvement"] is not None and data["score_improvement"] >= 0.10
    # Recommended date lands in the lowest-risk window [25, 28].
    recommended_day = int(data["recommended_collection_date"].split("-")[2])
    assert 25 <= recommended_day <= 28, (
        f"Expected day in [25, 28], got {data['recommended_collection_date']}"
    )
    # Recommended score is strictly less than the original.
    assert data["recommended_score"] < data["score"]
