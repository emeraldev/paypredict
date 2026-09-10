"""Tests for the PR that turned auth from label-only into enforced.

Covers: password policy at set-time, failed-login lockout, JWT
revocation via password_changed_at, self-service change-password
flow. The pre-existing test_auth_endpoint.py file still holds the
basic happy-path login + /me + /logout coverage.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.config import settings
from app.models.user import User
from app.services.auth_service import create_access_token
from tests.conftest import TEST_USER_EMAIL, TEST_USER_PASSWORD


# ---- Password policy at set-time ---------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [
    "short",                        # too short
    "alllowercaseandlong123",       # only 2 classes (lower, digit)
    "ALLUPPERCASEANDLONG123",       # only 2 classes (upper, digit)
    "NoSymbolsOrDigits",            # only 2 classes (upper, lower)
    "12345678901234",               # only 1 class (digit)
    "a" * 73,                       # over the 72-byte bcrypt cap
    "",                             # empty
])
async def test_team_invite_rejects_weak_password(
    async_client, sa_admin_user, bad
):
    login = await async_client.post(
        "/v1/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )
    token = login.json()["token"]
    r = await async_client.post(
        "/v1/config/team",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "email": "weak-pass@test.dev",
            "name": "Weak Password",
            "password": bad,
            "role": "VIEWER",
        },
    )
    assert r.status_code == 422, f"policy must reject {bad!r}"
    assert "password" in str(r.json()["detail"])


@pytest.mark.asyncio
@pytest.mark.parametrize("good", [
    "Strong-Pass-1234",             # upper + lower + digit + symbol
    "correcthorse-battery-9",       # lower + digit + symbol
    "TWELVE-CHARS1",                # upper + digit + symbol
    "Aa1" + "b" * 9,                # exactly 12 chars, three classes
])
async def test_team_invite_accepts_strong_password(
    async_client, sa_admin_user, good
):
    login = await async_client.post(
        "/v1/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )
    token = login.json()["token"]
    r = await async_client.post(
        "/v1/config/team",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "email": f"good-{hash(good) & 0xffff}@test.dev",
            "name": "Good Password",
            "password": good,
            "role": "VIEWER",
        },
    )
    assert r.status_code == 201, f"policy must accept {good!r}: {r.text}"


# ---- Failed-login lockout ----------------------------------------------


@pytest.mark.asyncio
async def test_lockout_triggers_after_threshold(
    async_client, sa_admin_user, db_session
):
    """N consecutive wrong passwords → account locks + Retry-After header."""
    for i in range(settings.login_lockout_threshold):
        r = await async_client.post(
            "/v1/auth/login",
            json={"email": TEST_USER_EMAIL, "password": f"wrong-{i}"},
        )
        assert r.status_code == 401, f"attempt {i} must fail"

    # The final wrong attempt sets locked_until on the row.
    await db_session.refresh(sa_admin_user)
    assert sa_admin_user.locked_until is not None
    assert sa_admin_user.failed_login_count >= settings.login_lockout_threshold

    # A subsequent attempt (even with the CORRECT password) is refused
    # while locked. Response body is generic; Retry-After header carries
    # the wait window.
    r = await async_client.post(
        "/v1/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )
    assert r.status_code == 401
    assert "Invalid email or password" in r.json()["detail"]
    assert "retry-after" in {k.lower() for k in r.headers.keys()}
    retry_after = int(r.headers["retry-after"])
    assert 0 < retry_after <= settings.login_lockout_minutes * 60


@pytest.mark.asyncio
async def test_lockout_clears_after_cooldown(
    async_client, sa_admin_user, db_session
):
    """A user whose lock has expired can log in again on the correct password."""
    # Arm the lock by hand — cheaper than the loop, and this test cares
    # about the release path, not the trigger.
    from sqlalchemy import update
    past = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db_session.execute(
        update(User)
        .where(User.id == sa_admin_user.id)
        .values(
            failed_login_count=settings.login_lockout_threshold,
            locked_until=past,
        )
    )
    await db_session.flush()

    r = await async_client.post(
        "/v1/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )
    assert r.status_code == 200

    # On the successful auth we clear both fields.
    await db_session.refresh(sa_admin_user)
    assert sa_admin_user.failed_login_count == 0
    assert sa_admin_user.locked_until is None


@pytest.mark.asyncio
async def test_failed_counter_resets_on_success(
    async_client, sa_admin_user, db_session
):
    """A wrong attempt below the threshold followed by a correct one clears
    the counter — otherwise even a legitimate user would gradually lock
    themselves out over time."""
    for _ in range(2):
        r = await async_client.post(
            "/v1/auth/login",
            json={"email": TEST_USER_EMAIL, "password": "wrong"},
        )
        assert r.status_code == 401

    await db_session.refresh(sa_admin_user)
    assert sa_admin_user.failed_login_count == 2

    r = await async_client.post(
        "/v1/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )
    assert r.status_code == 200

    await db_session.refresh(sa_admin_user)
    assert sa_admin_user.failed_login_count == 0


@pytest.mark.asyncio
async def test_lockout_does_not_leak_email_existence(async_client, sa_admin_user):
    """An unknown-email login returns INVALID, never LOCKED — otherwise the
    LOCKED-vs-INVALID distinction would tell an attacker which emails
    are registered."""
    for _ in range(settings.login_lockout_threshold + 3):
        r = await async_client.post(
            "/v1/auth/login",
            json={"email": "nobody-here@test.dev", "password": "whatever"},
        )
        assert r.status_code == 401
        # An unknown email should never trigger a Retry-After header —
        # that header only exists on a real lockout for a real user.
        assert "retry-after" not in {k.lower() for k in r.headers.keys()}


# ---- Password-change flow + JWT revocation -----------------------------


@pytest.mark.asyncio
async def test_change_password_requires_current_password(
    async_client, sa_admin_user
):
    login = await async_client.post(
        "/v1/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )
    token = login.json()["token"]
    r = await async_client.post(
        "/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "not-the-current-one",
            "new_password": "Strong-New-Pass-1",
        },
    )
    assert r.status_code == 400
    assert "current password" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_change_password_enforces_policy_on_new_password(
    async_client, sa_admin_user
):
    login = await async_client.post(
        "/v1/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )
    token = login.json()["token"]
    r = await async_client.post(
        "/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": TEST_USER_PASSWORD,
            "new_password": "short",
        },
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_change_password_rotates_and_returns_fresh_token(
    async_client, sa_admin_user, db_session
):
    login = await async_client.post(
        "/v1/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )
    old_token = login.json()["token"]

    new_pw = "New-Strong-Pass-9"
    r = await async_client.post(
        "/v1/auth/change-password",
        headers={"Authorization": f"Bearer {old_token}"},
        json={
            "current_password": TEST_USER_PASSWORD,
            "new_password": new_pw,
        },
    )
    assert r.status_code == 200, r.text
    fresh_token = r.json()["token"]
    assert fresh_token and fresh_token != old_token

    # Fresh token works.
    r = await async_client.get(
        "/v1/auth/me",
        headers={"Authorization": f"Bearer {fresh_token}"},
    )
    assert r.status_code == 200

    # Login with the new password works.
    r = await async_client.post(
        "/v1/auth/login",
        json={"email": TEST_USER_EMAIL, "password": new_pw},
    )
    assert r.status_code == 200

    # Login with the OLD password fails.
    r = await async_client.post(
        "/v1/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_stale_jwt_rejected_after_password_change(
    async_client, sa_admin_user, db_session
):
    """A token issued strictly before password_changed_at is invalidated —
    this is our server-side revocation surface."""
    # Mint a token, THEN bump password_changed_at into the future so
    # the token's iat is unambiguously before the rotation. Waiting a
    # real second would also work but adds test-suite latency for
    # nothing.
    token, _ = create_access_token(sa_admin_user.id)

    from sqlalchemy import update
    future = datetime.now(timezone.utc) + timedelta(seconds=5)
    await db_session.execute(
        update(User)
        .where(User.id == sa_admin_user.id)
        .values(password_changed_at=future)
    )
    await db_session.flush()

    r = await async_client.get(
        "/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 401
    assert "invalidated" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_null_password_changed_at_accepts_all_tokens(
    async_client, sa_admin_user, db_session
):
    """NULL password_changed_at means 'never rotated' — every token is
    accepted. This is the pre-migration posture so the auth-hardening
    rollout doesn't sign users out."""
    # Ensure NULL (the fixture leaves it NULL by default; be explicit).
    from sqlalchemy import update
    await db_session.execute(
        update(User)
        .where(User.id == sa_admin_user.id)
        .values(password_changed_at=None)
    )
    await db_session.flush()

    token, _ = create_access_token(sa_admin_user.id)
    r = await async_client.get(
        "/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_change_password_clears_any_lock(
    async_client, sa_admin_user, db_session
):
    """If the account is locked and the owner rotates via a still-valid
    JWT, the rotate clears the lock — the owner has proved control."""
    login = await async_client.post(
        "/v1/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )
    token = login.json()["token"]

    # Arm the lock by hand.
    from sqlalchemy import update
    future = datetime.now(timezone.utc) + timedelta(minutes=15)
    await db_session.execute(
        update(User)
        .where(User.id == sa_admin_user.id)
        .values(
            failed_login_count=99,
            locked_until=future,
        )
    )
    await db_session.flush()

    r = await async_client.post(
        "/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": TEST_USER_PASSWORD,
            "new_password": "Post-Lock-Pass-2026",
        },
    )
    assert r.status_code == 200

    await db_session.refresh(sa_admin_user)
    assert sa_admin_user.failed_login_count == 0
    assert sa_admin_user.locked_until is None


# ---- Helpers -----------------------------------------------------------

@pytest.mark.asyncio
async def test_login_shape_smoke(async_client, sa_admin_user, db_session):
    """Sanity check that fixtures + new endpoint still produce a live
    tenant/user pair (regression guard for the tuple return refactor)."""
    r = await async_client.post(
        "/v1/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )
    assert r.status_code == 200
    row = (await db_session.execute(
        select(User).where(User.email == TEST_USER_EMAIL)
    )).scalar_one()
    assert row.last_login_at is not None
