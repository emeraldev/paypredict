"""Tests for backtest endpoints."""
import pytest

from tests.conftest import TEST_USER_EMAIL, TEST_USER_PASSWORD


async def _login(client) -> str:
    r = await client.post(
        "/v1/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )
    return r.json()["token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _sample_collections(count: int = 5) -> list[dict]:
    """Generate sample backtest collections."""
    items = []
    for i in range(count):
        items.append({
            "external_customer_id": f"cust_{i:03d}",
            "external_collection_id": f"col_{i:03d}",
            "collection_amount": 1000 + i * 100,
            "collection_currency": "ZAR",
            "collection_date": "2025-11-15",
            "collection_method": "CARD",
            "customer_data": {
                "total_payments": 10,
                "successful_payments": 7 if i % 2 == 0 else 3,
                "card_type": "debit",
            },
            "actual_outcome": "SUCCESS" if i % 3 != 0 else "FAILED",
            "failure_reason": "insufficient_funds" if i % 3 == 0 else None,
        })
    return items


@pytest.mark.asyncio
async def test_backtest_success(async_client, sa_admin_user):
    """Run a backtest and get results."""
    token = await _login(async_client)
    r = await async_client.post(
        "/v1/backtest",
        headers=_auth(token),
        json={
            "name": "Test Backtest",
            "collections": _sample_collections(10),
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "COMPLETED"
    assert data["total_collections"] == 10
    assert data["summary"] is not None
    assert data["confusion_matrix"] is not None
    assert data["risk_distribution"] is not None
    assert 0 <= data["summary"]["overall_accuracy"] <= 1
    assert data["name"] == "Test Backtest"


@pytest.mark.asyncio
async def test_backtest_get_by_id(async_client, sa_admin_user):
    """Get a backtest by ID."""
    token = await _login(async_client)
    create = await async_client.post(
        "/v1/backtest",
        headers=_auth(token),
        json={"collections": _sample_collections(5)},
    )
    backtest_id = create.json()["backtest_id"]

    r = await async_client.get(
        f"/v1/backtest/{backtest_id}",
        headers=_auth(token),
    )
    assert r.status_code == 200
    assert r.json()["backtest_id"] == backtest_id
    assert r.json()["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_backtest_list(async_client, sa_admin_user):
    """List backtests for the tenant."""
    token = await _login(async_client)
    await async_client.post(
        "/v1/backtest",
        headers=_auth(token),
        json={"name": "Run 1", "collections": _sample_collections(3)},
    )
    await async_client.post(
        "/v1/backtest",
        headers=_auth(token),
        json={"name": "Run 2", "collections": _sample_collections(3)},
    )

    r = await async_client.get("/v1/backtests", headers=_auth(token))
    assert r.status_code == 200
    assert len(r.json()["items"]) >= 2


@pytest.mark.asyncio
async def test_backtest_not_found(async_client, sa_admin_user):
    token = await _login(async_client)
    r = await async_client.get(
        "/v1/backtest/00000000-0000-0000-0000-000000000000",
        headers=_auth(token),
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_backtest_csv_upload(async_client, sa_admin_user):
    """Upload a CSV file for backtesting."""
    token = await _login(async_client)
    csv_content = (
        "external_customer_id,external_collection_id,collection_amount,"
        "collection_currency,collection_date,collection_method,"
        "instalment_number,total_instalments,total_payments,"
        "successful_payments,card_type,card_expiry,actual_outcome,failure_reason\n"
        "cust_001,inst_001,833.33,ZAR,2025-11-15,CARD,3,6,8,5,debit,2026-09-01,FAILED,insufficient_funds\n"
        "cust_002,inst_002,500.00,ZAR,2025-11-15,DEBIT_ORDER,1,3,0,0,,,SUCCESS,\n"
    )

    r = await async_client.post(
        "/v1/backtest/upload",
        headers=_auth(token),
        files={"file": ("test.csv", csv_content.encode(), "text/csv")},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "COMPLETED"
    assert data["total_collections"] == 2


@pytest.mark.asyncio
async def test_backtest_csv_validation_errors(async_client, sa_admin_user):
    """CSV with invalid rows returns validation errors."""
    token = await _login(async_client)
    csv_content = (
        "external_customer_id,external_collection_id,collection_amount,"
        "collection_currency,collection_date,collection_method,"
        "actual_outcome,failure_reason\n"
        "cust_001,,bad_amount,INVALID,not-a-date,CARD,FAILED,\n"
    )

    r = await async_client.post(
        "/v1/backtest/upload",
        headers=_auth(token),
        files={"file": ("test.csv", csv_content.encode(), "text/csv")},
    )
    assert r.status_code == 201
    data = r.json()
    assert "errors" in data
    assert len(data["errors"]) > 0


@pytest.mark.asyncio
async def test_backtest_template_download(async_client, sa_admin_user):
    """Download the CSV template."""
    token = await _login(async_client)
    r = await async_client.get("/v1/backtest/template", headers=_auth(token))
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    assert "external_customer_id" in r.text


@pytest.mark.asyncio
async def test_backtest_no_auth(async_client, sa_tenant):
    r = await async_client.post("/v1/backtest", json={"collections": []})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_backtest_empty_collections(async_client, sa_admin_user):
    """Empty collections list → 422."""
    token = await _login(async_client)
    r = await async_client.post(
        "/v1/backtest",
        headers=_auth(token),
        json={"collections": []},
    )
    assert r.status_code == 422
