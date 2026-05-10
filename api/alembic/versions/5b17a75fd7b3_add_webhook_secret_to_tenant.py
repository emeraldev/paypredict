"""add_webhook_secret_to_tenant

Per-tenant webhook signing secret. Replaces the hardcoded shared
"paypredict" secret used for outgoing webhook HMAC signatures.

The secret is auto-generated for each tenant. Customers can read it
from GET /v1/config/alerts to verify webhook signatures on their end,
and rotate it via POST /v1/config/alerts/regenerate-secret.

Revision ID: 5b17a75fd7b3
Revises: ad96b9835926
Create Date: 2026-05-09 00:00:00.000000

"""
import secrets
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "5b17a75fd7b3"
down_revision: Union[str, None] = "ad96b9835926"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add column nullable first so the migration doesn't fail on existing rows
    op.add_column(
        "tenants",
        sa.Column("webhook_secret", sa.String(length=255), nullable=True),
    )

    # 2. Backfill existing tenants with random secrets
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id FROM tenants WHERE webhook_secret IS NULL"))
    for (tenant_id,) in rows.fetchall():
        new_secret = "whsec_" + secrets.token_urlsafe(32)
        bind.execute(
            sa.text("UPDATE tenants SET webhook_secret = :secret WHERE id = :tid"),
            {"secret": new_secret, "tid": tenant_id},
        )

    # 3. Now make the column NOT NULL
    op.alter_column("tenants", "webhook_secret", nullable=False)


def downgrade() -> None:
    op.drop_column("tenants", "webhook_secret")
