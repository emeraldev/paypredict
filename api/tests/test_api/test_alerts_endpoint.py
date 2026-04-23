"""Tests for alert endpoints and alert evaluation."""
import uuid

import pytest

from app.models.alert import Alert, AlertType
from tests.conftest import TEST_USER_EMAIL, TEST_USER_PASSWORD


async def _login(client) -> str:
    r = await client.post(
        "/v1/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )
    return r.json()["token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _create_alert(db_session, tenant_id, message="Test alert", is_read=False):
    alert = Alert(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        alert_type=AlertType.HIGH_RISK_BATCH,
        message=message,
        metadata_={"test": True},
        is_read=is_read,
    )
    db_session.add(alert)
    await db_session.flush()
    return alert


@pytest.mark.asyncio
async def test_list_alerts_empty(async_client, sa_admin_user):
    token = await _login(async_client)
    r = await async_client.get("/v1/alerts", headers=_auth(token))
    assert r.status_code == 200
    assert r.json()["items"] == []
    assert r.json()["unread_count"] == 0


@pytest.mark.asyncio
async def test_list_alerts_with_data(async_client, sa_admin_user, sa_tenant, db_session):
    await _create_alert(db_session, sa_tenant.id, "Alert 1", is_read=False)
    await _create_alert(db_session, sa_tenant.id, "Alert 2", is_read=True)

    token = await _login(async_client)
    r = await async_client.get("/v1/alerts", headers=_auth(token))
    assert r.status_code == 200
    assert len(r.json()["items"]) == 2
    assert r.json()["unread_count"] == 1


@pytest.mark.asyncio
async def test_list_alerts_unread_only(async_client, sa_admin_user, sa_tenant, db_session):
    await _create_alert(db_session, sa_tenant.id, "Unread", is_read=False)
    await _create_alert(db_session, sa_tenant.id, "Read", is_read=True)

    token = await _login(async_client)
    r = await async_client.get("/v1/alerts?unread_only=true", headers=_auth(token))
    assert len(r.json()["items"]) == 1
    assert r.json()["items"][0]["message"] == "Unread"


@pytest.mark.asyncio
async def test_mark_alert_read(async_client, sa_admin_user, sa_tenant, db_session):
    alert = await _create_alert(db_session, sa_tenant.id)

    token = await _login(async_client)
    r = await async_client.patch(
        f"/v1/alerts/{alert.id}/read", headers=_auth(token)
    )
    assert r.status_code == 200

    # Verify unread count dropped
    r2 = await async_client.get("/v1/alerts", headers=_auth(token))
    assert r2.json()["unread_count"] == 0


@pytest.mark.asyncio
async def test_mark_all_read(async_client, sa_admin_user, sa_tenant, db_session):
    await _create_alert(db_session, sa_tenant.id, "A1")
    await _create_alert(db_session, sa_tenant.id, "A2")

    token = await _login(async_client)
    r = await async_client.patch("/v1/alerts/read-all", headers=_auth(token))
    assert r.status_code == 200
    assert r.json()["marked_read"] == 2

    r2 = await async_client.get("/v1/alerts", headers=_auth(token))
    assert r2.json()["unread_count"] == 0


@pytest.mark.asyncio
async def test_mark_alert_not_found(async_client, sa_admin_user):
    token = await _login(async_client)
    r = await async_client.patch(
        "/v1/alerts/00000000-0000-0000-0000-000000000000/read",
        headers=_auth(token),
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_alerts_no_auth(async_client, sa_tenant):
    r = await async_client.get("/v1/alerts")
    assert r.status_code == 401
