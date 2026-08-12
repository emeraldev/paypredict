"""activity_log table + outcomes soft-delete columns

Revision ID: f3b7d92a1c8e
Revises: d4e8c1f95a72
Create Date: 2026-08-13 09:00:00.000000

Extends the compliance audit layer beyond weight changes:

1. `activity_log` — generic append-only trail for team, api_keys,
   alert_config, webhook_secret rotation, and outcome soft-deletes.
   Complements `weight_change_log` (which stays dedicated to
   per-factor value diffs). Every mutation site in these areas
   emits one entry in the same DB transaction as the underlying
   change so state and audit can never diverge.

2. `outcomes.deleted_at` + `outcomes.deleted_by` — soft-delete
   columns. `DELETE /v1/outcomes/{id}` now flips these instead of
   dropping the row; all outcome read paths filter
   `WHERE deleted_at IS NULL`. Preserves the labelled ML training
   dataset when a clerk corrects a mistaken entry.

Downgrade IS destructive: drops the audit log AND the soft-delete
columns (any outcomes that were soft-deleted after this revision
reappear in reads after downgrade, which is confusing but not
data-loss). Guarded via `require_downgrade_ack`.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.migration_guards import require_downgrade_ack


revision: str = "f3b7d92a1c8e"
down_revision: Union[str, None] = "d4e8c1f95a72"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Activity audit table.
    op.create_table(
        "activity_log",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=True),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("before", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("after", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column(
            "actor_type",
            sa.Enum(
                "user",
                "api_key",
                "system",
                name="activity_actor_type_enum",
            ),
            nullable=False,
        ),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("actor_name", sa.String(length=255), nullable=True),
        sa.Column("context", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_activity_log_tenant_created_at",
        "activity_log",
        ["tenant_id", "created_at"],
    )

    # 2. Soft-delete columns on outcomes. Both nullable so pre-existing
    # rows (which weren't deleted) stay valid.
    op.add_column(
        "outcomes",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "outcomes",
        sa.Column("deleted_by", sa.UUID(), nullable=True),
    )

    # 3. Convert the outcomes.score_result_id unique constraint (from
    # the initial migration, enforced as `outcomes_score_result_id_key`)
    # into a partial unique index that only covers live rows. Without
    # this, soft-deleting an outcome would prevent a fresh outcome
    # from re-linking to the same score — a real workflow when a clerk
    # corrects a mistaken entry.
    op.drop_constraint("outcomes_score_result_id_key", "outcomes", type_="unique")
    op.create_index(
        "ix_outcomes_score_result_active",
        "outcomes",
        ["score_result_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    require_downgrade_ack(
        revision=revision,
        at_risk_count=lambda bind: (
            bind.execute(
                sa.text("SELECT count(*) FROM activity_log")
            ).scalar_one()
            + bind.execute(
                sa.text(
                    "SELECT count(*) FROM outcomes WHERE deleted_at IS NOT NULL"
                )
            ).scalar_one()
        ),
        description=(
            "Dropping activity_log wipes every tenant's audit trail for "
            "team / API keys / alerts / webhook-secret rotations / "
            "outcome deletions. Dropping outcomes.deleted_at / deleted_by "
            "causes any soft-deleted outcomes to reappear in list "
            "responses (the rows survive; they just lose the tombstone). "
            "That surprise-resurrection is confusing enough on its own "
            "to warrant explicit consent."
        ),
    )

    # Restore the plain unique constraint on outcomes.score_result_id
    # (the pre-migration state) before dropping the partial index +
    # tombstone columns. Do this BEFORE the drops so any soft-deleted
    # rows that used to hold the same score_result_id would fail the
    # constraint loudly rather than silently corrupt state — but the
    # `at_risk_count` guard already refused if any exist.
    op.drop_index("ix_outcomes_score_result_active", table_name="outcomes")
    op.create_unique_constraint(
        "outcomes_score_result_id_key", "outcomes", ["score_result_id"]
    )
    op.drop_column("outcomes", "deleted_by")
    op.drop_column("outcomes", "deleted_at")
    op.drop_index(
        "ix_activity_log_tenant_created_at", table_name="activity_log"
    )
    op.drop_table("activity_log")
    sa.Enum(name="activity_actor_type_enum").drop(
        op.get_bind(), checkfirst=True
    )
