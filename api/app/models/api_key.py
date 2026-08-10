import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    # `lookup_id` is the indexed identifier the auth path uses to find
    # this key in one query. It is public (part of the key string given
    # to the customer) and NOT a secret — the secret is bcrypt-hashed
    # into `key_hash`. Structural cross-tenant safety comes from the
    # UNIQUE constraint: at most one row exists for any lookup_id, so
    # `SELECT ... WHERE lookup_id = ?` cannot fan out.
    lookup_id: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # Display prefix shown in the dashboard's API-keys list (e.g.
    # `pk_live_a1b2c3d4e5f6`). Not used by auth — that's `lookup_id`.
    key_prefix: Mapped[str] = mapped_column(String(32), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(back_populates="api_keys")  # noqa: F821

    __table_args__ = (
        Index("ix_api_keys_tenant_active", "tenant_id", "is_active"),
    )
