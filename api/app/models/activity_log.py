"""Append-only audit trail for tenant-wide mutations other than weights.

Weight-tuning has its own dedicated `weight_change_log` (per-factor
value diffs). This table covers everything else that would show up on
a compliance auditor's checklist:

- Team members (invite / role change / remove)
- API keys (create / activate / deactivate / revoke)
- Alert config (per-field diff of threshold, webhook, recipients)
- Webhook secret rotation
- Outcome soft-deletion (a clerk erasing a labelled row from the ML
  training set is exactly the kind of destructive edit an auditor
  wants to be able to trace)

Design mirrors `weight_change_log`:
- Append-only. No updates, no deletes.
- Every write happens in the same DB transaction as the mutation, so
  state and audit can never diverge.
- `actor_id` has NO FK — keeping the log intact after a user is later
  removed matters more than referential integrity. `actor_name` is
  denormalized on write so the row stays readable even after the user
  record is gone.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class ActivityActorType(str, enum.Enum):
    USER = "user"
    API_KEY = "api_key"
    SYSTEM = "system"


class ActivityLog(Base):
    __tablename__ = "activity_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )

    # Free-form entity classifier so new event types can land without
    # a migration. Current values: `user`, `api_key`, `alert_config`,
    # `webhook_secret`, `outcome`.
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # Target entity's PK when there is one (`user.id`, `api_key.id`,
    # `outcome.id`). Null for tenant-wide events like alert-config
    # updates or webhook-secret rotation.
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # Current values: `create`, `update`, `delete`, `revoke`,
    # `activate`, `deactivate`, `rotate`. Same free-form String
    # rationale as entity_type.
    action: Mapped[str] = mapped_column(String(50), nullable=False)

    # Pre/post-mutation snapshots. `before` is null on create;
    # `after` is null on delete. Both non-null is the ordinary update.
    # Kept as small dicts of the fields that meaningfully changed —
    # never dumps of full ORM rows.
    before: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    after: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    actor_type: Mapped[ActivityActorType] = mapped_column(
        Enum(
            ActivityActorType,
            name="activity_actor_type_enum",
            values_callable=lambda cls: [e.value for e in cls],
        ),
        nullable=False,
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    actor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    context: Mapped[str | None] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        # Dashboard reads most-recent-first per tenant.
        Index(
            "ix_activity_log_tenant_created_at",
            "tenant_id",
            "created_at",
        ),
    )
