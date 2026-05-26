"""Role enforcement matrix.

For every mutating dashboard endpoint, verify that:
  - ADMIN  → succeeds (or fails for a non-auth reason like 404/422)
  - MANAGER → 403 on Admin-only endpoints, succeeds on Manager-or-Admin
  - VIEWER  → 403 on every mutating endpoint

Read endpoints are not exercised here — they remain open to every
authenticated role and are covered by their own endpoint test files.
"""
import uuid

import pytest

from tests.conftest import (
    TEST_API_KEY,
    TEST_MANAGER_EMAIL,
    TEST_USER_EMAIL,
    TEST_USER_PASSWORD,
    TEST_VIEWER_EMAIL,
)


async def _token(client, email: str) -> str:
    r = await client.post(
        "/v1/auth/login",
        json={"email": email, "password": TEST_USER_PASSWORD},
    )
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---- Helpers to create a real backtest record for the GET tests ----


async def _seed_score(client) -> dict:
    r = await client.post(
        "/v1/score",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        json={
            "customer_id": "role_cust",
            "collection_id": "role_col",
            "collection_amount": 1000,
            "collection_currency": "ZAR",
            "collection_due_date": "2026-04-15",
            "collection_method": "CARD",
            "customer_data": {"total_payments": 5, "successful_payments": 4, "card_type": "debit"},
        },
    )
    assert r.status_code == 200
    return r.json()


# ---- API keys (Admin-only mutations) ----


@pytest.mark.asyncio
async def test_create_api_key_requires_admin(
    async_client, sa_admin_user, sa_manager_user, sa_viewer_user
):
    body = {"label": "test-key"}
    admin = await _token(async_client, TEST_USER_EMAIL)
    manager = await _token(async_client, TEST_MANAGER_EMAIL)
    viewer = await _token(async_client, TEST_VIEWER_EMAIL)

    assert (await async_client.post("/v1/config/api-keys", headers=_h(admin), json=body)).status_code == 201
    assert (await async_client.post("/v1/config/api-keys", headers=_h(manager), json=body)).status_code == 403
    assert (await async_client.post("/v1/config/api-keys", headers=_h(viewer), json=body)).status_code == 403


@pytest.mark.asyncio
async def test_revoke_api_key_requires_admin(
    async_client, sa_admin_user, sa_manager_user, sa_viewer_user
):
    # Create the key as admin first
    admin = await _token(async_client, TEST_USER_EMAIL)
    create = await async_client.post(
        "/v1/config/api-keys", headers=_h(admin), json={"label": "to-revoke"},
    )
    key_id = create.json()["id"]

    manager = await _token(async_client, TEST_MANAGER_EMAIL)
    viewer = await _token(async_client, TEST_VIEWER_EMAIL)

    assert (await async_client.delete(f"/v1/config/api-keys/{key_id}", headers=_h(manager))).status_code == 403
    assert (await async_client.delete(f"/v1/config/api-keys/{key_id}", headers=_h(viewer))).status_code == 403
    assert (await async_client.delete(f"/v1/config/api-keys/{key_id}", headers=_h(admin))).status_code == 204


# ---- Alert settings (Admin-only mutations) ----


@pytest.mark.asyncio
async def test_update_alert_settings_requires_admin(
    async_client, sa_admin_user, sa_manager_user, sa_viewer_user
):
    body = {"high_risk_threshold": 0.25}
    admin = await _token(async_client, TEST_USER_EMAIL)
    manager = await _token(async_client, TEST_MANAGER_EMAIL)
    viewer = await _token(async_client, TEST_VIEWER_EMAIL)

    assert (await async_client.put("/v1/config/alerts", headers=_h(admin), json=body)).status_code == 200
    assert (await async_client.put("/v1/config/alerts", headers=_h(manager), json=body)).status_code == 403
    assert (await async_client.put("/v1/config/alerts", headers=_h(viewer), json=body)).status_code == 403


@pytest.mark.asyncio
async def test_regenerate_webhook_secret_requires_admin(
    async_client, sa_admin_user, sa_manager_user, sa_viewer_user
):
    admin = await _token(async_client, TEST_USER_EMAIL)
    manager = await _token(async_client, TEST_MANAGER_EMAIL)
    viewer = await _token(async_client, TEST_VIEWER_EMAIL)

    assert (await async_client.post("/v1/config/alerts/regenerate-secret", headers=_h(manager))).status_code == 403
    assert (await async_client.post("/v1/config/alerts/regenerate-secret", headers=_h(viewer))).status_code == 403
    assert (await async_client.post("/v1/config/alerts/regenerate-secret", headers=_h(admin))).status_code == 200


