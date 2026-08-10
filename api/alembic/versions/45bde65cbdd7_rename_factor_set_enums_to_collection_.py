"""rename_factor_set_enums_to_collection_method

Factor sets describe the collection method, not the geography.
CARD_SA → CARD_DEBIT, MOBILE_ZM → MOBILE_WALLET.

Revision ID: 45bde65cbdd7
Revises: f012f11380b2
Create Date: 2026-04-08 17:07:06.356780

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.migration_guards import require_downgrade_precondition


# revision identifiers, used by Alembic.
revision: str = '45bde65cbdd7'
down_revision: Union[str, None] = 'f012f11380b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_PAYROLL_PRECONDITION_MSG = """\
This migration's downgrade recreates factor_set_enum WITHOUT PAYROLL
(the value was added by a later migration, 8f4a1c2d0e3b, whose own
downgrade is a no-op because Postgres cannot remove enum values).

Any tenant with factor_set='PAYROLL' cannot be cast into the old
enum, so this downgrade would crash mid-transaction.

The fix must happen BEFORE running the downgrade — reclassify the
affected tenants to a value that exists in both enum shapes:

    UPDATE tenants
    SET factor_set = 'CUSTOM'
    WHERE factor_set = 'PAYROLL';

This is a semantic change to how those tenants are scored. There is
NO automatic path back — a subsequent re-upgrade will not restore
their PAYROLL classification. Record the tenant ids first:

    SELECT id, name FROM tenants WHERE factor_set = 'PAYROLL';

FORCE_DESTRUCTIVE_DOWNGRADE does NOT bypass this check — the cast
would fail regardless of the flag."""


def upgrade() -> None:
    # 1. Rename factor_set enum: CARD_SA → CARD_DEBIT, MOBILE_ZM → MOBILE_WALLET
    # PostgreSQL can't rename enum values in-place within a transaction,
    # so we convert to text, replace values, drop old enum, create new, cast back.

    # Convert column to text
    op.execute("ALTER TABLE tenants ALTER COLUMN factor_set TYPE text")

    # Update values
    op.execute("UPDATE tenants SET factor_set = 'CARD_DEBIT' WHERE factor_set = 'CARD_SA'")
    op.execute("UPDATE tenants SET factor_set = 'MOBILE_WALLET' WHERE factor_set = 'MOBILE_ZM'")

    # Drop old enum and create new one
    op.execute("DROP TYPE factor_set_enum")
    op.execute("CREATE TYPE factor_set_enum AS ENUM ('CARD_DEBIT', 'MOBILE_WALLET', 'CUSTOM')")

    # Convert back to enum
    op.execute(
        "ALTER TABLE tenants ALTER COLUMN factor_set TYPE factor_set_enum "
        "USING factor_set::factor_set_enum"
    )

    # 2. Update model_version strings in score_results
    op.execute(
        "UPDATE score_results SET model_version = 'heuristic_card_v1' "
        "WHERE model_version = 'heuristic_sa_v1'"
    )
    op.execute(
        "UPDATE score_results SET model_version = 'heuristic_wallet_v1' "
        "WHERE model_version = 'heuristic_zm_v1'"
    )


def downgrade() -> None:
    require_downgrade_precondition(
        revision=revision,
        check=lambda bind: bind.execute(
            sa.text("SELECT count(*) FROM tenants WHERE factor_set = 'PAYROLL'")
        ).scalar_one(),
        unmet_message=_PAYROLL_PRECONDITION_MSG,
    )

    # 1. Revert factor_set enum
    op.execute("ALTER TABLE tenants ALTER COLUMN factor_set TYPE text")

    op.execute("UPDATE tenants SET factor_set = 'CARD_SA' WHERE factor_set = 'CARD_DEBIT'")
    op.execute("UPDATE tenants SET factor_set = 'MOBILE_ZM' WHERE factor_set = 'MOBILE_WALLET'")

    op.execute("DROP TYPE factor_set_enum")
    op.execute("CREATE TYPE factor_set_enum AS ENUM ('CARD_SA', 'MOBILE_ZM', 'CUSTOM')")

    op.execute(
        "ALTER TABLE tenants ALTER COLUMN factor_set TYPE factor_set_enum "
        "USING factor_set::factor_set_enum"
    )

    # 2. Revert model_version strings
    op.execute(
        "UPDATE score_results SET model_version = 'heuristic_sa_v1' "
        "WHERE model_version = 'heuristic_card_v1'"
    )
    op.execute(
        "UPDATE score_results SET model_version = 'heuristic_zm_v1' "
        "WHERE model_version = 'heuristic_wallet_v1'"
    )
