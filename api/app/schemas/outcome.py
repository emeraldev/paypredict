from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class OutcomeRequest(BaseModel):
    """Request body for POST /v1/outcomes."""

    score_id: UUID | None = None
    external_collection_id: str
    outcome: str = Field(pattern="^(SUCCESS|FAILED)$")
    failure_reason: str | None = None
    amount_collected: Decimal | None = None
    attempted_at: datetime


class OutcomeResponse(BaseModel):
    """Response body for POST /v1/outcomes."""

    outcome_id: UUID
    linked_score_id: UUID | None = None
    received_at: datetime
