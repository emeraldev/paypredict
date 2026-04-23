import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class BacktestStatus(str, enum.Enum):
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[BacktestStatus] = mapped_column(
        Enum(BacktestStatus, name="backtest_status_enum"),
        default=BacktestStatus.PROCESSING,
        nullable=False,
    )
    total_collections: Mapped[int] = mapped_column(Integer, nullable=False)
    factor_set_used: Mapped[str] = mapped_column(String(50), nullable=False)
    weights_used: Mapped[dict] = mapped_column(JSONB, nullable=False)
    summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    confusion_matrix: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    top_failure_factors: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    items: Mapped[list["BacktestItem"]] = relationship(
        back_populates="backtest_run", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_backtest_runs_tenant_created", "tenant_id", "created_at"),
    )


class BacktestItem(Base):
    __tablename__ = "backtest_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    backtest_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("backtest_runs.id"), nullable=False
    )
    external_customer_id: Mapped[str] = mapped_column(String(255), nullable=False)
    external_collection_id: Mapped[str] = mapped_column(String(255), nullable=False)
    collection_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    collection_method: Mapped[str] = mapped_column(String(50), nullable=False)
    predicted_score: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_risk_level: Mapped[str] = mapped_column(String(10), nullable=False)
    actual_outcome: Mapped[str] = mapped_column(String(10), nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    factors: Mapped[dict] = mapped_column(JSONB, nullable=False)
    prediction_matched: Mapped[bool] = mapped_column(Boolean, nullable=False)

    # Relationships
    backtest_run: Mapped["BacktestRun"] = relationship(back_populates="items")

    __table_args__ = (
        Index("ix_backtest_items_run_id", "backtest_run_id"),
    )
