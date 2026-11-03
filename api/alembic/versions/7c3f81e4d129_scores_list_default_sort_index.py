"""Index score_results on (tenant_id, score DESC) for the dashboard list default sort.

Revision ID: 7c3f81e4d129
Revises: a1b8c2d4e5f7
Create Date: 2026-11-03 10:30:00.000000

The dashboard home page (`GET /v1/scores`) defaults to
`ORDER BY score_results.score DESC`. Prior to this migration, that
sort fell back to the tenant-leading indexes (`ix_score_results_tenant_created`
and `ix_score_results_tenant_risk`) which do not include the score
column, forcing Postgres to sort the full tenant partition in memory
for every page load. Measured ~1.5-2 s of the warm 2.3 s latency on
staging comes from that sort.

Add a composite index on `(tenant_id, score DESC)`. The planner can
scan this index directly to produce the first N rows in sort order,
dropping the sort step entirely.

Built with `CREATE INDEX CONCURRENTLY` so a live table takes no
exclusive lock during the build (safe to run during traffic).

Downgrade drops the index. Non-destructive on data; a redeploy would
only re-slow the default sort.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "7c3f81e4d129"
down_revision: Union[str, None] = "a1b8c2d4e5f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# migration-guard: ok - drop_index is reversible, non-destructive on data.
def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.create_index(
            "ix_score_results_tenant_score_desc",
            "score_results",
            ["tenant_id", "score"],
            postgresql_concurrently=True,
            postgresql_ops={"score": "DESC"},
        )


# migration-guard: ok - drop_index is reversible, non-destructive on data.
def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.drop_index(
            "ix_score_results_tenant_score_desc",
            table_name="score_results",
            postgresql_concurrently=True,
        )
