"""Pydantic schemas for bulk scoring endpoints."""
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.score import CustomerData


class BulkScoreItem(BaseModel):
    external_customer_id: str
    external_collection_id: str
    collection_amount: Decimal = Field(gt=0)
    collection_currency: str = Field(pattern="^(ZAR|ZMW)$")
    collection_due_date: date
    collection_method: str = Field(pattern="^(CARD|DEBIT_ORDER|MOBILE_MONEY)$")
    customer_data: CustomerData = Field(default_factory=CustomerData)


class BulkScoreRequest(BaseModel):
    collections: list[BulkScoreItem] = Field(min_length=1, max_length=1000)
