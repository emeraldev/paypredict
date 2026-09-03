"""Auth request/response schemas for dashboard session endpoints."""
from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel, Field

from app.models.tenant import FactorSet, Market, Plan
from app.models.user import UserRole
from app.schemas._validators import validate_password


# Applied only at password-SET time. Login accepts any non-empty string
# so a legacy short password can still get its owner in to rotate.
Password = Annotated[str, AfterValidator(validate_password)]


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1)


class ChangePasswordRequest(BaseModel):
    """Self-service password change. The user must supply the current
    password to prove control of the session (defence in depth against
    a stolen JWT). The new password goes through the platform policy
    validator."""

    current_password: str = Field(min_length=1)
    new_password: Password


class TenantSummary(BaseModel):
    id: UUID
    name: str
    market: Market
    factor_set: FactorSet
    plan: Plan


class UserResponse(BaseModel):
    id: UUID
    email: str
    name: str
    role: UserRole
    last_login_at: datetime | None
    tenant: TenantSummary


class LoginResponse(BaseModel):
    token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserResponse


class LogoutResponse(BaseModel):
    message: str = "Logged out"


class ChangePasswordResponse(BaseModel):
    """Successful password change returns a fresh token so the client
    doesn't have to log in again — the OLD token is now dead by the
    iat-vs-password_changed_at check in `get_current_user`."""

    token: str
    token_type: str = "bearer"
    expires_in: int
