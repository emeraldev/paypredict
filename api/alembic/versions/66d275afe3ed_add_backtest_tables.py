"""add_backtest_tables

Phase 3: BacktestRun + BacktestItem tables for the backtest tool.

Revision ID: 66d275afe3ed
Revises: af259bfe8cfa
Create Date: 2026-04-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "66d275afe3ed"
down_revision: Union[str, None] = "af259bfe8cfa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create backtest_runs table (enum created inline via sa.Enum)
    op.create_table(
        "backtest_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            sa.Enum("PROCESSING", "COMPLETED", "FAILED", name="backtest_status_enum"),
            nullable=False,
            server_default="PROCESSING",
        ),
        sa.Column("total_collections", sa.Integer(), nullable=False),
        sa.Column("factor_set_used", sa.String(length=50), nullable=False),
        sa.Column("weights_used", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("confusion_matrix", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("top_failure_factors", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_backtest_runs_tenant_created",
        "backtest_runs",
        ["tenant_id", "created_at"],
        unique=False,
    )

    # 3. Create backtest_items table
    op.create_table(
        "backtest_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("backtest_run_id", sa.UUID(), nullable=False),
        sa.Column("external_customer_id", sa.String(length=255), nullable=False),
        sa.Column("external_collection_id", sa.String(length=255), nullable=False),
        sa.Column("collection_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("collection_method", sa.String(length=50), nullable=False),
        sa.Column("predicted_score", sa.Float(), nullable=False),
        sa.Column("predicted_risk_level", sa.String(length=10), nullable=False),
        sa.Column("actual_outcome", sa.String(length=10), nullable=False),
        sa.Column("failure_reason", sa.String(length=255), nullable=True),
        sa.Column("factors", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("prediction_matched", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["backtest_run_id"], ["backtest_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_backtest_items_run_id",
        "backtest_items",
        ["backtest_run_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_backtest_items_run_id", table_name="backtest_items")
    op.drop_table("backtest_items")
    op.drop_index("ix_backtest_runs_tenant_created", table_name="backtest_runs")
    op.drop_table("backtest_runs")
    sa.Enum(name="backtest_status_enum").drop(op.get_bind(), checkfirst=True)
