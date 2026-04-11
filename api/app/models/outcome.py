import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class OutcomeStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PENDING = "PENDING"


class FailureCategory(str, enum.Enum):
    SOFT_DECLINE = "SOFT_DECLINE"
    HARD_DECLINE = "HARD_DECLINE"
    TECHNICAL = "TECHNICAL"


class Outcome(Base):
    __tablename__ = "outcomes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    score_result_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("score_results.id"), unique=True, nullable=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    external_collection_id: Mapped[str] = mapped_column(String(255), nullable=False)
    outcome: Mapped[OutcomeStatus] = mapped_column(
        Enum(OutcomeStatus, name="outcome_status_enum"), nullable=False
    )
    failure_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    failure_category: Mapped[FailureCategory | None] = mapped_column(
        Enum(FailureCategory, name="failure_category_enum"), nullable=True
    )
    amount_collected: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    score_result: Mapped["ScoreResult | None"] = relationship(back_populates="outcome")  # noqa: F821

    __table_args__ = (
        Index("ix_outcomes_tenant_reported", "tenant_id", "reported_at"),
        Index("ix_outcomes_score_result", "score_result_id"),
        Index("ix_outcomes_tenant_outcome", "tenant_id", "outcome"),
        # Composite for outcomes list + analytics (filter by tenant + outcome,
        # ordered by created_at DESC)
        Index(
            "ix_outcomes_tenant_outcome_created",
            "tenant_id",
            "outcome",
            "created_at",
        ),
    )
