"""Dashboard session auth endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.docs_config import DASHBOARD_API_RESPONSES
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    ChangePasswordResponse,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    TenantSummary,
    UserResponse,
)
from app.services.auth_service import (
    LoginResult,
    authenticate_user,
    change_password,
    create_access_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["Auth"], responses=DASHBOARD_API_RESPONSES)


def _user_to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        last_login_at=user.last_login_at,
        tenant=TenantSummary(
            id=user.tenant.id,
            name=user.tenant.name,
            market=user.tenant.market,
            factor_set=user.tenant.factor_set,
            plan=user.tenant.plan,
        ),
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """Exchange email + password for a session JWT.

    Failed logins increment a per-user counter; on the 5th consecutive
    miss the account locks for 15 minutes. Response body is generic
    ("Invalid email or password") for both wrong-password and locked
    accounts so an attacker can't infer which emails exist or which
    are currently under attack. Locked accounts additionally get a
    `Retry-After` header so a well-behaved client can back off.
    """
    result, user, retry_after = await authenticate_user(
        db, payload.email, payload.password
    )
    # Commit either way — the failure-counter increment / lockout must
    # persist so successive attempts stack.
    await db.commit()

    if result is LoginResult.LOCKED:
        assert retry_after is not None
        # HTTPException's own `headers` is how a raised response gets
        # arbitrary headers — writing to a `response: Response` injected
        # into the route wouldn't reach the client on the exception path.
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
            headers={"Retry-After": str(retry_after)},
        )
    if result is LoginResult.INVALID or user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token, expires_in = create_access_token(user.id)
    return LoginResponse(
        token=token,
        expires_in=expires_in,
        user=_user_to_response(user),
    )


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)) -> UserResponse:
    """Return the current user from the session JWT."""
    return _user_to_response(user)


@router.post("/logout", response_model=LogoutResponse)
async def logout(_: User = Depends(get_current_user)) -> LogoutResponse:
    """Stateless JWT — server-side logout is a no-op.

    The client must drop the token. For a real one-click "sign out
    everywhere" use POST /v1/auth/change-password (rotates the
    password + invalidates every outstanding session via the
    password_changed_at check).
    """
    return LogoutResponse()


@router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password_endpoint(
    payload: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChangePasswordResponse:
    """Self-service password change.

    Requires the caller's CURRENT password even though they hold a
    valid JWT — a stolen session should not be enough to lock the
    real owner out. The new password goes through the platform
    policy (length 12–72, 3 of 4 character classes).

    Side effects on success:
      - password_hash rotated;
      - password_changed_at bumped to now, which invalidates every
        prior JWT for this user via the iat check in
        `get_current_user` — including the token the caller just
        used;
      - any failed-login lock cleared (the owner has proved control);
      - a fresh token returned so the client stays signed in without
        a round-trip through /login.

    Returns 400 if the current password is wrong. Same body shape
    as /login (`token`, `token_type`, `expires_in`).
    """
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    await change_password(db, user, payload.new_password)
    await db.commit()

    token, expires_in = create_access_token(user.id)
    return ChangePasswordResponse(token=token, expires_in=expires_in)
