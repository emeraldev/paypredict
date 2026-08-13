from datetime import date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from app.schemas._validators import validate_opaque_id


# Reused across every lender-facing schema that carries an id string.
# Rejects PII shapes (emails, whitespace, formatted phone numbers) at
# the boundary. See `_validators.py` for the rule + rationale.
OpaqueId = Annotated[str, AfterValidator(validate_opaque_id)]


class CustomerData(BaseModel):
    """Customer data provided by the lender for scoring."""

    # extra="forbid" — silent-drop is worse than a loud reject. An
    # integrator sending `{"phone": "..."}` or `{"email": "..."}`
    # thinking it helps the model needs to get 422 telling them the
    # field isn't expected AND that we don't want PII on the boundary.
    model_config = ConfigDict(extra="forbid")

    # Common fields (all markets)
    total_payments: int = 0
    successful_payments: int = 0
    last_successful_payment_date: date | None = None
    average_collection_amount: Decimal | None = None
    instalment_number: int | None = None
    total_instalments: int | None = None

    # SA card-based fields. String fields are enum-shaped (`card_type`
    # in `credit`/`debit`, `regular_inflow_day` in `monday`..`friday`,
    # etc.) — max_length is generous but rules out paragraphs where a
    # name / address / free-form PII could hide.
    card_type: str | None = Field(default=None, max_length=32)
    card_expiry_date: date | None = None
    last_decline_code: str | None = Field(default=None, max_length=64)
    debit_order_returns: list[str] = Field(default_factory=list)
    known_salary_day: int | None = Field(default=None, ge=1, le=31)

    # Zambia mobile money fields
    wallet_balance_7d_avg: Decimal | None = None
    wallet_balance_current: Decimal | None = None
    hours_since_last_inflow: int | None = None
    regular_inflow_day: str | None = Field(default=None, max_length=32)
    active_loan_count: int | None = None
    transactions_last_7d: int | None = None
    transactions_avg_7d: int | None = None
    last_airtime_purchase_days_ago: int | None = None
    new_loan_within_repayment_period: bool | None = None
    loans_taken_last_90d: int | None = None

    # Payroll deduction fields (used when collection_method == PAYROLL —
    # salary-advance lenders whose collections go through payroll systems)
    gross_salary: Decimal | None = None
    net_pay: Decimal | None = None
    current_total_deductions: Decimal | None = None
    deduction_threshold_pct: float | None = None
    resubmission_count: int | None = None
    borrower_segment: str | None = Field(default=None, max_length=32)


class ScoreRequest(BaseModel):
    """Request body for POST /v1/score."""

    # extra="forbid" catches unknown keys at the request root too
    # (e.g. `{"borrower_name": "..."}` sitting alongside customer_data).
    model_config = ConfigDict(extra="forbid")

    customer_id: OpaqueId
    collection_id: OpaqueId
    collection_amount: Decimal = Field(gt=0)
    collection_currency: str = Field(pattern="^(ZAR|ZMW)$")
    collection_due_date: date
    collection_method: str = Field(pattern="^(CARD|DEBIT_ORDER|MOBILE_MONEY|PAYROLL)$")
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
    # Both fields are populated together by the timing optimiser when
    # `recommended_action == "shift_date"`; otherwise both are None.
    recommended_score: float | None = None
    score_improvement: float | None = None
    factors: list[FactorBreakdown]
    skipped_factors: list[str] = Field(default_factory=list)
    model_version: str
    scored_at: datetime
    scoring_duration_ms: int
