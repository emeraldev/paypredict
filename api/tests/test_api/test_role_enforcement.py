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
    # Weights payloads are per-method now; supply a full valid CARD bundle
    # so the request itself is well-formed and only role enforcement can
    # cause a 403.
    body = {
        "collection_method": "CARD",
        "weights": {
            "historical_failure_rate": 0.25,
            "day_of_month_vs_payday": 0.20,
            "days_since_last_payment": 0.15,
            "instalment_position": 0.10,
            "order_value_vs_average": 0.10,
            "card_health": 0.10,
            "card_type": 0.05,
            "debit_order_return_history": 0.05,
        },
    }
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
        json={
            "collection_method": "CARD",
            "weights": {
                "historical_failure_rate": 0.25,
                "day_of_month_vs_payday": 0.20,
                "days_since_last_payment": 0.15,
                "instalment_position": 0.10,
                "order_value_vs_average": 0.10,
                "card_health": 0.10,
                "card_type": 0.05,
                "debit_order_return_history": 0.05,
            },
        },
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


@pytest.mark.asyncio
async def test_scores_upload_requires_admin_or_manager(
    async_client, sa_admin_user, sa_manager_user, sa_viewer_user
):
    """M1 regression: POST /v1/scores/upload was using `get_current_user`,
    which meant VIEWERs could persist scoring rows and fire alert
    notifications by uploading a CSV. It now mirrors /v1/backtest/upload's
    require_admin_or_manager gate."""
    viewer = await _token(async_client, TEST_VIEWER_EMAIL)
    files = {"file": ("not_a_csv.txt", b"irrelevant", "text/plain")}
    r = await async_client.post("/v1/scores/upload", headers=_h(viewer), files=files)
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


# ---- Dual-auth writes (M2 fix): POST /v1/score + POST /v1/outcomes ----


def _score_body() -> dict:
    return {
        "customer_id": "role_test_cust",
        "collection_id": "role_test_col",
        "collection_amount": 500,
        "collection_currency": "ZAR",
        "collection_due_date": "2026-09-15",
        "collection_method": "CARD",
        "customer_data": {"total_payments": 10, "successful_payments": 8},
    }


@pytest.mark.asyncio
async def test_score_via_jwt_requires_admin_or_manager(
    async_client, sa_admin_user, sa_manager_user, sa_viewer_user
):
    """M2 regression. Pre-fix, `POST /v1/score` via a VIEWER JWT
    succeeded — VIEWER is documented read-only, but the dual-auth
    dep skipped the role check. Now blocks 403."""
    admin = await _token(async_client, TEST_USER_EMAIL)
    manager = await _token(async_client, TEST_MANAGER_EMAIL)
    viewer = await _token(async_client, TEST_VIEWER_EMAIL)

    body = _score_body()
    assert (await async_client.post("/v1/score", headers=_h(admin), json=body)).status_code == 200
    assert (await async_client.post("/v1/score", headers=_h(manager), json=body)).status_code == 200
    assert (await async_client.post("/v1/score", headers=_h(viewer), json=body)).status_code == 403


@pytest.mark.asyncio
async def test_score_via_api_key_still_works(async_client, sa_tenant):
    """The API-key branch of the dual-auth dep is unchanged — no role
    check for lender integrations (a key represents the tenant, not a
    dashboard user)."""
    r = await async_client.post(
        "/v1/score",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        json=_score_body(),
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_outcomes_via_jwt_requires_admin_or_manager(
    async_client, sa_admin_user, sa_manager_user, sa_viewer_user
):
    """Same fix, outcomes side. Extra stakes: outcomes feed the
    labelled ML dataset — a VIEWER-generated outcome silently
    corrupts training data."""
    admin = await _token(async_client, TEST_USER_EMAIL)
    manager = await _token(async_client, TEST_MANAGER_EMAIL)
    viewer = await _token(async_client, TEST_VIEWER_EMAIL)

    # Score once as admin to get a score_id we can attach outcomes to.
    r = await async_client.post("/v1/score", headers=_h(admin), json=_score_body())
    score_id = r.json()["score_id"]

    def _body(cid: str) -> dict:
        return {
            "score_id": score_id,
            "collection_id": cid,
            "outcome": "SUCCESS",
            "attempted_at": "2026-09-15T10:00:00Z",
        }

    assert (await async_client.post("/v1/outcomes", headers=_h(admin), json=_body("m2_a"))).status_code == 201
    # Manager can outcome a DIFFERENT collection (score_id is 1:1 with outcomes).
    r2 = await async_client.post("/v1/score", headers=_h(admin), json={**_score_body(), "collection_id": "role_test_col2"})
    body_m = {**_body("m2_m"), "score_id": r2.json()["score_id"]}
    assert (await async_client.post("/v1/outcomes", headers=_h(manager), json=body_m)).status_code == 201
    # Viewer blocked.
    r3 = await async_client.post("/v1/score", headers=_h(admin), json={**_score_body(), "collection_id": "role_test_col3"})
    body_v = {**_body("m2_v"), "score_id": r3.json()["score_id"]}
    assert (await async_client.post("/v1/outcomes", headers=_h(viewer), json=body_v)).status_code == 403


@pytest.mark.asyncio
async def test_outcomes_via_api_key_still_works(async_client, sa_tenant):
    """API-key branch unchanged for /v1/outcomes."""
    # Score first to have a target.
    r = await async_client.post(
        "/v1/score",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        json=_score_body(),
    )
    score_id = r.json()["score_id"]
    r = await async_client.post(
        "/v1/outcomes",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        json={
            "score_id": score_id,
            "collection_id": "role_test_col_apikey",
            "outcome": "SUCCESS",
            "attempted_at": "2026-09-15T10:00:00Z",
        },
    )
    assert r.status_code == 201
