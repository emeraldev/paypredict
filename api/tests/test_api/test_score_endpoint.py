"""Tests for POST /v1/score endpoint."""

import pytest

from tests.conftest import TEST_API_KEY, TEST_USER_EMAIL, TEST_USER_PASSWORD


@pytest.mark.asyncio
async def test_score_success(async_client, sa_tenant):
    response = await async_client.post(
        "/v1/score",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        json={
            "customer_id": "cust_001",
            "collection_id": "col_001",
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
            "customer_id": "cust_001",
            "collection_id": "col_001",
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
            "customer_id": "cust_001",
            "collection_id": "col_001",
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
            "customer_id": "cust_001",
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
            "customer_id": "cust_002",
            "collection_id": "col_002",
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
            "customer_id": "cust_no_shift",
            "collection_id": "col_no_shift",
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
            "customer_id": "cust_shift",
            "collection_id": "col_shift",
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


@pytest.mark.asyncio
async def test_score_via_dashboard_jwt(async_client, sa_admin_user):
    """The single-collection form on /dashboard/score posts to /v1/score with
    a JWT (no API key). Same scoring behaviour, no rate-limit headers."""
    r = await async_client.post(
        "/v1/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )
    token = r.json()["token"]

    response = await async_client.post(
        "/v1/score",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "customer_id": "cust_jwt",
            "collection_id": "col_jwt",
            "collection_amount": 1500.00,
            "collection_currency": "ZAR",
            "collection_due_date": "2026-08-15",
            "collection_method": "CARD",
            "customer_data": {"total_payments": 10, "successful_payments": 7},
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "score_id" in data
    assert 0.0 <= data["score"] <= 1.0
    # JWT callers must not be rate-limited (no headers consumed).
    assert "x-ratelimit-limit" not in {k.lower() for k in response.headers}


# ---- PII enforcement at the API boundary --------------------------------


def _valid_body(**overrides) -> dict:
    """Minimal-but-valid POST /v1/score body. Tests override individual
    fields to exercise rejection paths."""
    body = {
        "customer_id": "cust_valid_001",
        "collection_id": "col_valid_001",
        "collection_amount": 1500.00,
        "collection_currency": "ZAR",
        "collection_due_date": "2026-04-15",
        "collection_method": "CARD",
    }
    body.update(overrides)
    return body


@pytest.mark.asyncio
async def test_customer_data_rejects_extra_fields(async_client, sa_tenant):
    """A lender that sends a `phone` field inside customer_data — thinking
    it'll help the model — must get a 422 pointing at the offending key,
    not a 200 with the field silently dropped."""
    response = await async_client.post(
        "/v1/score",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        json=_valid_body(customer_data={"total_payments": 5, "phone": "+27..."}),
    )
    assert response.status_code == 422
    body = response.json()
    # Pydantic reports the extra field name; assert it's flagged.
    detail_str = str(body["detail"]).lower()
    assert "phone" in detail_str
    assert "extra" in detail_str or "forbidden" in detail_str


@pytest.mark.asyncio
async def test_score_request_rejects_extra_fields(async_client, sa_tenant):
    """Same rule at the top-level payload — `borrower_name` alongside
    customer_data is rejected."""
    response = await async_client.post(
        "/v1/score",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        json=_valid_body(borrower_name="Jane Doe"),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_id", [
    "john@example.com",              # email
    "John Doe",                      # whitespace
    "+27 82 555 1234",               # formatted phone
    "(082) 555-1234",                # parens
    "cust,001",                      # comma
    "a" * 129,                       # over length cap
    "",                              # empty
])
async def test_customer_id_rejects_pii_shapes(async_client, sa_tenant, bad_id):
    response = await async_client.post(
        "/v1/score",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        json=_valid_body(customer_id=bad_id),
    )
    assert response.status_code == 422, f"expected 422 for {bad_id!r}"
    # Error mentions customer_id specifically.
    assert "customer_id" in str(response.json()["detail"])


@pytest.mark.asyncio
@pytest.mark.parametrize("good_id", [
    "550e8400-e29b-41d4-a716-446655440000",  # UUID
    "cust_sa_001",                            # underscored prefix
    "EMP_ROSE_001",                           # SCREAMING prefix
    "500000123",                              # purely numeric internal id
    "col:2026:08:13",                         # colon-separated
    "cust.sa.001",                            # dot-separated
    "abc-123",                                # hyphen
])
async def test_customer_id_accepts_opaque_shapes(async_client, sa_tenant, good_id):
    response = await async_client.post(
        "/v1/score",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        json=_valid_body(customer_id=good_id),
    )
    assert response.status_code == 200, f"expected 200 for {good_id!r}"


@pytest.mark.asyncio
async def test_collection_id_shares_rules(async_client, sa_tenant):
    """collection_id follows the same shape as customer_id."""
    response = await async_client.post(
        "/v1/score",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        json=_valid_body(collection_id="john@example.com"),
    )
    assert response.status_code == 422
    assert "collection_id" in str(response.json()["detail"])


@pytest.mark.asyncio
async def test_customer_data_string_field_max_length(async_client, sa_tenant):
    """Free-form string fields on customer_data carry length limits to
    prevent names / addresses / paragraphs of notes slipping in."""
    response = await async_client.post(
        "/v1/score",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        json=_valid_body(customer_data={
            "total_payments": 5,
            # 100-char blob far exceeds the 32-char cap on card_type
            "card_type": "credit — this is a really long description with the customer's " * 3,
        }),
    )
    assert response.status_code == 422
    assert "card_type" in str(response.json()["detail"])
