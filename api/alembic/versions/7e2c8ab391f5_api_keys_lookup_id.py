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
exists at migration time, the destructive step is gated by
`FORCE_DESTRUCTIVE_UPGRADE=1` — same pattern as the destructive
downgrade guard in `52f6a4d1b0c9`.

After running: re-seed with `python -m app.seed --reseed` (dev) or
re-mint each tenant's key via the dashboard (prod).
"""
import os
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7e2c8ab391f5"
down_revision: Union[str, None] = "52f6a4d1b0c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # Guard: refuse to wipe api_keys rows unless the operator has
    # explicitly acknowledged the destruction. Empty CI DBs pass
    # through untouched.
    active_keys = bind.execute(
        sa.text("SELECT count(*) FROM api_keys WHERE is_active = true")
    ).scalar_one()
    if active_keys > 0 and os.environ.get("FORCE_DESTRUCTIVE_UPGRADE") != "1":
        raise RuntimeError(
            f"Refusing to upgrade: {active_keys} active api_keys row(s) "
            "would be wiped (existing keys cannot be migrated to the new "
            "schema because bcrypt hashes are one-way). Set "
            "FORCE_DESTRUCTIVE_UPGRADE=1 in the environment to acknowledge, "
            "and re-mint each tenant's key after the migration."
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
    bind = op.get_bind()

    # Same destruction guard as upgrade — downgrading here loses every
    # key that was minted post-upgrade (the old shape can't hold the
    # new lookup_id + full key structure).
    active_keys = bind.execute(
        sa.text("SELECT count(*) FROM api_keys WHERE is_active = true")
    ).scalar_one()
    if active_keys > 0 and os.environ.get("FORCE_DESTRUCTIVE_DOWNGRADE") != "1":
        raise RuntimeError(
            f"Refusing to downgrade: {active_keys} active api_keys row(s) "
            "would be wiped (the pre-migration schema cannot represent "
            "new-format keys). Set FORCE_DESTRUCTIVE_DOWNGRADE=1 to "
            "acknowledge, and re-mint each tenant's key after."
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
