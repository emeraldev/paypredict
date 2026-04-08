from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class CustomerData(BaseModel):
    """Customer data provided by the lender for scoring."""

    # Common fields (all markets)
    total_payments: int = 0
    successful_payments: int = 0
    last_successful_payment_date: date | None = None
    average_collection_amount: Decimal | None = None
    instalment_number: int | None = None
    total_instalments: int | None = None

    # SA card-based fields
    card_type: str | None = None
    card_expiry_date: date | None = None
    last_decline_code: str | None = None
    debit_order_returns: list[str] = Field(default_factory=list)
    known_salary_day: int | None = Field(default=None, ge=1, le=31)

    # Zambia mobile money fields
    wallet_balance_7d_avg: Decimal | None = None
    wallet_balance_current: Decimal | None = None
    hours_since_last_inflow: int | None = None
    regular_inflow_day: str | None = None
    active_loan_count: int | None = None
    transactions_last_7d: int | None = None
    transactions_avg_7d: int | None = None
    last_airtime_purchase_days_ago: int | None = None
    new_loan_within_repayment_period: bool | None = None
    loans_taken_last_90d: int | None = None


class ScoreRequest(BaseModel):
    """Request body for POST /v1/score."""

    external_customer_id: str
    external_collection_id: str
    collection_amount: Decimal = Field(gt=0)
    collection_currency: str = Field(pattern="^(ZAR|ZMW)$")
    collection_due_date: date
    collection_method: str = Field(pattern="^(CARD|DEBIT_ORDER|MOBILE_MONEY)$")
    customer_data: CustomerData = Field(default_factory=CustomerData)


class FactorBreakdown(BaseModel):
    """Individual factor result in score response."""

    factor: str
    raw_score: float
    weight: float
    weighted_score: float
    explanation: str


class ScoreResponse(BaseModel):
    """Response body for POST /v1/score."""

    score_id: UUID
    score: float
    risk_level: str
    recommended_action: str
    recommended_collection_date: date | None = None
    factors: list[FactorBreakdown]
    model_version: str
    scored_at: datetime
    scoring_duration_ms: int
