"""add recommended_score + score_improvement to score_results

Revision ID: 9ce5ceb0356c
Revises: 4664b45678c5
Create Date: 2026-05-14 17:32:16.207574

These two columns store the output of the timing optimiser
(`app/scoring/timing_optimiser.py`). Both are nullable — they're None
when the optimiser decided no shift was worth recommending, or for
historical rows that pre-date this feature.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '9ce5ceb0356c'
down_revision: Union[str, None] = '4664b45678c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "score_results",
        sa.Column("recommended_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "score_results",
        sa.Column("score_improvement", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("score_results", "score_improvement")
    op.drop_column("score_results", "recommended_score")
