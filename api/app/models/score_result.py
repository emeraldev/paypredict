import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ScoreResult(Base):
    __tablename__ = "score_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    score_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("score_requests.id"), unique=True, nullable=False
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel, name="risk_level_enum"), nullable=False
    )
    factors: Mapped[dict] = mapped_column(JSONB, nullable=False)
    recommended_action: Mapped[str] = mapped_column(String(255), nullable=False)
    recommended_collection_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    scoring_duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    score_request: Mapped["ScoreRequest"] = relationship(back_populates="score_result")  # noqa: F821
    outcome: Mapped["Outcome | None"] = relationship(back_populates="score_result")  # noqa: F821

    __table_args__ = (
        Index("ix_score_results_tenant_created", "tenant_id", "created_at"),
        Index("ix_score_results_tenant_risk", "tenant_id", "risk_level"),
    )
