"""Pydantic schemas for the dashboard outcomes list endpoint."""
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.services.query_utils import PaginationMeta


class OutcomeListItem(BaseModel):
    outcome_id: UUID
    external_collection_id: str
    score: float | None = None
    risk_level: str | None = None
    outcome: str
    failure_reason: str | None = None
    collection_amount: Decimal | None = None
    collection_currency: str | None = None
    collection_method: str | None = None
    attempted_at: datetime
    reported_at: datetime
    prediction_matched: bool | None = None


class OutcomeListStats(BaseModel):
    """Aggregate stats over the full filtered dataset."""
    total_outcomes: int
    success_count: int
    failed_count: int
    success_rate: float
    predictions_matched: int
    match_rate: float


class OutcomesListResponse(BaseModel):
    items: list[OutcomeListItem]
    pagination: PaginationMeta
    stats: OutcomeListStats
