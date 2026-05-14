"""Tests for the lender-facing rate limiter.

Strategy: each test uses a fresh tenant (sa_tenant / zm_tenant fixtures
generate new UUIDs), so their Redis bucket keys never collide. To test
the over-limit path without making 200 real requests, we monkeypatch
`PLAN_RATE_LIMITS` to a tiny number for the duration of the test.
"""
import pytest

from app import config
from app.services.rate_limit_service import _bucket_key
from tests.conftest import TEST_API_KEY


_SCORE_PAYLOAD = {
    "external_customer_id": "rl_cust_001",
    "external_collection_id": "rl_inst_001",
    "collection_amount": 1500.00,
    "collection_currency": "ZAR",
    "collection_due_date": "2026-04-15",
    "collection_method": "CARD",
    "customer_data": {
        "total_payments": 10,
        "successful_payments": 7,
        "card_type": "debit",
    },
}


def _auth() -> dict[str, str]:
    return {"Authorization": f"Bearer {TEST_API_KEY}"}


@pytest.fixture
def reset_rate_limit_redis(sa_tenant):
    """Clear this tenant's bucket before and after each test so leftover
    counters from earlier runs don't poison the limit math."""
    from app.dependencies import _rate_limit_redis
    import time

    now = int(time.time())
    # Delete the current and previous window keys for this tenant.
    for offset in (-1, 0, 1):
        _rate_limit_redis.delete(_bucket_key(sa_tenant.id, now + offset * config.RATE_LIMIT_WINDOW_SECONDS))
    yield
    for offset in (-1, 0, 1):
        _rate_limit_redis.delete(_bucket_key(sa_tenant.id, now + offset * config.RATE_LIMIT_WINDOW_SECONDS))


@pytest.mark.asyncio
async def test_under_limit_succeeds_with_headers(
    async_client, sa_tenant, reset_rate_limit_redis
):
    """A single request under the limit returns 200 + X-RateLimit-* headers."""
    r = await async_client.post("/v1/score", headers=_auth(), json=_SCORE_PAYLOAD)
    assert r.status_code == 200
    # sa_tenant is STARTER → 200 req/min.
    assert r.headers["X-RateLimit-Limit"] == "200"
    assert r.headers["X-RateLimit-Remaining"] == "199"
    assert int(r.headers["X-RateLimit-Reset"]) > 0


@pytest.mark.asyncio
async def test_over_limit_returns_429_with_retry_after(
    async_client, sa_tenant, reset_rate_limit_redis, monkeypatch
):
    """Exceeding the tenant's tier limit returns 429 + Retry-After."""
    # Shrink the STARTER limit so 2 requests exhaust it.
    monkeypatch.setitem(config.PLAN_RATE_LIMITS, "STARTER", 2)

    for _ in range(2):
        ok = await async_client.post("/v1/score", headers=_auth(), json=_SCORE_PAYLOAD)
        assert ok.status_code == 200, ok.text

    blocked = await async_client.post("/v1/score", headers=_auth(), json=_SCORE_PAYLOAD)
    assert blocked.status_code == 429, blocked.text
    assert blocked.headers["X-RateLimit-Limit"] == "2"
    assert blocked.headers["X-RateLimit-Remaining"] == "0"
    assert int(blocked.headers["Retry-After"]) >= 1
    body = blocked.json()
    assert "Rate limit exceeded" in body["detail"]
    assert "STARTER" in body["detail"]


@pytest.mark.asyncio
async def test_over_limit_does_not_burn_extra_tickets(
    async_client, sa_tenant, reset_rate_limit_redis, monkeypatch
):
    """Once over the limit, subsequent 429s shouldn't keep incrementing the
    counter — otherwise an attacker spamming requests stretches the
    cooldown indefinitely."""
    monkeypatch.setitem(config.PLAN_RATE_LIMITS, "STARTER", 1)

    # Burn the single ticket.
    await async_client.post("/v1/score", headers=_auth(), json=_SCORE_PAYLOAD)

    # Two consecutive 429s should both report remaining=0 with no change.
    r1 = await async_client.post("/v1/score", headers=_auth(), json=_SCORE_PAYLOAD)
    r2 = await async_client.post("/v1/score", headers=_auth(), json=_SCORE_PAYLOAD)
    assert r1.status_code == 429
    assert r2.status_code == 429
    assert r1.headers["X-RateLimit-Remaining"] == "0"
    assert r2.headers["X-RateLimit-Remaining"] == "0"


@pytest.mark.asyncio
async def test_bulk_endpoint_counts_as_one_ticket(
    async_client, sa_tenant, reset_rate_limit_redis, monkeypatch
):
    """POST /v1/score/bulk with 50 collections should consume exactly one
    ticket, not fifty. Matches the api-reference.md contract."""
    monkeypatch.setitem(config.PLAN_RATE_LIMITS, "STARTER", 3)

    bulk_items = [
        {**_SCORE_PAYLOAD, "external_customer_id": f"bk_{i}", "external_collection_id": f"bk_inst_{i}"}
        for i in range(10)
    ]
    r = await async_client.post(
        "/v1/score/bulk", headers=_auth(), json={"collections": bulk_items}
    )
    assert r.status_code == 200, r.text
    assert r.headers["X-RateLimit-Remaining"] == "2", (
        "bulk-of-10 should burn 1 ticket, leaving 2 of 3 remaining"
    )


