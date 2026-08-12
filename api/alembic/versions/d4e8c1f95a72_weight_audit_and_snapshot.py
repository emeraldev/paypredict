"""weight_change_log table + score_results.weights_snapshot column

Revision ID: d4e8c1f95a72
Revises: c9a7f10e5b28
Create Date: 2026-08-12 09:00:00.000000

Adds the compliance + reproducibility layer for factor weights:

1. `weight_change_log` — append-only audit trail. Every mutation of
   `factor_weights` (PUT /v1/config/weights, POST
   /v1/config/weights/methods, or the future add-method affordance)
   writes one row per (method, factor) pair that changed: old value,
   new value, actor, timestamp. Answers the compliance question
   "who changed CardHealth on 2026-08-01 and from what to what?"
   which the upsert-in-place `factor_weights` table loses.

2. `score_results.weights_snapshot` — full effective weight vector at
   scoring time (nullable JSONB). Answers the ML training question
   "reproduce the score that was produced under this exact config."
   The existing `factors` JSONB captures evaluated-factor weights but
   loses skipped-factor weights; the snapshot is the complete config.

Downgrade IS destructive: drops the audit log and the snapshot column.
Guarded via `require_downgrade_ack` so an operator has to name this
revision in FORCE_DESTRUCTIVE_DOWNGRADE to actually run it.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.migration_guards import require_downgrade_ack


revision: str = "d4e8c1f95a72"
down_revision: Union[str, None] = "c9a7f10e5b28"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Audit table.
    op.create_table(
        "weight_change_log",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("collection_method", sa.String(length=50), nullable=False),
        sa.Column("factor_name", sa.String(length=255), nullable=False),
        sa.Column("old_weight", sa.Float(), nullable=True),
        sa.Column("new_weight", sa.Float(), nullable=True),
        sa.Column(
            "actor_type",
            sa.Enum(
                "user",
                "api_key",
                "system",
                name="weight_change_actor_type_enum",
            ),
            nullable=False,
        ),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("actor_name", sa.String(length=255), nullable=True),
        sa.Column("context", sa.String(length=50), nullable=True),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_weight_change_log_tenant_changed_at",
        "weight_change_log",
        ["tenant_id", "changed_at"],
    )

    # 2. Full-config snapshot per score. Nullable so existing rows
    # remain valid; populated for every new score from this revision on.
    op.add_column(
        "score_results",
        sa.Column(
            "weights_snapshot",
            sa.dialects.postgresql.JSONB(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    require_downgrade_ack(
        revision=revision,
        at_risk_count=lambda bind: (
            bind.execute(
                sa.text("SELECT count(*) FROM weight_change_log")
            ).scalar_one()
            + bind.execute(
                sa.text(
                    "SELECT count(*) FROM score_results "
                    "WHERE weights_snapshot IS NOT NULL"
                )
            ).scalar_one()
        ),
        description=(
            "Dropping weight_change_log wipes every tenant's weight-tuning "
            "audit trail — the compliance record of who changed which "
            "factor when. Dropping score_results.weights_snapshot loses "
            "the full weight vector each new score was produced under; "
            "the coarse per-evaluated-factor weight inside score_results."
            "factors JSONB survives, but skipped-factor weights and the "
            "'full config identity' are lost."
        ),
    )

    op.drop_column("score_results", "weights_snapshot")
    op.drop_index(
        "ix_weight_change_log_tenant_changed_at",
        table_name="weight_change_log",
    )
    op.drop_table("weight_change_log")
    sa.Enum(name="weight_change_actor_type_enum").drop(
        op.get_bind(), checkfirst=True
    )
