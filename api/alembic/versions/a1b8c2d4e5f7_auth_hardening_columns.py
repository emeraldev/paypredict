"""auth-hardening columns on users

Revision ID: a1b8c2d4e5f7
Revises: f3b7d92a1c8e
Create Date: 2026-09-03 09:00:00.000000

Adds three columns to `users`:

1. `failed_login_count` (int, default 0) — incremented on every wrong
   password at `/v1/auth/login`; cleared on any successful login.
2. `locked_until` (timestamptz, nullable) — set when
   `failed_login_count` crosses the lockout threshold; login is
   refused until now() >= locked_until, at which point the counter
   and the timestamp both clear on the next successful auth.
3. `password_changed_at` (timestamptz, nullable) — bumped to now()
   on every password change (self-service and admin-set). The JWT
   dependency rejects any token whose `iat` predates this
   timestamp. Nullable rather than NOT NULL so we don't invalidate
   existing sessions the day the migration ships; a NULL is
   treated as "never rotated" (the JWT iat check is skipped). New
   users have it set at creation.

Downgrade drops the columns. It's guarded because doing so also
drops the lockout state and the JWT-revocation timestamp — a
rollback + redeploy would let compromised sessions back in and
un-lock currently-locked accounts. `require_downgrade_ack` fires
on any row where either state is set.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.migration_guards import require_downgrade_ack


revision: str = "a1b8c2d4e5f7"
down_revision: Union[str, None] = "f3b7d92a1c8e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Additive; safe under concurrent traffic. server_default on
    # failed_login_count backfills existing rows to 0.
    op.add_column(
        "users",
        sa.Column(
            "failed_login_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "users",
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "password_changed_at", sa.DateTime(timezone=True), nullable=True
        ),
    )


def downgrade() -> None:
    require_downgrade_ack(
        revision=revision,
        at_risk_count=lambda bind: bind.execute(
            sa.text(
                "SELECT count(*) FROM users "
                "WHERE locked_until IS NOT NULL "
                "OR password_changed_at IS NOT NULL "
                "OR failed_login_count > 0"
            )
        ).scalar_one(),
        description=(
            "Dropping the auth-hardening columns removes both the "
            "failed-login lockout state (currently-locked accounts "
            "unlock silently) and the password_changed_at timestamp "
            "the JWT dependency uses to reject sessions issued before "
            "a password rotation. After a rollback + redeploy those "
            "compromised sessions would be honoured again."
        ),
    )
    op.drop_column("users", "password_changed_at")
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_count")
