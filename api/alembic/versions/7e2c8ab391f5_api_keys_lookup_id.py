"""api_keys: add lookup_id, widen key_prefix, remove degenerate prefix index

Revision ID: 7e2c8ab391f5
Revises: 52f6a4d1b0c9
Create Date: 2026-08-10 08:00:00.000000

Fixes the bcrypt-DoS class of bug in the API-key auth path. The old
schema stored `key_prefix = raw_key[:8]`, which for keys minted with
"pk_live_" or "pk_test_" was ALWAYS the literal 8-char environment
prefix — a degenerate lookup that fanned out to every active key on
the platform per request, then bcrypt-checked each. See PR audit
finding H2.

New shape:
  - `lookup_id`         12-hex-char, UNIQUE, indexed — the fast lookup
                        key the auth path uses. Public (part of the
                        key string given to the customer).
  - `key_prefix`        widened to 32 chars, holds a display-only
                        string like `pk_live_a1b2c3d4e5f6`.
  - `key_hash`          unchanged — bcrypt of the FULL raw key
                        (env prefix + lookup_id + separator + secret).

DESTRUCTIVE: existing api_keys rows have no `lookup_id` and cannot be
recovered from bcrypt(). This migration DELETEs all rows. Pre-customer
that's exactly zero customer keys — verified by
`SELECT count(*) FROM api_keys WHERE is_active=true` at PR time (4 rows,
all seed defaults, last_used_at NULL). If a real customer key ever
exists at migration time, `require_upgrade_ack` (see
`app/migration_guards.py`) refuses unless the operator names this
revision in `FORCE_DESTRUCTIVE_UPGRADE`.

After running: re-seed with `python -m app.seed --reseed` (dev) or
re-mint each tenant's key via the dashboard (prod).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.migration_guards import require_downgrade_ack, require_upgrade_ack


revision: str = "7e2c8ab391f5"
down_revision: Union[str, None] = "52f6a4d1b0c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    require_upgrade_ack(
        revision=revision,
        at_risk_count=lambda bind: bind.execute(
            sa.text("SELECT count(*) FROM api_keys WHERE is_active = true")
        ).scalar_one(),
        description=(
            "Existing api_keys rows can't be migrated to the new "
            "lookup_id + secret format — bcrypt hashes are one-way, so "
            "the pre-migration keys must be re-minted after this "
            "upgrade. Every customer's current API key stops working."
        ),
    )

    # Wipe existing rows — they don't fit the new schema.
    op.execute("DELETE FROM api_keys")

    # Drop the legacy index; the old key_prefix was too coarse to be
    # useful as a lookup key and the new schema replaces it entirely.
    op.drop_index("ix_api_keys_key_prefix", table_name="api_keys")

    # New columns.
    op.add_column(
        "api_keys",
        sa.Column("lookup_id", sa.String(length=32), nullable=False),
    )
    op.create_unique_constraint(
        "uq_api_keys_lookup_id", "api_keys", ["lookup_id"]
    )
    op.create_index(
        "ix_api_keys_lookup_id", "api_keys", ["lookup_id"], unique=True
    )

    # Widen key_prefix from 16 → 32 so it can hold the display form
    # `pk_live_<12-hex>` (20 chars) plus room for future changes.
    op.alter_column(
        "api_keys",
        "key_prefix",
        existing_type=sa.String(length=16),
        type_=sa.String(length=32),
        existing_nullable=False,
    )


def downgrade() -> None:
    require_downgrade_ack(
        revision=revision,
        at_risk_count=lambda bind: bind.execute(
            sa.text("SELECT count(*) FROM api_keys WHERE is_active = true")
        ).scalar_one(),
        description=(
            "New-format api_keys can't be represented by the old schema "
            "(no lookup_id column). These rows will be deleted and each "
            "tenant will need to re-mint their key after."
        ),
    )

    op.execute("DELETE FROM api_keys")

    op.drop_index("ix_api_keys_lookup_id", table_name="api_keys")
    op.drop_constraint("uq_api_keys_lookup_id", "api_keys", type_="unique")
    op.drop_column("api_keys", "lookup_id")

    op.alter_column(
        "api_keys",
        "key_prefix",
        existing_type=sa.String(length=32),
        type_=sa.String(length=16),
        existing_nullable=False,
    )
    op.create_index("ix_api_keys_key_prefix", "api_keys", ["key_prefix"])
