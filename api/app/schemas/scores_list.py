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
    customer_id: str
    collection_id: str
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
    model_version: str
    scored_at: datetime


class ScoresSummary(BaseModel):
    """Aggregate counts returned alongside every list request, computed
    over the full filtered dataset (not just the current page)."""

    high_risk: int
    medium_risk: int
    low_risk: int
    total_value_at_risk: Decimal
    # Number of collections whose `recommended_action == "shift_date"` —
    # surfaces the timing optimiser's call to action on the dashboard.
    shift_recommended: int = 0


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

    outcome_id: UUID
    outcome: str
    failure_reason: str | None = None
    attempted_at: datetime | None = None


class CustomerJourneyEntry(BaseModel):
    """One prior scoring event for the same (tenant, customer_id).

    Used by the dashboard drawer to render a chronological loan
    timeline so a lender can see this customer's full history in
    one glance. Includes the current score itself (flagged with
    `is_current: True`) so the timeline reads as "you are here"
    against the rest.
    """

    score_id: UUID
    scored_at: datetime
    collection_amount: Decimal
    collection_currency: str
    collection_method: str
    collection_due_date: date
    instalment_number: int | None = None
    total_instalments: int | None = None
    score: float
    risk_level: str
    outcome: str | None = None
    outcome_reported_at: datetime | None = None
    is_current: bool = False


class ScoreDetailResponse(BaseModel):
    score_id: UUID
    customer_id: str
    collection_id: str
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
    recommended_score: float | None = None
    score_improvement: float | None = None
    factors: list[FactorBreakdown]
    skipped_factors: list[str] = []
    model_version: str
    scored_at: datetime
    scoring_duration_ms: int
    customer_context: CustomerContext
    outcome: OutcomeSummary | None = None
    # Chronological timeline of prior scores + outcomes for the same
    # (tenant, external_customer_id). Includes the current row, flagged
    # `is_current=True`. Empty for singleton customers. Capped at 50
    # entries so a pathological loan-book doesn't bloat the response.
    customer_journey: list[CustomerJourneyEntry] = []
