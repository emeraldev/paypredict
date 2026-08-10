"""Shared guard helpers for destructive migrations.

`FORCE_DESTRUCTIVE_UPGRADE` and `FORCE_DESTRUCTIVE_DOWNGRADE` each
take a comma-separated list of Alembic revision IDs, or the sentinel
`all`. Only guards whose revision is in the list (or when `all` is
set) are bypassed. This is a deliberate departure from a single
boolean:

  - A boolean `1` disarms every guard in the codebase at once. Running
    `alembic downgrade base` with `FORCE_DESTRUCTIVE_DOWNGRADE=1` is
    then exactly as destructive as it was before any guard existed —
    a speed bump, not a gate.
  - A revision list forces per-operation consent. The operator names
    exactly which destructive step they've accepted.

CI needs a one-line escape (its round-trip test intentionally runs
against an empty DB but still executes every migration): `all` covers
that case and is conspicuous enough in a runbook that nobody pastes
it into a production shell by accident.

Usage inside a migration's `downgrade()`:

    from app.migration_guards import require_downgrade_ack

    require_downgrade_ack(
        revision="5b17a75fd7b3",
        at_risk_count=lambda bind: bind.execute(sa.text(
            "SELECT count(*) FROM tenants WHERE webhook_secret IS NOT NULL"
        )).scalar_one(),
        description=(
            "N tenants have webhook_secret set — dropping this column "
            "invalidates every customer's cached HMAC signing key."
        ),
    )
"""
from __future__ import annotations

import os
from typing import Callable

from alembic import op


_ALL_SENTINEL = "all"
_UPGRADE_ENV = "FORCE_DESTRUCTIVE_UPGRADE"
_DOWNGRADE_ENV = "FORCE_DESTRUCTIVE_DOWNGRADE"


def _allowed_revisions(env_var: str) -> set[str]:
    """Parse the env-var value into the set of allowed revisions."""
    raw = os.environ.get(env_var, "").strip()
    if not raw:
        return set()
    return {piece.strip() for piece in raw.split(",") if piece.strip()}


def _is_ack(env_var: str, revision: str) -> bool:
    """Has the operator explicitly consented to this migration's guard?"""
    allowed = _allowed_revisions(env_var)
    return _ALL_SENTINEL in allowed or revision in allowed


def _require_ack(
    *,
    env_var: str,
    direction: str,
    revision: str,
    at_risk_count: Callable[[object], int],
    description: str,
) -> None:
    bind = op.get_bind()
    n = at_risk_count(bind)
    if n == 0:
        return
    if _is_ack(env_var, revision):
        return
    raise RuntimeError(
        f"Refusing to {direction} migration {revision}: {n} at-risk "
        f"item(s) would be destroyed.\n\n"
        f"{description}\n\n"
        f"To proceed, set {env_var}={revision} in the environment. "
        f"For a nuclear reset (dev/CI only), set {env_var}=all."
    )


def require_downgrade_ack(
    *,
    revision: str,
    at_risk_count: Callable[[object], int],
    description: str,
) -> None:
    """Refuse the downgrade unless the operator has ack'd this revision.

    `at_risk_count` is called with the Alembic connection and should
    return the count of rows / columns / whatever that would be
    destroyed. Zero → skip the guard silently (empty DB in CI).
    `description` should explain what's at risk and, if applicable,
    how to preserve the data before proceeding.
    """
    _require_ack(
        env_var=_DOWNGRADE_ENV,
        direction="downgrade",
        revision=revision,
        at_risk_count=at_risk_count,
        description=description,
    )


def require_upgrade_ack(
    *,
    revision: str,
    at_risk_count: Callable[[object], int],
    description: str,
) -> None:
    """Refuse the upgrade unless the operator has ack'd this revision.

    Symmetric counterpart to `require_downgrade_ack` for the rare case
    where an upgrade itself destroys data (e.g. a one-way schema
    change that discards rows the new shape can't hold).
    """
    _require_ack(
        env_var=_UPGRADE_ENV,
        direction="upgrade",
        revision=revision,
        at_risk_count=at_risk_count,
        description=description,
    )


def require_downgrade_precondition(
    *,
    revision: str,
    check: Callable[[object], int],
    unmet_message: str,
) -> None:
    """Refuse the downgrade unconditionally when `check` returns > 0.

    Differs from `require_downgrade_ack` in that `FORCE_DESTRUCTIVE_DOWNGRADE`
    does NOT bypass this — it's for the case where the downgrade *cannot
    physically succeed* given current data, not for "this will delete
    stuff, are you sure?". For example: a value in an enum column that
    doesn't exist in the enum shape being restored. Forcing the
    downgrade would just crash it anyway.

    The operator must resolve the precondition first (e.g. reclassify
    the offending rows with a specific UPDATE statement), then re-run
    the downgrade. `unmet_message` should include the exact SQL and
    identifiers they need. Empty-condition (check returns 0) proceeds
    silently so CI works.
    """
    bind = op.get_bind()
    n = check(bind)
    if n == 0:
        return
    raise RuntimeError(
        f"Cannot downgrade migration {revision}: precondition unmet "
        f"({n} row(s) block the downgrade).\n\n{unmet_message}"
    )
