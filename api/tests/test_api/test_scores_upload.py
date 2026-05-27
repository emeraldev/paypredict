"""Tests for POST /v1/scores/upload + GET /v1/scores/upload/template."""
import pytest

from tests.conftest import TEST_USER_EMAIL, TEST_USER_PASSWORD


async def _login(client) -> str:
    r = await client.post(
        "/v1/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )
    return r.json()["token"]


VALID_HEADER = (
    "customer_id,collection_id,collection_amount,collection_currency,"
    "collection_due_date,collection_method,total_payments,successful_payments\n"
)


def _csv(rows: list[str]) -> bytes:
    return (VALID_HEADER + "\n".join(rows) + "\n").encode("utf-8")


@pytest.mark.asyncio
async def test_upload_happy_path_scores_and_persists(async_client, sa_admin_user):
    """A valid CSV is parsed, every row is scored, rows show up on /v1/scores."""
    token = await _login(async_client)
    body = _csv([
        "cust_001,inst_001,1500.00,ZAR,2026-06-15,CARD,10,7",
        "cust_002,inst_002,800.00,ZAR,2026-06-20,DEBIT_ORDER,5,5",
    ])

    r = await async_client.post(
        "/v1/scores/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("upcoming.csv", body, "text/csv")},
    )
    assert r.status_code == 201
    data = r.json()
    assert "errors" not in data
    assert data["total_items"] == 2
    assert len(data["results"]) == 2
    assert all("score_id" in row for row in data["results"])

    # Rows must now appear in the dashboard scores list
    r = await async_client.get(
        "/v1/scores",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    listed = r.json()
    assert listed["pagination"]["total_items"] == 2
    customer_ids = {item["customer_id"] for item in listed["items"]}
    assert customer_ids == {"cust_001", "cust_002"}


@pytest.mark.asyncio
async def test_upload_validation_errors_returned_per_row(async_client, sa_admin_user):
    """Bad rows produce row-level errors with row numbers."""
    token = await _login(async_client)
    body = _csv([
        "cust_a,inst_a,1000,ZAR,2026-06-15,CARD,10,7",     # ok
        "cust_b,inst_b,-50,ZAR,2026-06-15,CARD,1,1",        # bad amount
        "cust_c,inst_c,1000,GBP,2026-06-15,CARD,1,1",       # bad currency
        "cust_d,inst_d,1000,ZAR,not-a-date,CARD,1,1",       # bad date
        "cust_e,inst_e,1000,ZAR,2026-06-15,CARRIER,1,1",    # bad method
    ])
    r = await async_client.post(
        "/v1/scores/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("upcoming.csv", body, "text/csv")},
    )
    assert r.status_code == 201
    data = r.json()
    assert "errors" in data
    fields = {(e["row"], e["field"]) for e in data["errors"]}
    assert (3, "collection_amount") in fields
    assert (4, "collection_currency") in fields
    assert (5, "collection_due_date") in fields
    assert (6, "collection_method") in fields

    # Nothing should have been persisted when there are errors
    r = await async_client.get(
        "/v1/scores",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.json()["pagination"]["total_items"] == 0


@pytest.mark.asyncio
async def test_upload_missing_required_column(async_client, sa_admin_user):
    token = await _login(async_client)
    body = (
        "customer_id,collection_amount,collection_currency,"
        "collection_due_date,collection_method\n"
        "cust_a,1000,ZAR,2026-06-15,CARD\n"
    ).encode("utf-8")
    r = await async_client.post(
        "/v1/scores/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("bad.csv", body, "text/csv")},
    )
    assert r.status_code == 201
    data = r.json()
    assert "errors" in data
    assert any("collection_id" in e["message"] for e in data["errors"])


@pytest.mark.asyncio
async def test_upload_rejects_non_csv_filename(async_client, sa_admin_user):
    token = await _login(async_client)
    r = await async_client.post(
        "/v1/scores/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("upcoming.xlsx", b"anything", "text/csv")},
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_upload_requires_auth(async_client, sa_admin_user):
    body = _csv(["cust_a,inst_a,1000,ZAR,2026-06-15,CARD,1,1"])
    r = await async_client.post(
        "/v1/scores/upload",
        files={"file": ("upcoming.csv", body, "text/csv")},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_template_download_has_expected_headers(async_client, sa_admin_user):
    token = await _login(async_client)
    r = await async_client.get(
        "/v1/scores/upload/template",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    first_line = r.text.splitlines()[0]
    required = [
        "customer_id",
        "collection_id",
        "collection_amount",
        "collection_currency",
        "collection_due_date",
        "collection_method",
    ]
    for col in required:
        assert col in first_line, f"template missing column: {col}"


@pytest.mark.asyncio
async def test_template_is_header_only(async_client, sa_admin_user):
    """Template ships no example rows — uploading it as-is should return a
    friendly error, not persist anything. Reference values live in the
    dashboard's Example Data card instead."""
    token = await _login(async_client)
    tpl = await async_client.get(
        "/v1/scores/upload/template",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert tpl.status_code == 200
    # Single line: just the header, no data rows.
    assert tpl.text.count("\n") == 1, "template should be header-only"

    r = await async_client.post(
        "/v1/scores/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("template.csv", tpl.content, "text/csv")},
    )
    assert r.status_code == 400
    assert "no data rows" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_accepts_excel_friendly_formats(async_client, sa_admin_user):
    """Lenders export from Excel — date is DD/MM/YYYY, method is 'Debit Order'.
    The parser must normalise these instead of rejecting them.
    """
    token = await _login(async_client)
    body = (
        "customer_id,collection_id,collection_amount,collection_currency,"
        "collection_due_date,collection_method\n"
        "cust_ex_a,inst_ex_a,1500,zar,15/07/2026,Card\n"
        "cust_ex_b,inst_ex_b,800,ZAR,15-07-2026,debit order\n"
        "cust_ex_c,inst_ex_c,250,ZMW,2026/07/20,Mobile Money\n"
    ).encode("utf-8")

    r = await async_client.post(
        "/v1/scores/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("excel.csv", body, "text/csv")},
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert "errors" not in data, data.get("errors")
    assert data["total_items"] == 3
    # Each row's metadata should be echoed in the response (used by dashboard
    # for the inline results table + CSV download).
    rows_by_customer = {row["customer_id"]: row for row in data["results"]}
    assert rows_by_customer["cust_ex_a"]["collection_method"] == "CARD"
    assert rows_by_customer["cust_ex_a"]["collection_currency"] == "ZAR"
    assert rows_by_customer["cust_ex_a"]["collection_due_date"] == "2026-07-15"
    assert rows_by_customer["cust_ex_b"]["collection_method"] == "DEBIT_ORDER"
    assert rows_by_customer["cust_ex_b"]["collection_due_date"] == "2026-07-15"
    assert rows_by_customer["cust_ex_c"]["collection_method"] == "MOBILE_MONEY"
    assert rows_by_customer["cust_ex_c"]["collection_due_date"] == "2026-07-20"


@pytest.mark.asyncio
async def test_upload_full_customer_data_exercises_all_factors(
    async_client, sa_admin_user
):
    """A row populating every optional CARD_DEBIT field must parse + score
    without errors. Regression for missing field-extraction in the parser."""
    token = await _login(async_client)
    header = (
        "customer_id,collection_id,collection_amount,collection_currency,"
        "collection_due_date,collection_method,"
        "total_payments,successful_payments,last_successful_payment_date,"
        "average_collection_amount,instalment_number,total_instalments,"
        "card_type,card_expiry,last_decline_code,debit_order_returns,known_salary_day"
    )
    row = (
        "cust_full,inst_full,833.33,ZAR,2026-07-25,CARD,"
        "8,7,2026-06-25,800.00,3,6,"
        "debit,2028-09-01,insufficient_funds,RD|account_closed,25"
    )
    body = (header + "\n" + row + "\n").encode("utf-8")

    r = await async_client.post(
        "/v1/scores/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("full.csv", body, "text/csv")},
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert "errors" not in data
    assert data["total_items"] == 1
    assert 0.0 <= data["results"][0]["score"] <= 1.0