# ---- Weights PUT (Admin-only on JWT path; API-key path stays open) ----


@pytest.mark.asyncio
async def test_update_weights_requires_admin_on_jwt(
    async_client, sa_admin_user, sa_manager_user, sa_viewer_user
):
    body = {"weights": {"historical_failure_rate": 0.25}}
    admin = await _token(async_client, TEST_USER_EMAIL)
    manager = await _token(async_client, TEST_MANAGER_EMAIL)
    viewer = await _token(async_client, TEST_VIEWER_EMAIL)

    assert (await async_client.put("/v1/config/weights", headers=_h(admin), json=body)).status_code == 200
    assert (await async_client.put("/v1/config/weights", headers=_h(manager), json=body)).status_code == 403
    assert (await async_client.put("/v1/config/weights", headers=_h(viewer), json=body)).status_code == 403


@pytest.mark.asyncio
async def test_update_weights_via_api_key_still_works(async_client, sa_tenant):
    """Lender API-key callers bypass the JWT-role check by design — the
    key represents the tenant itself, not a specific dashboard user."""
    r = await async_client.put(
        "/v1/config/weights",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        json={"weights": {"historical_failure_rate": 0.25}},
    )
    assert r.status_code == 200


# ---- Backtest (Admin OR Manager) ----


@pytest.mark.asyncio
async def test_run_backtest_requires_admin_or_manager(
    async_client, sa_admin_user, sa_manager_user, sa_viewer_user
):
    body = {"name": "test-bt", "collections": [{
        "customer_id": "bt_c1",
        "collection_id": "bt_col1",
        "collection_amount": 500,
        "collection_currency": "ZAR",
        "collection_date": "2026-04-15",  # NB: backtest schema uses collection_date
        "collection_method": "CARD",
        "actual_outcome": "SUCCESS",
        "customer_data": {"total_payments": 5, "successful_payments": 4, "card_type": "debit"},
    }]}
    admin = await _token(async_client, TEST_USER_EMAIL)
    manager = await _token(async_client, TEST_MANAGER_EMAIL)
    viewer = await _token(async_client, TEST_VIEWER_EMAIL)

    assert (await async_client.post("/v1/backtest", headers=_h(admin), json=body)).status_code == 201
    assert (await async_client.post("/v1/backtest", headers=_h(manager), json=body)).status_code == 201
    assert (await async_client.post("/v1/backtest", headers=_h(viewer), json=body)).status_code == 403


@pytest.mark.asyncio
async def test_backtest_upload_requires_admin_or_manager(
    async_client, sa_admin_user, sa_manager_user, sa_viewer_user
):
    """The CSV upload endpoint used to skip the role check — confirm it
    now uses the same require_admin_or_manager dep."""
    viewer = await _token(async_client, TEST_VIEWER_EMAIL)
    # We send a deliberately invalid file (no .csv extension) — the route
    # should reject on RBAC (403) before it ever inspects the filename.
    files = {"file": ("not_a_csv.txt", b"irrelevant", "text/plain")}
    r = await async_client.post("/v1/backtest/upload", headers=_h(viewer), files=files)
    assert r.status_code == 403


# ---- Team management (Admin-only — already enforced; sanity ensure unchanged) ----


@pytest.mark.asyncio
async def test_invite_member_requires_admin(
    async_client, sa_admin_user, sa_manager_user, sa_viewer_user
):
    body = {
        "email": "new@paypredict.test",
        "name": "Newbie",
        "password": "test-password-1234",
        "role": "VIEWER",
    }
    manager = await _token(async_client, TEST_MANAGER_EMAIL)
    viewer = await _token(async_client, TEST_VIEWER_EMAIL)

    assert (await async_client.post("/v1/config/team", headers=_h(manager), json=body)).status_code == 403
    assert (await async_client.post("/v1/config/team", headers=_h(viewer), json=body)).status_code == 403


# ---- Read endpoints remain open to every role ----


@pytest.mark.asyncio
async def test_read_endpoints_open_to_every_role(
    async_client, sa_admin_user, sa_manager_user, sa_viewer_user
):
    """Spot-check that a Viewer can still read the dashboard."""
    viewer = await _token(async_client, TEST_VIEWER_EMAIL)
    for path in (
        "/v1/scores",
        "/v1/outcomes",
        "/v1/analytics/summary?period=30d",
        "/v1/config/weights",
        "/v1/config/api-keys",
        "/v1/config/alerts",
        "/v1/backtests",
        "/v1/notifications",
    ):
        r = await async_client.get(path, headers=_h(viewer))
        assert r.status_code == 200, f"GET {path} → {r.status_code}: {r.text}"
