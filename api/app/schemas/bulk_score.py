"""Pydantic schemas for bulk scoring endpoints."""
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.score import CustomerData, OpaqueId


class BulkScoreItem(BaseModel):
    # Match the single-score schema's boundary: unknown keys are a
    # 422, not a silent-drop. Applies per-row inside the batch — one
    # malformed row surfaces its own validation error rather than
    # sinking the whole submission.
    model_config = ConfigDict(extra="forbid")

    customer_id: OpaqueId
    collection_id: OpaqueId
    collection_amount: Decimal = Field(gt=0)
    collection_currency: str = Field(pattern="^(ZAR|ZMW)$")
    collection_due_date: date
    collection_method: str = Field(pattern="^(CARD|DEBIT_ORDER|MOBILE_MONEY|PAYROLL)$")
    customer_data: CustomerData = Field(default_factory=CustomerData)


class BulkScoreRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    collections: list[BulkScoreItem] = Field(min_length=1, max_length=1000)
