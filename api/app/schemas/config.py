"""Pydantic schemas for dashboard config endpoints (api-keys, team, alerts, weights)."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.score_request import CollectionMethod
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
    webhook_secret: str
    slack_webhook_url: str | None
    email_digest: EmailDigest
    email_recipients: list[str]


class AlertsConfigUpdateRequest(BaseModel):
    high_risk_threshold: float | None = Field(None, ge=0.0, le=1.0)
    webhook_url: str | None = None
    slack_webhook_url: str | None = None
    email_digest: EmailDigest | None = None
    email_recipients: list[str] | None = None


# ---- Weights (per collection method) ----

class WeightsFactorEntry(BaseModel):
    """One factor's weight for a specific collection method.

    `label` and `description` are inlined so integrators and the
    dashboard see the same plain-English name for each factor without
    duplicating the mapping.
    """
    factor_name: str
    label: str
    description: str
    weight: float


class WeightsMethodEntry(BaseModel):
    """All factors + weights that apply to one collection method."""
    collection_method: CollectionMethod
    method_label: str
    factors: list[WeightsFactorEntry]
    total_weight: float


class WeightsResponse(BaseModel):
    """Grouped view: one entry per collection method the tenant uses.

    Only methods where the tenant has scored at least one collection OR
    saved custom weights appear here. A payroll-only lender receives one
    entry; a lender running card + debit_order receives two.
    """
    methods: list[WeightsMethodEntry]


class WeightsUpdateRequest(BaseModel):
    """PUT payload — updates weights for ONE method only.

    Cross-method isolation: a PUT that tunes CARD leaves the tenant's
    PAYROLL weights untouched. Every factor in `weights` must belong to
    the method's bundle; unknown names are rejected with 400. Weights
    must sum to 1.0 (±0.01 tolerance).
    """
    collection_method: CollectionMethod
    weights: dict[str, float] = Field(min_length=1)


class WeightsAddMethodRequest(BaseModel):
    """POST payload — opt into weight configuration for a new method.

    Seeds default weights for the method so the dashboard shows a tab
    for it before the tenant has scored their first collection with
    that method. Idempotent: calling it for a method that already has
    weights is a no-op that still returns the current state.
    """
    collection_method: CollectionMethod
