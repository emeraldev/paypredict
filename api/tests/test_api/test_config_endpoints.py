"""Tests for config endpoints: api-keys, team, alerts."""
import pytest

from tests.conftest import TEST_USER_EMAIL, TEST_USER_PASSWORD


async def _login(client, email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD) -> str:
    r = await client.post(
        "/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert r.status_code == 200
    return r.json()["token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ==================== API Keys ====================


@pytest.mark.asyncio
async def test_api_keys_list(async_client, sa_admin_user):
    """List returns at least the seed key."""
    token = await _login(async_client)
    r = await async_client.get("/v1/config/api-keys", headers=_auth(token))
    assert r.status_code == 200
    # Seed creates a test key for the SA tenant
    assert len(r.json()["items"]) >= 1


@pytest.mark.asyncio
async def test_api_keys_create_and_revoke(async_client, sa_admin_user):
    """Create a key, verify it appears in list, then delete it."""
    token = await _login(async_client)

    # Create
    r = await async_client.post(
        "/v1/config/api-keys",
        headers=_auth(token),
        json={"label": "CI Key"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["label"] == "CI Key"
    assert data["key"].startswith("pk_live_")
    key_id = data["id"]

    # Verify it's in the list
    r2 = await async_client.get("/v1/config/api-keys", headers=_auth(token))
    ids = [i["id"] for i in r2.json()["items"]]
    assert key_id in ids

    # Delete
    r3 = await async_client.delete(
        f"/v1/config/api-keys/{key_id}", headers=_auth(token)
    )
    assert r3.status_code == 204

    # Verify it's gone
    r4 = await async_client.get("/v1/config/api-keys", headers=_auth(token))
    ids2 = [i["id"] for i in r4.json()["items"]]
    assert key_id not in ids2


@pytest.mark.asyncio
async def test_api_keys_toggle(async_client, sa_admin_user):
    """Deactivate then reactivate a key."""
    token = await _login(async_client)

    # Create
    r = await async_client.post(
        "/v1/config/api-keys",
        headers=_auth(token),
        json={"label": "Toggle Test"},
    )
    key_id = r.json()["id"]

    # Deactivate
    r2 = await async_client.patch(
        f"/v1/config/api-keys/{key_id}",
        headers=_auth(token),
        json={"is_active": False},
    )
    assert r2.status_code == 200
    assert r2.json()["is_active"] is False

    # Reactivate
    r3 = await async_client.patch(
        f"/v1/config/api-keys/{key_id}",
        headers=_auth(token),
        json={"is_active": True},
    )
    assert r3.json()["is_active"] is True


@pytest.mark.asyncio
async def test_api_keys_not_found(async_client, sa_admin_user):
    token = await _login(async_client)
    r = await async_client.delete(
        "/v1/config/api-keys/00000000-0000-0000-0000-000000000000",
        headers=_auth(token),
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_api_keys_no_auth(async_client, sa_tenant):
    r = await async_client.get("/v1/config/api-keys")
    assert r.status_code == 401


# ==================== Team ====================


@pytest.mark.asyncio
async def test_team_list(async_client, sa_admin_user):
    """Admin can list team members."""
    token = await _login(async_client)
    r = await async_client.get("/v1/config/team", headers=_auth(token))
    assert r.status_code == 200
    assert len(r.json()["items"]) >= 1


@pytest.mark.asyncio
async def test_team_invite_and_remove(async_client, sa_admin_user):
    """Admin invites a new viewer, then removes them."""
    token = await _login(async_client)

    # Invite
    r = await async_client.post(
        "/v1/config/team",
        headers=_auth(token),
        json={
            "email": "viewer@test.dev",
            "name": "Test Viewer",
            "password": "viewer123",
            "role": "VIEWER",
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == "viewer@test.dev"
    assert data["role"] == "VIEWER"
    user_id = data["id"]

    # Remove
    r2 = await async_client.delete(
        f"/v1/config/team/{user_id}", headers=_auth(token)
    )
    assert r2.status_code == 204


@pytest.mark.asyncio
async def test_team_update_role(async_client, sa_admin_user):
    """Admin can change a member's role."""
    token = await _login(async_client)

    # Invite
    r = await async_client.post(
        "/v1/config/team",
        headers=_auth(token),
        json={
            "email": "role-change@test.dev",
            "name": "Role Changer",
            "password": "change123",
            "role": "VIEWER",
        },
    )
    user_id = r.json()["id"]

    # Update to MANAGER
    r2 = await async_client.patch(
        f"/v1/config/team/{user_id}",
        headers=_auth(token),
        json={"role": "MANAGER"},
    )
    assert r2.status_code == 200
    assert r2.json()["role"] == "MANAGER"

    # Cleanup
    await async_client.delete(f"/v1/config/team/{user_id}", headers=_auth(token))


@pytest.mark.asyncio
async def test_team_duplicate_email(async_client, sa_admin_user):
    """Can't invite with an email already in use."""
    token = await _login(async_client)
    r = await async_client.post(
        "/v1/config/team",
        headers=_auth(token),
        json={
            "email": TEST_USER_EMAIL,
            "name": "Duplicate",
            "password": "dup12345",
            "role": "VIEWER",
        },
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_team_viewer_forbidden(async_client, sa_admin_user):
    """Non-admin user cannot access team endpoints."""
    admin_token = await _login(async_client)

    # Create a viewer
    r = await async_client.post(
        "/v1/config/team",
        headers=_auth(admin_token),
        json={
            "email": "viewer-forbidden@test.dev",
            "name": "Forbidden Viewer",
            "password": "view1234",
            "role": "VIEWER",
        },
    )
    viewer_id = r.json()["id"]

    # Login as viewer
    viewer_token = await _login(
        async_client, email="viewer-forbidden@test.dev", password="view1234"
    )

    # Try to list team → 403
    r2 = await async_client.get("/v1/config/team", headers=_auth(viewer_token))
    assert r2.status_code == 403

    # Cleanup
    await async_client.delete(
        f"/v1/config/team/{viewer_id}", headers=_auth(admin_token)
    )


# ==================== Alerts ====================


@pytest.mark.asyncio
async def test_alerts_get(async_client, sa_admin_user):
    """Get default alerts config."""
    token = await _login(async_client)
    r = await async_client.get("/v1/config/alerts", headers=_auth(token))
    assert r.status_code == 200
    data = r.json()
    assert "high_risk_threshold" in data
    assert "email_digest" in data
    assert data["email_digest"] == "OFF"
    # Webhook secret should be exposed and have the whsec_ prefix
    assert data["webhook_secret"].startswith("whsec_")


@pytest.mark.asyncio
async def test_alerts_rotate_secret(async_client, sa_admin_user):
    """Rotating the secret returns a new whsec_-prefixed value that
    differs from the previous one, and persists across reads."""
    token = await _login(async_client)

    initial = await async_client.get("/v1/config/alerts", headers=_auth(token))
    original_secret = initial.json()["webhook_secret"]

    rotated = await async_client.post(
        "/v1/config/alerts/regenerate-secret", headers=_auth(token)
    )
    assert rotated.status_code == 200
    new_secret = rotated.json()["webhook_secret"]
    assert new_secret.startswith("whsec_")
    assert new_secret != original_secret

    # GET reflects the new secret
    after = await async_client.get("/v1/config/alerts", headers=_auth(token))
    assert after.json()["webhook_secret"] == new_secret


@pytest.mark.asyncio
async def test_alerts_rotate_no_auth(async_client, sa_tenant):
    """Rotation requires session auth."""
    r = await async_client.post("/v1/config/alerts/regenerate-secret")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_alerts_update(async_client, sa_admin_user):
    """Update alerts config and verify."""
    token = await _login(async_client)

    r = await async_client.put(
        "/v1/config/alerts",
        headers=_auth(token),
        json={
            "high_risk_threshold": 0.35,
            "email_digest": "WEEKLY",
            "email_recipients": ["ops@test.dev"],
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["high_risk_threshold"] == 0.35
    assert data["email_digest"] == "WEEKLY"
    assert data["email_recipients"] == ["ops@test.dev"]

    # Verify it persists
    r2 = await async_client.get("/v1/config/alerts", headers=_auth(token))
    assert r2.json()["high_risk_threshold"] == 0.35


@pytest.mark.asyncio
async def test_alerts_partial_update(async_client, sa_admin_user):
    """Only update the fields you send — others stay untouched."""
    token = await _login(async_client)

    # Set a baseline
    await async_client.put(
        "/v1/config/alerts",
        headers=_auth(token),
        json={"high_risk_threshold": 0.25, "email_digest": "DAILY"},
    )

    # Only update webhook
    r = await async_client.put(
        "/v1/config/alerts",
        headers=_auth(token),
        json={"webhook_url": "https://example.com/hook"},
    )
    data = r.json()
    assert data["webhook_url"] == "https://example.com/hook"
    # threshold and digest should remain as previously set
    assert data["high_risk_threshold"] == 0.25
    assert data["email_digest"] == "DAILY"


@pytest.mark.asyncio
async def test_alerts_no_auth(async_client, sa_tenant):
    r = await async_client.get("/v1/config/alerts")
    assert r.status_code == 401


# ==================== Weights (per collection method) ====================


CARD_WEIGHTS = {
    "historical_failure_rate": 0.25,
    "day_of_month_vs_payday": 0.20,
    "days_since_last_payment": 0.15,
    "instalment_position": 0.10,
    "order_value_vs_average": 0.10,
    "card_health": 0.10,
    "card_type": 0.05,
    "debit_order_return_history": 0.05,
}


@pytest.mark.asyncio
async def test_get_weights_grouped_by_method(async_client, sa_admin_user):
    """The SA test tenant is seeded with weights for CARD + DEBIT_ORDER.
    GET should return both, each with its label and 8 factors."""
    token = await _login(async_client)
    r = await async_client.get("/v1/config/weights", headers=_auth(token))
    assert r.status_code == 200
    body = r.json()
    methods = {m["collection_method"]: m for m in body["methods"]}
    assert set(methods.keys()) == {"CARD", "DEBIT_ORDER"}
    for entry in methods.values():
        assert entry["method_label"] in ("Card", "Debit Order")
        assert len(entry["factors"]) == 8
        # Each factor carries its plain-English label and one-liner.
        for f in entry["factors"]:
            assert f["label"]
            assert f["description"]
        assert abs(entry["total_weight"] - 1.0) < 0.01


@pytest.mark.asyncio
async def test_put_weights_isolates_method(async_client, sa_admin_user):
    """PUT for CARD must leave DEBIT_ORDER weights untouched — the whole
    point of the per-method schema."""
    token = await _login(async_client)

    # Skew CARD weights toward historical_failure_rate.
    skewed = {**CARD_WEIGHTS, "historical_failure_rate": 0.40, "day_of_month_vs_payday": 0.05}
    r = await async_client.put(
        "/v1/config/weights",
        headers=_auth(token),
        json={"collection_method": "CARD", "weights": skewed},
    )
    assert r.status_code == 200
    body = r.json()
    methods = {m["collection_method"]: m for m in body["methods"]}
    card_hfr = next(f for f in methods["CARD"]["factors"] if f["factor_name"] == "historical_failure_rate")
    debit_hfr = next(f for f in methods["DEBIT_ORDER"]["factors"] if f["factor_name"] == "historical_failure_rate")
    assert card_hfr["weight"] == 0.40
    assert debit_hfr["weight"] == 0.25, (
        "DEBIT_ORDER weights should be untouched by a CARD-only PUT"
    )


@pytest.mark.asyncio
async def test_put_weights_rejects_wrong_sum(async_client, sa_admin_user):
    token = await _login(async_client)
    r = await async_client.put(
        "/v1/config/weights",
        headers=_auth(token),
        json={
            "collection_method": "CARD",
            "weights": {"historical_failure_rate": 0.5},
        },
    )
    assert r.status_code == 400
    assert "sum" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_put_weights_rejects_unknown_factor_for_method(async_client, sa_admin_user):
    """threshold_headroom belongs to PAYROLL, not CARD — reject it loudly."""
    token = await _login(async_client)
    r = await async_client.put(
        "/v1/config/weights",
        headers=_auth(token),
        json={
            "collection_method": "CARD",
            "weights": {**CARD_WEIGHTS, "threshold_headroom": 0.10},
        },
    )
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert "threshold_headroom" in detail["unknown_factors"]


@pytest.mark.asyncio
async def test_add_method_creates_default_rows(async_client, sa_admin_user):
    """POST /v1/config/weights/methods with a NEW method seeds defaults
    and makes the tab appear in the grouped GET response."""
    token = await _login(async_client)

    # Baseline: SA fixture has CARD + DEBIT_ORDER only.
    r = await async_client.get("/v1/config/weights", headers=_auth(token))
    baseline = {m["collection_method"] for m in r.json()["methods"]}
    assert baseline == {"CARD", "DEBIT_ORDER"}

    # Opt into PAYROLL.
    r = await async_client.post(
        "/v1/config/weights/methods",
        headers=_auth(token),
        json={"collection_method": "PAYROLL"},
    )
    assert r.status_code == 200
    body = r.json()
    methods = {m["collection_method"]: m for m in body["methods"]}
    assert "PAYROLL" in methods
    payroll = methods["PAYROLL"]
    assert len(payroll["factors"]) == 8
    assert abs(payroll["total_weight"] - 1.0) < 0.01
    # Defaults, not zeros.
    threshold_headroom = next(
        f for f in payroll["factors"] if f["factor_name"] == "threshold_headroom"
    )
    assert threshold_headroom["weight"] > 0


@pytest.mark.asyncio
async def test_add_method_is_idempotent(async_client, sa_admin_user):
    """Calling POST for a method the tenant already has must not stomp
    their tuning — return the existing state, no changes."""
    token = await _login(async_client)

    # Tune CARD to a distinctive shape first.
    skewed = {**CARD_WEIGHTS, "historical_failure_rate": 0.40, "day_of_month_vs_payday": 0.05}
    r = await async_client.put(
        "/v1/config/weights",
        headers=_auth(token),
        json={"collection_method": "CARD", "weights": skewed},
    )
    assert r.status_code == 200

    # Now "add" CARD again — should be a no-op.
    r = await async_client.post(
        "/v1/config/weights/methods",
        headers=_auth(token),
        json={"collection_method": "CARD"},
    )
    assert r.status_code == 200
    methods = {m["collection_method"]: m for m in r.json()["methods"]}
    hfr = next(f for f in methods["CARD"]["factors"] if f["factor_name"] == "historical_failure_rate")
    assert hfr["weight"] == 0.40, "Existing tuning must be preserved"


@pytest.mark.asyncio
async def test_add_method_requires_admin_on_jwt(
    async_client, sa_admin_user, sa_manager_user, sa_viewer_user
):
    """Manager + Viewer roles cannot expand the tenant's method set."""
    from tests.conftest import TEST_MANAGER_EMAIL, TEST_VIEWER_EMAIL

    admin = await _login(async_client, email=TEST_USER_EMAIL)
    manager = await _login(async_client, email=TEST_MANAGER_EMAIL)
    viewer = await _login(async_client, email=TEST_VIEWER_EMAIL)

    body = {"collection_method": "PAYROLL"}
    assert (await async_client.post("/v1/config/weights/methods", headers=_auth(manager), json=body)).status_code == 403
    assert (await async_client.post("/v1/config/weights/methods", headers=_auth(viewer), json=body)).status_code == 403
    assert (await async_client.post("/v1/config/weights/methods", headers=_auth(admin), json=body)).status_code == 200




# ==================== API key auth path (H2) ====================


@pytest.mark.asyncio
async def test_api_key_auth_rejects_malformed_token(async_client, sa_tenant):
    """Tokens that don't match the fixed shape return 401 without
    fanning out to the DB."""
    for bad in (
        "not-a-key",
        "pk_live_",              # only env prefix
        "pk_live_short",         # too short
        "pk_live_xxxxxxxxxxxx",  # missing separator + secret
        "pk_live_xxxxxxxxxxxx_", # missing secret
        "pk_live_ZZZZZZZZZZZZ_secret",  # non-hex lookup_id
        "pk_bad_0123456789ab_secret",   # wrong env prefix
    ):
        r = await async_client.post(
            "/v1/score",
            headers={"Authorization": f"Bearer {bad}"},
            json={},
        )
        assert r.status_code == 401, f"expected 401 for {bad!r}, got {r.status_code}"


@pytest.mark.asyncio
async def test_api_key_auth_unknown_lookup_id_returns_401(async_client, sa_tenant):
    """A well-formed but unknown lookup_id returns 401. This confirms the
    single-row SELECT path — a hit for zero rows takes the miss branch
    rather than fanning out."""
    unknown = "pk_test_ffffffffffff_secret_bytes_that_dont_matter_here_xxx"
    r = await async_client.post(
        "/v1/score",
        headers={"Authorization": f"Bearer {unknown}"},
        json={},
    )
    assert r.status_code == 401
