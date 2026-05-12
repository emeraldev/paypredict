"""normalize factor key in score_results jsonb

Revision ID: 4664b45678c5
Revises: 5b17a75fd7b3
Create Date: 2026-05-12 19:41:33.296870

Legacy rows written by the bulk scoring path used `"factor"` instead of
`"factor_name"` for each entry in `factors -> 'evaluated'`. The single-
score path always used `"factor_name"`, which is what
`analytics_service.get_factor_contributions` reads.

This migration rewrites those legacy entries in place. Idempotent: rows
already using `"factor_name"` are skipped by the WHERE clause.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '4664b45678c5'
down_revision: Union[str, None] = '5b17a75fd7b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # For each evaluated factor entry that has "factor" but not "factor_name",
    # rename the key. jsonb_set adds factor_name, then `- 'factor'` drops the
    # legacy key.
    op.execute(
        """
        UPDATE score_results
        SET factors = jsonb_set(
            factors,
            '{evaluated}',
            (
                SELECT jsonb_agg(
                    CASE
                        WHEN entry ? 'factor_name' THEN entry
                        WHEN entry ? 'factor' THEN
                            jsonb_set(entry, '{factor_name}', entry -> 'factor') - 'factor'
                        ELSE entry
                    END
                )
                FROM jsonb_array_elements(factors -> 'evaluated') AS entry
            )
        )
        WHERE factors -> 'evaluated' IS NOT NULL
          AND EXISTS (
              SELECT 1
              FROM jsonb_array_elements(factors -> 'evaluated') AS entry
              WHERE entry ? 'factor' AND NOT (entry ? 'factor_name')
          )
        """
    )


def downgrade() -> None:
    # Reverse: rename factor_name back to factor on every evaluated entry.
    op.execute(
        """
        UPDATE score_results
        SET factors = jsonb_set(
            factors,
            '{evaluated}',
            (
                SELECT jsonb_agg(
                    CASE
                        WHEN entry ? 'factor_name' THEN
                            jsonb_set(entry, '{factor}', entry -> 'factor_name') - 'factor_name'
                        ELSE entry
                    END
                )
                FROM jsonb_array_elements(factors -> 'evaluated') AS entry
            )
        )
        WHERE factors -> 'evaluated' IS NOT NULL
        """
    )
