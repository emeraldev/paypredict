"""phase_2_5_dashboard_endpoints_setup

Phase 2.5 prep for dashboard-facing endpoints:

1. Add Tenant.email_digest (enum OFF/DAILY/WEEKLY, default OFF)
2. Add Tenant.email_recipients (text[], default empty array)
3. Add ScoreResult composite index (tenant_id, risk_level, created_at)
   for the dashboard list query.
4. Add Outcome composite index (tenant_id, outcome, created_at)
   for the dashboard outcomes list + analytics queries.

Revision ID: af259bfe8cfa
Revises: 45bde65cbdd7
Create Date: 2026-04-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "af259bfe8cfa"
down_revision: Union[str, None] = "45bde65cbdd7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create the email_digest enum type
    email_digest_enum = sa.Enum(
        "OFF", "DAILY", "WEEKLY", name="email_digest_enum"
    )
    email_digest_enum.create(op.get_bind(), checkfirst=True)

    # 2. Add Tenant columns
    op.add_column(
        "tenants",
        sa.Column(
            "email_digest",
            sa.Enum("OFF", "DAILY", "WEEKLY", name="email_digest_enum", create_type=False),
            nullable=False,
            server_default="OFF",
        ),
    )
    op.add_column(
        "tenants",
        sa.Column(
            "email_recipients",
            sa.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
    )

    # 3. ScoreResult composite index for filtered list queries
    op.create_index(
        "ix_score_results_tenant_risk_created",
        "score_results",
        ["tenant_id", "risk_level", "created_at"],
        unique=False,
    )

    # 4. Outcome composite index for outcomes list + analytics
    op.create_index(
        "ix_outcomes_tenant_outcome_created",
        "outcomes",
        ["tenant_id", "outcome", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    # 4. Drop Outcome composite index
    op.drop_index("ix_outcomes_tenant_outcome_created", table_name="outcomes")

    # 3. Drop ScoreResult composite index
    op.drop_index("ix_score_results_tenant_risk_created", table_name="score_results")

    # 2. Drop Tenant columns
    op.drop_column("tenants", "email_recipients")
    op.drop_column("tenants", "email_digest")

    # 1. Drop the enum type
    sa.Enum(name="email_digest_enum").drop(op.get_bind(), checkfirst=True)
