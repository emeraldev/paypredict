"""Tests for GET /v1/analytics/* endpoints."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from tests.conftest import TEST_API_KEY, TEST_USER_EMAIL, TEST_USER_PASSWORD


async def _login(client) -> str:
    r = await client.post(
        "/v1/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )
    return r.json()["token"]


async def _create_score_and_outcome(
    client,
    *,
    customer_id: str,
    outcome: str = "SUCCESS",
    failure_reason: str | None = None,
):
    """Create a score then report an outcome linked to it."""
    score = await client.post(
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
    assert score.status_code == 200
    score_id = score.json()["score_id"]

    # Use a recent timestamp so analytics period filters (e.g. 30d) always
    # include this outcome regardless of when the test happens to run.
    attempted_at = (datetime.now(timezone.utc) - timedelta(days=1)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    body: dict = {
        "score_id": score_id,
        "external_collection_id": f"col_{customer_id}",
        "outcome": outcome,
        "attempted_at": attempted_at,
    }
    if failure_reason:
        body["failure_reason"] = failure_reason

    out = await client.post(
        "/v1/outcomes",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        json=body,
    )
    assert out.status_code == 201
    return score.json(), out.json()


# ---- Summary ----

@pytest.mark.asyncio
async def test_summary_empty(async_client, sa_admin_user):
    """Empty dataset → zeroed summary."""
    token = await _login(async_client)
    r = await async_client.get(
        "/v1/analytics/summary?period=30d",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["period"] == "30d"
    assert data["total_scored"] == 0
    assert data["total_outcomes"] == 0
    assert data["collection_rate"] == 0.0


@pytest.mark.asyncio
async def test_summary_with_data(async_client, sa_admin_user):
    """Summary reflects scored collections and outcomes."""
    token = await _login(async_client)

    await _create_score_and_outcome(async_client, customer_id="sum_001", outcome="SUCCESS")
    await _create_score_and_outcome(async_client, customer_id="sum_002", outcome="FAILED", failure_reason="insufficient_funds")

    r = await async_client.get(
        "/v1/analytics/summary?period=30d",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = r.json()
    assert data["total_scored"] == 2
    assert data["total_outcomes"] == 2
    assert data["collection_rate"] == 0.5
    assert data["risk_distribution"]["high"] + data["risk_distribution"]["medium"] + data["risk_distribution"]["low"] == 2
    assert 0.0 <= data["prediction_accuracy"]["overall_accuracy"] <= 1.0
    assert float(data["total_value_scored"]) > 0


@pytest.mark.asyncio
async def test_summary_no_auth(async_client, sa_tenant):
    r = await async_client.get("/v1/analytics/summary")
    assert r.status_code == 401


# ---- Collection Rate ----

@pytest.mark.asyncio
async def test_collection_rate_empty(async_client, sa_admin_user):
    token = await _login(async_client)
    r = await async_client.get(
        "/v1/analytics/collection-rate?period=30d&interval=daily",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["data_points"] == []


@pytest.mark.asyncio
async def test_collection_rate_with_data(async_client, sa_admin_user):
    token = await _login(async_client)
    await _create_score_and_outcome(async_client, customer_id="cr_001", outcome="SUCCESS")
    await _create_score_and_outcome(async_client, customer_id="cr_002", outcome="FAILED")

    r = await async_client.get(
        "/v1/analytics/collection-rate?period=30d&interval=daily",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = r.json()
    assert len(data["data_points"]) >= 1
    point = data["data_points"][0]
    assert "date" in point
    assert "collection_rate" in point
    assert point["scored_count"] >= 1


# ---- Factors ----

@pytest.mark.asyncio
async def test_factors_empty(async_client, sa_admin_user):
    token = await _login(async_client)
    r = await async_client.get(
        "/v1/analytics/factors?period=30d",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["factors"] == []


@pytest.mark.asyncio
async def test_factors_with_data(async_client, sa_admin_user):
    token = await _login(async_client)
    await _create_score_and_outcome(async_client, customer_id="fac_001", outcome="SUCCESS")
    await _create_score_and_outcome(async_client, customer_id="fac_002", outcome="FAILED")

    r = await async_client.get(
        "/v1/analytics/factors?period=30d",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = r.json()
    assert len(data["factors"]) > 0
    factor = data["factors"][0]
    assert "factor" in factor
    assert "avg_contribution" in factor
    assert "correlation_with_failure" in factor


@pytest.mark.asyncio
async def test_factors_tolerates_legacy_jsonb_key(async_client, sa_admin_user, db_session):
    """Score rows from the pre-fix bulk path used 'factor' instead of
    'factor_name' in the JSONB. The factors endpoint must still return 200
    with COALESCE-fallback (and skip rows that have neither key, rather
    than 500ing on a None factor_name)."""
    from sqlalchemy import update
    from app.models.score_result import ScoreResult

    token = await _login(async_client)
    await _create_score_and_outcome(async_client, customer_id="legacy_001", outcome="FAILED")

    # Rewrite the persisted JSONB to simulate a legacy bulk-scored row.
    result = await db_session.execute(
        select(ScoreResult).order_by(ScoreResult.created_at.desc()).limit(1)
    )
    row = result.scalar_one()
    legacy_factors = {
        "evaluated": [
            {"factor": entry["factor_name"], **{k: v for k, v in entry.items() if k != "factor_name"}}
            for entry in row.factors["evaluated"]
        ],
        "skipped": row.factors.get("skipped", []),
    }
    await db_session.execute(
        update(ScoreResult).where(ScoreResult.id == row.id).values(factors=legacy_factors)
    )
    await db_session.flush()

    r = await async_client.get(
        "/v1/analytics/factors?period=30d",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    # Legacy entries are still surfaced via the COALESCE.
    assert len(r.json()["factors"]) > 0


# ---- Accuracy (confusion matrix) ----

@pytest.mark.asyncio
async def test_accuracy_empty(async_client, sa_admin_user):
    token = await _login(async_client)
    r = await async_client.get(
        "/v1/analytics/accuracy?period=30d",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    cm = r.json()["confusion_matrix"]
    total = sum(cm.values())
    assert total == 0


@pytest.mark.asyncio
async def test_accuracy_with_data(async_client, sa_admin_user):
    token = await _login(async_client)
    await _create_score_and_outcome(async_client, customer_id="acc_001", outcome="SUCCESS")
    await _create_score_and_outcome(async_client, customer_id="acc_002", outcome="FAILED")

    r = await async_client.get(
        "/v1/analytics/accuracy?period=30d",
        headers={"Authorization": f"Bearer {token}"},
    )
    cm = r.json()["confusion_matrix"]
    total = sum(cm.values())
    assert total == 2  # 2 outcomes linked to scores


@pytest.mark.asyncio
async def test_invalid_period(async_client, sa_admin_user):
    """Invalid period string → 422."""
    token = await _login(async_client)
    r = await async_client.get(
        "/v1/analytics/summary?period=999d",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422
