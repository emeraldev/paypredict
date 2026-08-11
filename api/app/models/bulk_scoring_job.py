"""Postgres source of truth for async bulk-scoring job state.

Async bulk scoring used to keep every piece of job state in Redis
(status / total / completed / results / error, all TTL'd). Redis being
down at the exact moment `on_failure` fired meant the failure record
couldn't be written, and the polling client saw eternal `processing`
until the 1h TTL. Moving state to Postgres removes that failure mode:
even if Redis is dead, terminal transitions still land somewhere the
customer can observe.

Redis is no longer used for job state at all. If we ever want fast
progress polling without hitting Postgres per request, we can layer a
cache on top later — but the truth lives here.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class BulkScoringJobStatus(str, enum.Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class BulkScoringJob(Base):
    __tablename__ = "bulk_scoring_jobs"

    # `id` is our internal PK; `job_id` is the external identifier the
    # POST /v1/score/bulk response returns and the GET polling endpoint
    # accepts. Both are UUIDs and, in practice, could collapse into one
    # column, but keeping them distinct means we control the primary
    # key completely (row id used for FK targets later, e.g. per-item
    # detail rows) and the external identifier stays stable if we ever
    # rewrite storage.
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    status: Mapped[BulkScoringJobStatus] = mapped_column(
        # `values_callable` makes SQLAlchemy send the enum VALUE
        # ("processing") to Postgres instead of the enum NAME
        # ("PROCESSING") — matches the enum type declared by the
        # migration.
        Enum(
            BulkScoringJobStatus,
            name="bulk_scoring_job_status_enum",
            values_callable=lambda cls: [e.value for e in cls],
        ),
        nullable=False,
        default=BulkScoringJobStatus.PROCESSING,
    )
    total_items: Mapped[int] = mapped_column(Integer, nullable=False)
    completed_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Populated on terminal transitions only. `summary` + `results` on
    # completion; `error` on failure. Nullable so the row exists during
    # `processing`.
    summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    results: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        # Structural cross-tenant guarantee for polling: the endpoint
        # looks up `(tenant_id, job_id)` — a caller cannot construct a
        # key that matches another tenant's job. Same shape as the
        # Redis namespacing PR #35 landed for the old design.
        UniqueConstraint(
            "tenant_id", "job_id", name="uq_bulk_scoring_jobs_tenant_job"
        ),
        # Support the polling lookup with a single index.
        Index("ix_bulk_scoring_jobs_tenant_job", "tenant_id", "job_id"),
    )
