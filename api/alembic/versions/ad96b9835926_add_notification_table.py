"""add_notification_table

Notification table for the bell dropdown — separate from the existing
Alert table. Both coexist: Alert handles threshold evaluation + webhook
delivery, Notification handles the dashboard UI bell + dropdown.

Revision ID: ad96b9835926
Revises: 66d275afe3ed
Create Date: 2026-04-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "ad96b9835926"
down_revision: Union[str, None] = "66d275afe3ed"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column(
            "category",
            sa.Enum("SYSTEM", "ACTIVITY", name="notification_category_enum"),
            nullable=False,
        ),
        sa.Column(
            "severity",
            sa.Enum("CRITICAL", "WARNING", "INFO", name="notification_severity_enum"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.String(length=1024), nullable=False),
        sa.Column("link_to", sa.String(length=512), nullable=True),
        sa.Column("link_label", sa.String(length=255), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_by", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["read_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_notifications_tenant_unread",
        "notifications",
        ["tenant_id", "is_read", "created_at"],
    )
    op.create_index(
        "ix_notifications_tenant_category",
        "notifications",
        ["tenant_id", "category", "created_at"],
    )
    op.create_index(
        "ix_notifications_tenant_created",
        "notifications",
        ["tenant_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_tenant_created", table_name="notifications")
    op.drop_index("ix_notifications_tenant_category", table_name="notifications")
    op.drop_index("ix_notifications_tenant_unread", table_name="notifications")
    op.drop_table("notifications")
    sa.Enum(name="notification_category_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="notification_severity_enum").drop(op.get_bind(), checkfirst=True)
