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
