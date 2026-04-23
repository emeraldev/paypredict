"""Auth request/response schemas for dashboard session endpoints."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.tenant import FactorSet, Market, Plan
from app.models.user import UserRole


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1)


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
