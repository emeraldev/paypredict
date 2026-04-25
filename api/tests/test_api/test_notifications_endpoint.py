"""Tests for notification endpoints."""
import uuid

import pytest

from app.models.notification import Notification, NotificationCategory, NotificationSeverity
from tests.conftest import TEST_USER_EMAIL, TEST_USER_PASSWORD


async def _login(client) -> str:
    r = await client.post(
        "/v1/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )
    return r.json()["token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _create_notification(db_session, tenant_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "tenant_id": tenant_id,
        "category": NotificationCategory.SYSTEM,
        "severity": NotificationSeverity.INFO,
        "event_type": "backtest_complete",
        "title": "Test notification",
        "message": "This is a test",
        "is_read": False,
    }
    defaults.update(kwargs)
    n = Notification(**defaults)
    db_session.add(n)
    await db_session.flush()
    return n


@pytest.mark.asyncio
async def test_list_empty(async_client, sa_admin_user):
    token = await _login(async_client)
    r = await async_client.get("/v1/notifications", headers=_auth(token))
    assert r.status_code == 200
    assert r.json()["items"] == []
    assert r.json()["unread_count"] == 0


@pytest.mark.asyncio
async def test_list_with_data(async_client, sa_admin_user, sa_tenant, db_session):
    await _create_notification(db_session, sa_tenant.id, title="Alert 1", is_read=False)
    await _create_notification(db_session, sa_tenant.id, title="Alert 2", is_read=True)

    token = await _login(async_client)
    r = await async_client.get("/v1/notifications", headers=_auth(token))
    assert r.status_code == 200
    assert len(r.json()["items"]) == 2
    assert r.json()["unread_count"] == 1


@pytest.mark.asyncio
async def test_list_unread_only(async_client, sa_admin_user, sa_tenant, db_session):
    await _create_notification(db_session, sa_tenant.id, title="Unread", is_read=False)
    await _create_notification(db_session, sa_tenant.id, title="Read", is_read=True)

    token = await _login(async_client)
    r = await async_client.get("/v1/notifications?unread_only=true", headers=_auth(token))
    assert len(r.json()["items"]) == 1
    assert r.json()["items"][0]["title"] == "Unread"


@pytest.mark.asyncio
async def test_unread_count(async_client, sa_admin_user, sa_tenant, db_session):
    await _create_notification(db_session, sa_tenant.id, is_read=False)
    await _create_notification(db_session, sa_tenant.id, is_read=False)
    await _create_notification(db_session, sa_tenant.id, is_read=True)

    token = await _login(async_client)
    r = await async_client.get("/v1/notifications/unread-count", headers=_auth(token))
    assert r.status_code == 200
    assert r.json()["unread_count"] == 2


@pytest.mark.asyncio
async def test_mark_read(async_client, sa_admin_user, sa_tenant, db_session):
    n = await _create_notification(db_session, sa_tenant.id, is_read=False)

    token = await _login(async_client)
    r = await async_client.patch(f"/v1/notifications/{n.id}/read", headers=_auth(token))
    assert r.status_code == 200

    r2 = await async_client.get("/v1/notifications/unread-count", headers=_auth(token))
    assert r2.json()["unread_count"] == 0


@pytest.mark.asyncio
async def test_read_all(async_client, sa_admin_user, sa_tenant, db_session):
    await _create_notification(db_session, sa_tenant.id, is_read=False)
    await _create_notification(db_session, sa_tenant.id, is_read=False)

    token = await _login(async_client)
    r = await async_client.post("/v1/notifications/read-all", headers=_auth(token))
    assert r.status_code == 200
    assert r.json()["marked_read"] == 2

    r2 = await async_client.get("/v1/notifications/unread-count", headers=_auth(token))
    assert r2.json()["unread_count"] == 0


@pytest.mark.asyncio
async def test_mark_not_found(async_client, sa_admin_user):
    token = await _login(async_client)
    r = await async_client.patch(
        "/v1/notifications/00000000-0000-0000-0000-000000000000/read",
        headers=_auth(token),
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_notification_has_fields(async_client, sa_admin_user, sa_tenant, db_session):
    """Verify response contains all expected fields."""
    await _create_notification(
        db_session, sa_tenant.id,
        event_type="high_risk_batch",
        severity=NotificationSeverity.CRITICAL,
        category=NotificationCategory.SYSTEM,
        title="High-risk batch detected",
        message="12 of 50 high risk",
        link_to="/dashboard?risk_level=HIGH",
        link_label="View collections",
    )

    token = await _login(async_client)
    r = await async_client.get("/v1/notifications", headers=_auth(token))
    item = r.json()["items"][0]
    assert item["category"] == "SYSTEM"
    assert item["severity"] == "CRITICAL"
    assert item["event_type"] == "high_risk_batch"
    assert item["title"] == "High-risk batch detected"
    assert item["link_to"] == "/dashboard?risk_level=HIGH"
    assert item["link_label"] == "View collections"
    assert "created_at" in item


@pytest.mark.asyncio
async def test_no_auth(async_client, sa_tenant):
    r = await async_client.get("/v1/notifications")
    assert r.status_code == 401
