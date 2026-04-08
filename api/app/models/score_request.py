import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class CollectionCurrency(str, enum.Enum):
    ZAR = "ZAR"
    ZMW = "ZMW"


class CollectionMethod(str, enum.Enum):
    CARD = "CARD"
    DEBIT_ORDER = "DEBIT_ORDER"
    MOBILE_MONEY = "MOBILE_MONEY"


class ScoreRequest(Base):
    __tablename__ = "score_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    external_customer_id: Mapped[str] = mapped_column(String(255), nullable=False)
    external_collection_id: Mapped[str] = mapped_column(String(255), nullable=False)
    collection_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    collection_currency: Mapped[CollectionCurrency] = mapped_column(
        Enum(CollectionCurrency, name="collection_currency_enum"), nullable=False
    )
    collection_due_date: Mapped[date] = mapped_column(Date, nullable=False)
    collection_method: Mapped[CollectionMethod] = mapped_column(
        Enum(CollectionMethod, name="collection_method_enum"), nullable=False
    )
    request_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(back_populates="score_requests")  # noqa: F821
    score_result: Mapped["ScoreResult | None"] = relationship(back_populates="score_request")  # noqa: F821

    __table_args__ = (
        Index("ix_score_requests_tenant_created", "tenant_id", "created_at"),
        Index("ix_score_requests_tenant_customer", "tenant_id", "external_customer_id"),
        Index("ix_score_requests_tenant_collection", "tenant_id", "external_collection_id"),
    )
