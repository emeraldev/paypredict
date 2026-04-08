"""Tests for POST /v1/outcomes endpoint."""

import pytest

from tests.conftest import TEST_API_KEY


@pytest.mark.asyncio
async def test_outcome_success(async_client, sa_tenant):
    response = await async_client.post(
        "/v1/outcomes",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        json={
            "external_collection_id": "col_001",
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
            "external_collection_id": "col_002",
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
            "external_collection_id": "col_001",
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
            "external_collection_id": "col_001",
            "outcome": "INVALID_STATUS",
            "attempted_at": "2026-04-15T08:00:00Z",
        },
    )
    assert response.status_code == 422
