"""Startup preconditions the app refuses to run without.

Currently one check: DB migration version equals the expected head.
Wired into the FastAPI lifespan so uvicorn crashes with a clear
message when the DB is behind — no request ever reaches an endpoint
that would 500 on a missing column.

Real-world triggers this catches:

  1. Deploy sequencing bug — new API code shipped before migrations
     ran. Every request hits the missing-column error until the
     migration catches up. First customer 500s land here.
  2. Failed partial migration — migration A applied, B crashed
     mid-way. Half-migrated DB looks fine to code that expects head.
  3. Ops mistake — `alembic downgrade -1` typed against the wrong
     env. The non-destructive downgrades don't hit our destructive-
     op guards; they land silently.
  4. Restore from an older backup — DR event, snapshot from a prior
     schema version.
  5. Blue/green deploy overlap — old + new code both serving during
     rollout, migration state serves whichever version wins.

Costs ~1ms per boot. Cheaper than the alternative.
"""
from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine


_API_ROOT = Path(__file__).resolve().parent.parent
_ALEMBIC_INI = _API_ROOT / "alembic.ini"


class SchemaVersionMismatch(RuntimeError):
    """Raised at startup when the DB's alembic_version doesn't match
    the code's expected head. Uvicorn treats this as a startup crash
    (the app never binds), which is the correct behaviour — a partially-
    migrated DB serving live traffic is worse than a container that
    won't start."""


def expected_head() -> str:
    """The Alembic head as declared by the versions/ directory this
    code shipped with. Computed once per process (no I/O in the hot
    path — this only runs at boot)."""
    cfg = Config(str(_ALEMBIC_INI))
    heads = ScriptDirectory.from_config(cfg).get_heads()
    if len(heads) != 1:
        # Branch migrations — a scenario this project doesn't use, but
        # if it ever does we need to be intentional about which head is
        # "current". Refuse rather than picking the wrong one silently.
        raise SchemaVersionMismatch(
            f"Alembic script directory reports {len(heads)} heads: {heads}. "
            "This project assumes a single linear migration history."
        )
    return heads[0]


async def current_db_version(bind: AsyncConnection | AsyncEngine) -> str | None:
    """The revision currently applied to the DB. `None` means the
    alembic_version table doesn't exist (fresh DB, or a DB that has
    never been migrated). Callers treat that as its own failure mode.

    Accepts either an AsyncConnection (already open — e.g. from a
    request's session) or an AsyncEngine (opens a short-lived
    connection). The engine path is what the boot check uses; the
    connection path is what `/health/detailed` uses so the query
    joins the request's transaction context.
    """
    async def _query(conn: AsyncConnection) -> str | None:
        try:
            result = await conn.execute(text("SELECT version_num FROM alembic_version"))
            row = result.first()
        except ProgrammingError:
            return None
        return row[0] if row else None

    if isinstance(bind, AsyncEngine):
        async with bind.connect() as conn:
            return await _query(conn)
    return await _query(bind)


async def assert_db_at_head(bind: AsyncConnection | AsyncEngine) -> None:
    """Refuse startup unless the DB is at the code's expected head.

    Two failure shapes surface here:
      - `alembic_version` table missing → the DB was never migrated.
        Message tells the operator to run `alembic upgrade head`.
      - version mismatch → the DB is at a different revision than
        this code expects. Both directions are bad (ahead or behind);
        we report the exact revisions so ops knows what to reconcile.
    """
    expected = expected_head()
    actual = await current_db_version(bind)

    if actual is None:
        raise SchemaVersionMismatch(
            "alembic_version table not found in the target database. "
            "The DB has never been migrated. Run `alembic upgrade head` "
            "before starting the app."
        )
    if actual != expected:
        raise SchemaVersionMismatch(
            f"DB migration version mismatch: DB is at {actual!r}, code "
            f"expects {expected!r}. Refusing to serve traffic — a "
            "partially-migrated DB would 500 on missing columns. "
            "Reconcile with `alembic upgrade head` (or downgrade the "
            "code) before restarting."
        )
