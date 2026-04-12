"""Tests for auth endpoints: POST /v1/auth/login, GET /v1/auth/me, POST /v1/auth/logout."""
import pytest

from tests.conftest import TEST_USER_EMAIL, TEST_USER_PASSWORD


@pytest.mark.asyncio
async def test_login_success(async_client, sa_admin_user):
    """Valid email + password → returns JWT + user with tenant."""
    response = await async_client.post(
        "/v1/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )
    assert response.status_code == 200

    data = response.json()
    assert "token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0

    user = data["user"]
    assert user["email"] == TEST_USER_EMAIL
    assert user["name"] == "Test Admin"
    assert user["role"] == "ADMIN"

    tenant = user["tenant"]
    assert tenant["name"] == "Test SA Tenant"
    assert tenant["market"] == "SA"


@pytest.mark.asyncio
async def test_login_wrong_password(async_client, sa_admin_user):
    """Wrong password → 401."""
    response = await async_client.post(
        "/v1/auth/login",
        json={"email": TEST_USER_EMAIL, "password": "wrong-password"},
    )
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_unknown_email(async_client, sa_admin_user):
    """Unknown email → 401 (same message as wrong password)."""
    response = await async_client.post(
        "/v1/auth/login",
        json={"email": "nobody@test.com", "password": TEST_USER_PASSWORD},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_case_insensitive(async_client, sa_admin_user):
    """Email lookup should be case-insensitive."""
    response = await async_client.post(
        "/v1/auth/login",
        json={"email": TEST_USER_EMAIL.upper(), "password": TEST_USER_PASSWORD},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_me_with_valid_token(async_client, sa_admin_user):
    """GET /me with valid JWT → returns user."""
    login = await async_client.post(
        "/v1/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )
    token = login.json()["token"]

    response = await async_client.get(
        "/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == TEST_USER_EMAIL


@pytest.mark.asyncio
async def test_me_without_token(async_client, sa_tenant):
    """GET /me with no auth header → 401."""
    response = await async_client.get("/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_with_garbage_token(async_client, sa_tenant):
    """GET /me with invalid JWT → 401."""
    response = await async_client.get(
        "/v1/auth/me",
        headers={"Authorization": "Bearer totally-bogus-token"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout(async_client, sa_admin_user):
    """POST /logout with valid JWT → 200."""
    login = await async_client.post(
        "/v1/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )
    token = login.json()["token"]

    response = await async_client.post(
        "/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Logged out"


@pytest.mark.asyncio
async def test_login_validation_error(async_client, sa_tenant):
    """Missing fields → 422."""
    response = await async_client.post(
        "/v1/auth/login",
        json={"email": ""},
    )
    assert response.status_code == 422
