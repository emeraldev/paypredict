"""factor weights per collection_method

Revision ID: 52f6a4d1b0c9
Revises: 8f4a1c2d0e3b
Create Date: 2026-08-08 10:00:00.000000

Adds `collection_method` to `factor_weights` so a single tenant can tune
weights per method (a card+debit-order lender or a lender expanding across
markets no longer has to duplicate accounts).

Backfill rules:
- CARD_DEBIT tenants: existing rows are copied to both CARD and DEBIT_ORDER
  so the tenant keeps their tuning for both.
- MOBILE_WALLET tenants: existing rows -> MOBILE_MONEY.
- PAYROLL tenants: existing rows -> PAYROLL.
- CUSTOM tenants (unused today): backfilled as CARD (arbitrary fallback).

Old rows without a collection_method are removed after the expansion —
they'd violate the new unique constraint otherwise.

Downgrade is destructive by design: it collapses two rows-per-CARD_DEBIT
tenant back into one (keeping the CARD sibling, dropping DEBIT_ORDER).
Any DEBIT_ORDER-only customisations made through the new UI would be
lost. Guarded via `require_downgrade_ack` — refuses unless the operator
names this revision in `FORCE_DESTRUCTIVE_DOWNGRADE` (see
`alembic/guards.py`).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.migration_guards import require_downgrade_ack


revision: str = "52f6a4d1b0c9"
down_revision: Union[str, None] = "8f4a1c2d0e3b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add column, nullable so backfill can proceed.
    op.add_column(
        "factor_weights",
        sa.Column("collection_method", sa.String(length=50), nullable=True),
    )

    # 2. Drop the old unique constraint UP FRONT. The expansion insert below
    #    would otherwise collide on (tenant_id, factor_name) with the
    #    pre-migration rows we haven't deleted yet.
    op.drop_constraint(
        "uq_factor_weight_tenant_factor",
        "factor_weights",
        type_="unique",
    )

    # 3. Expand each pre-migration row into one row per applicable method.
    #    CARD_DEBIT tenants get both CARD and DEBIT_ORDER so their tuning
    #    survives for both. gen_random_uuid() is core in PG 13+.
    #
    #    Cast `t.factor_set` (a Postgres enum) to text before the CASE so we
    #    compare text-against-text — otherwise PG has to resolve the string
    #    literals as enum values, and when the previous migration
    #    (8f4a1c2d0e3b) added PAYROLL to `factor_set_enum` in the same
    #    Alembic run it can't be used yet (UnsafeNewEnumValueUsageError).
    op.execute(
        """
        INSERT INTO factor_weights
            (id, tenant_id, factor_name, weight, updated_at, updated_by,
             collection_method)
        SELECT gen_random_uuid(), fw.tenant_id, fw.factor_name, fw.weight,
               fw.updated_at, fw.updated_by, m.method
        FROM factor_weights fw
        JOIN tenants t ON t.id = fw.tenant_id
        CROSS JOIN LATERAL (
            SELECT unnest(
                CASE t.factor_set::text
                    WHEN 'CARD_DEBIT'    THEN ARRAY['CARD', 'DEBIT_ORDER']
                    WHEN 'MOBILE_WALLET' THEN ARRAY['MOBILE_MONEY']
                    WHEN 'PAYROLL'       THEN ARRAY['PAYROLL']
                    ELSE                      ARRAY['CARD']
                END
            ) AS method
        ) m
        WHERE fw.collection_method IS NULL
        """
    )

    # 4. Delete the pre-migration rows (their content was just expanded).
    op.execute("DELETE FROM factor_weights WHERE collection_method IS NULL")

    # 5. NOT NULL now that every row has a method.
    op.alter_column(
        "factor_weights",
        "collection_method",
        existing_type=sa.String(length=50),
        nullable=False,
    )

    # 6. Create the new unique constraint.
    op.create_unique_constraint(
        "uq_factor_weight_tenant_method_factor",
        "factor_weights",
        ["tenant_id", "collection_method", "factor_name"],
    )


def downgrade() -> None:
    require_downgrade_ack(
        revision=revision,
        at_risk_count=lambda bind: bind.execute(
            sa.text(
                "SELECT count(*) FROM factor_weights "
                "WHERE collection_method IN ('DEBIT_ORDER', 'MOBILE_MONEY', 'PAYROLL')"
            )
        ).scalar_one(),
        description=(
            "DEBIT_ORDER / MOBILE_MONEY / PAYROLL factor_weight rows have no "
            "home in the old schema (unique(tenant_id, factor_name) restore "
            "would collide). These rows will be deleted; tenants' per-method "
            "tuning for those methods is lost."
        ),
    )

    # 1. Restore the old unique constraint. Non-CARD rows would collide with
    #    their CARD sibling (or be orphaned entirely), so drop them first.
    #    CARD wins as the canonical representation of the old CARD_DEBIT
    #    weights.
    op.execute(
        "DELETE FROM factor_weights "
        "WHERE collection_method IN ('DEBIT_ORDER', 'MOBILE_MONEY', 'PAYROLL')"
    )

    op.drop_constraint(
        "uq_factor_weight_tenant_method_factor",
        "factor_weights",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_factor_weight_tenant_factor",
        "factor_weights",
        ["tenant_id", "factor_name"],
    )

    # 2. Drop the column.
    op.drop_column("factor_weights", "collection_method")