@pytest.mark.asyncio
async def test_dashboard_endpoints_are_not_rate_limited(
    async_client, sa_admin_user, monkeypatch
):
    """Dashboard JWT routes don't go through enforce_rate_limit. Even with
    the limit set to zero, dashboard calls succeed."""
    monkeypatch.setitem(config.PLAN_RATE_LIMITS, "STARTER", 0)

    # Login (dashboard endpoint, no rate limit).
    from tests.conftest import TEST_USER_EMAIL, TEST_USER_PASSWORD
    login = await async_client.post(
        "/v1/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )
    token = login.json()["token"]

    # Dashboard scores list — should not 429.
    r = await async_client.get(
        "/v1/scores", headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert "X-RateLimit-Limit" not in r.headers, (
        "Dashboard responses should not carry lender rate-limit headers"
    )


def test_get_limit_for_plan_falls_back_to_pilot_for_unknown():
    """Unknown plan strings collapse to the most restrictive tier so a typo
    can't grant unlimited access."""
    from app.services.rate_limit_service import get_limit_for_plan

    assert get_limit_for_plan("PILOT") == config.PLAN_RATE_LIMITS["PILOT"]
    assert get_limit_for_plan("STARTER") == config.PLAN_RATE_LIMITS["STARTER"]
    assert get_limit_for_plan("ENTERPRISE_DELUXE_PRO") == config.PLAN_RATE_LIMITS["PILOT"]


@pytest.mark.asyncio
async def test_dual_auth_api_key_path_is_rate_limited(
    async_client, sa_tenant, reset_rate_limit_redis, monkeypatch
):
    """`/v1/analytics/*` and `/v1/config/weights` accept either an API key
    or a dashboard JWT. The API-key path must consume a ticket and
    surface X-RateLimit-* headers; exhausting the bucket must 429."""
    monkeypatch.setitem(config.PLAN_RATE_LIMITS, "STARTER", 2)

    r1 = await async_client.get("/v1/analytics/summary?period=30d", headers=_auth())
    r2 = await async_client.get("/v1/analytics/summary?period=30d", headers=_auth())
    r3 = await async_client.get("/v1/analytics/summary?period=30d", headers=_auth())

    assert r1.status_code == 200
    assert r1.headers["X-RateLimit-Limit"] == "2"
    assert r1.headers["X-RateLimit-Remaining"] == "1"
    assert r2.status_code == 200
    assert r2.headers["X-RateLimit-Remaining"] == "0"
    assert r3.status_code == 429
    assert r3.headers["Retry-After"]


@pytest.mark.asyncio
async def test_dual_auth_jwt_path_is_not_rate_limited(
    async_client, sa_admin_user, monkeypatch
):
    """A dashboard user hitting the same shared endpoint via JWT must
    bypass the rate limiter entirely: no X-RateLimit-* headers and no
    429 even after many calls. We set the API-key limit to 0 so any
    accidental rate-limit application would immediately fail."""
    monkeypatch.setitem(config.PLAN_RATE_LIMITS, "STARTER", 0)

    from tests.conftest import TEST_USER_EMAIL, TEST_USER_PASSWORD
    login = await async_client.post(
        "/v1/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )
    token = login.json()["token"]
    jwt_headers = {"Authorization": f"Bearer {token}"}

    # Hit the endpoint a few times to make sure it doesn't 429.
    for _ in range(3):
        r = await async_client.get("/v1/analytics/summary?period=30d", headers=jwt_headers)
        assert r.status_code == 200, r.text
        assert "X-RateLimit-Limit" not in r.headers, (
            "Dashboard JWT calls must not surface rate-limit headers"
        )

    # The weights endpoint behaves the same way.
    r = await async_client.get("/v1/config/weights", headers=jwt_headers)
    assert r.status_code == 200
    assert "X-RateLimit-Limit" not in r.headers


@pytest.mark.asyncio
async def test_dual_auth_jwt_does_not_consume_api_key_bucket(
    async_client, sa_admin_user, sa_tenant, reset_rate_limit_redis, monkeypatch
):
    """A dashboard JWT call to a shared endpoint must not consume the
    same tenant's API-key bucket. Otherwise the team using the dashboard
    could starve their own lender integration of rate-limit budget."""
    monkeypatch.setitem(config.PLAN_RATE_LIMITS, "STARTER", 1)

    from tests.conftest import TEST_USER_EMAIL, TEST_USER_PASSWORD
    login = await async_client.post(
        "/v1/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )
    token = login.json()["token"]
    jwt_headers = {"Authorization": f"Bearer {token}"}

    # 5 dashboard calls — should NOT touch the API-key bucket.
    for _ in range(5):
        r = await async_client.get("/v1/analytics/summary?period=30d", headers=jwt_headers)
        assert r.status_code == 200

    # The single API-key ticket is still available.
    r = await async_client.get("/v1/analytics/summary?period=30d", headers=_auth())
    assert r.status_code == 200, r.text
    assert r.headers["X-RateLimit-Remaining"] == "0"


def test_check_and_increment_isolates_tenants():
    """Two tenants exhausting their own buckets must not affect each other."""
    import uuid
    from app.dependencies import _rate_limit_redis
    from app.services.rate_limit_service import check_and_increment

    t1, t2 = uuid.uuid4(), uuid.uuid4()
    # Use a fixed `now` so both tenants share the same window edge.
    now = 1_700_000_000
    # Saturate t1 against STARTER (200).
    for _ in range(config.PLAN_RATE_LIMITS["STARTER"]):
        check_and_increment(t1, "STARTER", _rate_limit_redis, now=now)
    blocked = check_and_increment(t1, "STARTER", _rate_limit_redis, now=now)
    assert blocked.allowed is False

    # t2 in the same window should still be fully available.
    ok = check_and_increment(t2, "STARTER", _rate_limit_redis, now=now)
    assert ok.allowed is True
    assert ok.remaining == config.PLAN_RATE_LIMITS["STARTER"] - 1
