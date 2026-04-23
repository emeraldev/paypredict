"""Pydantic schemas for dashboard config endpoints (api-keys, team, alerts)."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.tenant import EmailDigest
from app.models.user import UserRole


# ---- API Keys ----

class ApiKeyListItem(BaseModel):
    id: UUID
    prefix: str
    label: str
    is_active: bool
    last_used_at: datetime | None
    created_at: datetime


class ApiKeyCreateRequest(BaseModel):
    label: str = Field(min_length=1, max_length=255)


class ApiKeyCreateResponse(BaseModel):
    """Returned ONLY on creation — the full key is never shown again."""
    id: UUID
    key: str
    prefix: str
    label: str
    message: str = "Copy this key now. You will not be able to see it again."


class ApiKeyToggleRequest(BaseModel):
    is_active: bool


class ApiKeyListResponse(BaseModel):
    items: list[ApiKeyListItem]


# ---- Team ----

class TeamMemberItem(BaseModel):
    id: UUID
    email: str
    name: str
    role: UserRole
    last_login_at: datetime | None
    created_at: datetime


class TeamInviteRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=6, max_length=255)
    role: UserRole = UserRole.VIEWER


class TeamUpdateRequest(BaseModel):
    role: UserRole


class TeamListResponse(BaseModel):
    items: list[TeamMemberItem]


# ---- Alerts ----

class AlertsConfigResponse(BaseModel):
    high_risk_threshold: float
    webhook_url: str | None
    slack_webhook_url: str | None
    email_digest: EmailDigest
    email_recipients: list[str]


class AlertsConfigUpdateRequest(BaseModel):
    high_risk_threshold: float | None = Field(None, ge=0.0, le=1.0)
    webhook_url: str | None = None
    slack_webhook_url: str | None = None
    email_digest: EmailDigest | None = None
    email_recipients: list[str] | None = None
