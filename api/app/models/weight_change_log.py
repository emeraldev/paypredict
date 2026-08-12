"""Append-only audit log for factor-weight changes.

Every mutation of `factor_weights` writes one row here per (method,
factor) pair that changed: old value, new value, actor, timestamp.
Answers the compliance question "who changed CardHealth on 2026-08-01
and from what to what?" — the `factor_weights` table itself is
upsert-in-place and loses that history.

Design notes:
- Append-only. No updates, no deletes. The dashboard reads it; the
  weights service writes to it inside the same DB transaction as the
  actual weight mutation so the log and the state can never diverge.
- `actor_id` is stored WITHOUT a FK. Users can be removed from a
  tenant later; keeping the log intact matters more than referential
  integrity here. `actor_name` is denormalized on write so the entry
  stays readable even after the user record is gone.
- `old_weight` is null when a factor row is created (first tune of a
  new method, or the "+ Add method" affordance seeding defaults).
  `new_weight` is null when a factor row is deleted (stale cleanup
  during upsert if a factor is removed from the bundle).
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class WeightChangeActorType(str, enum.Enum):
    USER = "user"
    API_KEY = "api_key"
    SYSTEM = "system"


class WeightChangeLog(Base):
    __tablename__ = "weight_change_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    collection_method: Mapped[str] = mapped_column(String(50), nullable=False)
    factor_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Nullable to represent create (old=None) and delete (new=None).
    # Both non-null is the ordinary update case.
    old_weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    new_weight: Mapped[float | None] = mapped_column(Float, nullable=True)

    actor_type: Mapped[WeightChangeActorType] = mapped_column(
        Enum(
            WeightChangeActorType,
            name="weight_change_actor_type_enum",
            values_callable=lambda cls: [e.value for e in cls],
        ),
        nullable=False,
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    actor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Freeform tag for future filtering ("upsert", "add_method",
    # "stale_cleanup", "backfill_migration"). Not user-facing today.
    context: Mapped[str | None] = mapped_column(String(50), nullable=True)

    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        # Primary read pattern: dashboard fetches most-recent-first per tenant.
        Index(
            "ix_weight_change_log_tenant_changed_at",
            "tenant_id",
            "changed_at",
        ),
    )
