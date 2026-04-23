"""Dashboard session auth endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    TenantSummary,
    UserResponse,
)
from app.services.auth_service import (
    authenticate_user,
    create_access_token,
    touch_last_login,
)

router = APIRouter(prefix="/auth", tags=["auth"])


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
    """Exchange email + password for a session JWT."""
    user = await authenticate_user(db, payload.email, payload.password)
    if user is None:
        # Don't distinguish between unknown email and wrong password.
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token, expires_in = create_access_token(user.id)
    await touch_last_login(db, user.id)
    await db.commit()

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

    The client must drop the token. Once we add a refresh-token table or a
    revocation list we'll do real invalidation here. For now this endpoint
    exists so the dashboard can call a "logout" action and get a 200.
    """
    return LogoutResponse()
