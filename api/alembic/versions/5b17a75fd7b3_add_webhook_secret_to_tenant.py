"""add_webhook_secret_to_tenant

Per-tenant webhook signing secret. Replaces the hardcoded shared
"paypredict" secret used for outgoing webhook HMAC signatures.

The secret is auto-generated for each tenant. Customers can read it
from GET /v1/config/alerts to verify webhook signatures on their end,
and rotate it via POST /v1/config/alerts/regenerate-secret.

Revision ID: 5b17a75fd7b3
Revises: ad96b9835926
Create Date: 2026-05-09 00:00:00.000000

Rollback semantics: down + up preserves the ORIGINAL secret per
tenant, so customers who cached the value from GET /v1/config/alerts
retain a working HMAC key across an emergency rollback + redeploy.
The downgrade stashes secrets into `_preserved_webhook_secrets`; the
upgrade backfill reads that table before falling back to minting.
"""
import secrets
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "5b17a75fd7b3"
down_revision: Union[str, None] = "ad96b9835926"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_PRESERVATION_TABLE = "_preserved_webhook_secrets"


def upgrade() -> None:
    # 1. Add column nullable first so the migration doesn't fail on existing rows
    op.add_column(
        "tenants",
        sa.Column("webhook_secret", sa.String(length=255), nullable=True),
    )

    bind = op.get_bind()

    # 2a. If a previous downgrade stashed original secrets, restore
    #     those first — a rollback + re-upgrade must not silently
    #     invalidate every customer's cached HMAC verification key.
    #     The table is created only by our downgrade, so `to_regclass`
    #     tells us whether the preservation ever happened.
    preservation_exists = bind.execute(
        sa.text(f"SELECT to_regclass('{_PRESERVATION_TABLE}')")
    ).scalar_one() is not None

    if preservation_exists:
        bind.execute(
            sa.text(
                f"UPDATE tenants t "
                f"SET webhook_secret = p.webhook_secret "
                f"FROM {_PRESERVATION_TABLE} p "
                f"WHERE t.id = p.tenant_id AND t.webhook_secret IS NULL"
            )
        )
        # Drop the preservation table so a second down+up cycle would
        # not restore stale secrets (only the most-recent rollback's
        # values are valid).
        op.execute(f"DROP TABLE {_PRESERVATION_TABLE}")

    # 2b. Backfill any tenant still without a secret (fresh installs,
    #     or tenants added between the downgrade and this re-upgrade).
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
    # Stash current secrets before dropping the column so a subsequent
    # re-upgrade can restore them. Without this, down + up mints fresh
    # secrets and every customer's cached HMAC key stops working
    # silently — the failure surfaces only on their side as "webhook
    # signature verification failed", with no signal to us.
    op.execute(
        f"CREATE TABLE IF NOT EXISTS {_PRESERVATION_TABLE} AS "
        f"SELECT id AS tenant_id, webhook_secret "
        f"FROM tenants WHERE webhook_secret IS NOT NULL"
    )
    op.drop_column("tenants", "webhook_secret")
