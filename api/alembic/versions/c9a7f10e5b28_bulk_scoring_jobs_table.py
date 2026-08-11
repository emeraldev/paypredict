"""bulk_scoring_jobs table (Postgres source of truth for async jobs)

Revision ID: c9a7f10e5b28
Revises: 7e2c8ab391f5
Create Date: 2026-08-11 14:00:00.000000

Moves async bulk-scoring job state (status / progress / results /
error) from Redis to Postgres. Fixes the PR #37 (H4) limitation:
Redis being down at the moment `on_failure` fired meant the failure
record couldn't be written, and the polling client saw eternal
`processing` until the 1h TTL expired. Postgres survives Redis
outages, so terminal transitions always land somewhere the customer
can observe.

Downgrade is destructive: dropping the table loses every tenant's
async-bulk history. Guarded via `require_downgrade_ack` — refuses
unless the operator names this revision in
`FORCE_DESTRUCTIVE_DOWNGRADE`.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.migration_guards import require_downgrade_ack


revision: str = "c9a7f10e5b28"
down_revision: Union[str, None] = "7e2c8ab391f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bulk_scoring_jobs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("job_id", sa.UUID(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "processing",
                "completed",
                "failed",
                name="bulk_scoring_job_status_enum",
            ),
            nullable=False,
        ),
        sa.Column("total_items", sa.Integer(), nullable=False),
        sa.Column("completed_items", sa.Integer(), nullable=False),
        sa.Column("summary", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("results", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("error", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "job_id", name="uq_bulk_scoring_jobs_tenant_job"
        ),
    )
    op.create_index(
        "ix_bulk_scoring_jobs_tenant_job",
        "bulk_scoring_jobs",
        ["tenant_id", "job_id"],
    )


def downgrade() -> None:
    require_downgrade_ack(
        revision=revision,
        at_risk_count=lambda bind: bind.execute(
            sa.text("SELECT count(*) FROM bulk_scoring_jobs")
        ).scalar_one(),
        description=(
            "Dropping bulk_scoring_jobs wipes every tenant's async "
            "bulk-scoring history — the record of which large uploads "
            "were queued, how far they got, and what results came back. "
            "Individual score rows in score_results are unaffected "
            "(they live in their own table); only the job envelope is "
            "lost."
        ),
    )

    op.drop_index("ix_bulk_scoring_jobs_tenant_job", table_name="bulk_scoring_jobs")
    op.drop_table("bulk_scoring_jobs")
    sa.Enum(name="bulk_scoring_job_status_enum").drop(op.get_bind(), checkfirst=True)
