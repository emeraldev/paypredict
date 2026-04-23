import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, String
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Market(str, enum.Enum):
    SA = "SA"
    ZM = "ZM"


class FactorSet(str, enum.Enum):
    CARD_DEBIT = "CARD_DEBIT"          # Card-on-file + debit order collections
    MOBILE_WALLET = "MOBILE_WALLET"    # Mobile money wallet auto-deductions
    CUSTOM = "CUSTOM"                  # Future: tenant-defined factor mix


class Plan(str, enum.Enum):
    PILOT = "PILOT"
    STARTER = "STARTER"
    GROWTH = "GROWTH"
    SCALE = "SCALE"


class EmailDigest(str, enum.Enum):
    OFF = "OFF"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    market: Mapped[Market] = mapped_column(Enum(Market, name="market_enum"), nullable=False)
    factor_set: Mapped[FactorSet] = mapped_column(
        Enum(FactorSet, name="factor_set_enum"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    plan: Mapped[Plan] = mapped_column(
        Enum(Plan, name="plan_enum"), default=Plan.PILOT, nullable=False
    )
    webhook_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    slack_webhook_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    alert_threshold: Mapped[float] = mapped_column(Float, default=0.20, nullable=False)
    email_digest: Mapped[EmailDigest] = mapped_column(
        Enum(EmailDigest, name="email_digest_enum"),
        default=EmailDigest.OFF,
        nullable=False,
    )
    email_recipients: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    api_keys: Mapped[list["ApiKey"]] = relationship(back_populates="tenant")  # noqa: F821
    factor_weights: Mapped[list["FactorWeight"]] = relationship(back_populates="tenant")  # noqa: F821
    score_requests: Mapped[list["ScoreRequest"]] = relationship(back_populates="tenant")  # noqa: F821
    users: Mapped[list["User"]] = relationship(back_populates="tenant")  # noqa: F821
    alerts: Mapped[list["Alert"]] = relationship(back_populates="tenant")  # noqa: F821
