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
