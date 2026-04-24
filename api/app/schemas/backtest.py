"""Pydantic schemas for backtest endpoints."""
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


# ---- Request ----

class BacktestCustomerData(BaseModel):
    """Subset of customer data fields accepted in backtest input."""
    total_payments: int = 0
    successful_payments: int = 0
    last_successful_payment_date: date | None = None
    average_collection_amount: Decimal | None = None
    instalment_number: int | None = None
    total_instalments: int | None = None
    card_type: str | None = None
    card_expiry_date: date | None = None
    last_decline_code: str | None = None
    debit_order_returns: list[str] = Field(default_factory=list)
    known_salary_day: int | None = Field(default=None, ge=1, le=31)
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


class BacktestCollectionInput(BaseModel):
    external_customer_id: str
    external_collection_id: str
    collection_amount: Decimal = Field(gt=0)
    collection_currency: str = Field(pattern="^(ZAR|ZMW)$")
    collection_date: date
    collection_method: str = Field(pattern="^(CARD|DEBIT_ORDER|MOBILE_MONEY)$")
    customer_data: BacktestCustomerData = Field(default_factory=BacktestCustomerData)
    actual_outcome: str = Field(pattern="^(SUCCESS|FAILED)$")
    failure_reason: str | None = None


class BacktestRequest(BaseModel):
    name: str | None = None
    collections: list[BacktestCollectionInput] = Field(min_length=1, max_length=500)


# ---- Response ----

class BacktestRiskBucket(BaseModel):
    count: int
    actually_failed: int
    accuracy: float


class BacktestSummary(BaseModel):
    overall_accuracy: float
    collection_rate_actual: float
    collection_rate_if_acted: float
    estimated_annual_recovery: float
    total_failed_value: float
    flagged_in_advance_value: float


class BacktestFactorContribution(BaseModel):
    factor: str
    avg_score_in_failures: float
    contribution: float


class BacktestConfusionMatrix(BaseModel):
    predicted_high_actual_failed: int
    predicted_high_actual_success: int
    predicted_medium_actual_failed: int
    predicted_medium_actual_success: int
    predicted_low_actual_failed: int
    predicted_low_actual_success: int


class BacktestResultItem(BaseModel):
    external_customer_id: str
    external_collection_id: str
    collection_amount: float
    collection_method: str
    predicted_score: float
    predicted_risk_level: str
    actual_outcome: str
    failure_reason: str | None
    prediction_matched: bool


class BacktestResponse(BaseModel):
    backtest_id: UUID
    name: str | None
    total_collections: int
    status: str
    started_at: datetime
    completed_at: datetime | None
    summary: BacktestSummary | None
    risk_distribution: dict[str, BacktestRiskBucket] | None
    top_failure_factors: list[BacktestFactorContribution] | None
    confusion_matrix: BacktestConfusionMatrix | None


class BacktestListItem(BaseModel):
    backtest_id: UUID
    name: str | None
    total_collections: int
    status: str
    overall_accuracy: float | None
    created_at: datetime


class BacktestListResponse(BaseModel):
    items: list[BacktestListItem]


class CsvValidationError(BaseModel):
    row: int
    field: str
    message: str


class CsvUploadResponse(BaseModel):
    """Returned when CSV has validation errors."""
    errors: list[CsvValidationError]
