"""Pydantic schemas for the dashboard scores list + detail endpoints."""
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.schemas.score import FactorBreakdown
from app.services.query_utils import PaginationMeta


# ---- List item (table row) ----

class ScoreListItem(BaseModel):
    score_id: UUID
    external_customer_id: str
    external_collection_id: str
    collection_amount: Decimal
    collection_currency: str
    collection_due_date: date
    collection_method: str
    instalment_number: int | None = None
    total_instalments: int | None = None
    score: float
    risk_level: str
    recommended_action: str
    model_version: str
    scored_at: datetime


class ScoresSummary(BaseModel):
    """Aggregate counts returned alongside every list request, computed
    over the full filtered dataset (not just the current page)."""

    high_risk: int
    medium_risk: int
    low_risk: int
    total_value_at_risk: Decimal


class ScoresListResponse(BaseModel):
    items: list[ScoreListItem]
    pagination: PaginationMeta
    summary: ScoresSummary


# ---- Detail (drawer) ----

class CustomerContext(BaseModel):
    """Subset of customer_data extracted from the stored request_payload."""

    total_payments: int | None = None
    successful_payments: int | None = None
    success_rate: float | None = None
    days_since_last_payment: int | None = None


class OutcomeSummary(BaseModel):
    """Linked outcome, or null if not yet reported."""

    outcome: str
    failure_reason: str | None = None
    attempted_at: datetime | None = None


class ScoreDetailResponse(BaseModel):
    score_id: UUID
    external_customer_id: str
    external_collection_id: str
    collection_amount: Decimal
    collection_currency: str
    collection_due_date: date
    collection_method: str
    instalment_number: int | None = None
    total_instalments: int | None = None
    score: float
    risk_level: str
    recommended_action: str
    recommended_collection_date: date | None = None
    factors: list[FactorBreakdown]
    skipped_factors: list[str] = []
    model_version: str
    scored_at: datetime
    scoring_duration_ms: int
    customer_context: CustomerContext
    outcome: OutcomeSummary | None = None
