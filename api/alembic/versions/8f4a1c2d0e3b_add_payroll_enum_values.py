"""add PAYROLL to factor_set_enum + collection_method_enum

Revision ID: 8f4a1c2d0e3b
Revises: 9ce5ceb0356c
Create Date: 2026-07-28 12:00:00.000000

Adds the PAYROLL value to both native Postgres enums so:
  - tenants.factor_set can be set to PAYROLL (new factor set for
    salary-advance lenders in Zambia)
  - score_requests.collection_method can be set to PAYROLL

`ALTER TYPE ... ADD VALUE IF NOT EXISTS` is the standard way to extend
a native enum on Postgres 12+ and is idempotent, so re-running the
migration on an already-migrated DB is a no-op. The `IF NOT EXISTS`
guard is important — without it, re-running would raise
`DuplicateObject`.

Downgrade is intentionally a no-op: Postgres does not support removing
a value from an enum type. If a hard rollback is needed, the whole
type has to be recreated (drop-and-recast), which is the pattern used
by migration 45bde65cbdd7 — but that's only worth doing if someone
actually needs to roll this back, which is unlikely.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "8f4a1c2d0e3b"
down_revision: Union[str, None] = "9ce5ceb0356c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE factor_set_enum ADD VALUE IF NOT EXISTS 'PAYROLL'")
    op.execute(
        "ALTER TYPE collection_method_enum ADD VALUE IF NOT EXISTS 'PAYROLL'"
    )


def downgrade() -> None:
    # Postgres does not support DROP VALUE on an enum. To truly roll back
    # you'd need to drop and recreate the enum (see migration 45bde65cbdd7
    # for the pattern) — deferred until a real rollback need appears.
    pass
