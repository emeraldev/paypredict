import asyncio
from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "development",
    pool_size=10,
    max_overflow=20,
    # - statement_cache_size=0: required when the DATABASE_URL points
    #   at a PgBouncer transaction-pooling endpoint (Neon's `-pooler`
    #   hostname, the default we use in Fly). Transaction-mode pooling
    #   reuses backend connections across clients, so cached statement
    #   names collide across requests and asyncpg raises
    #   DuplicatePreparedStatementError on the second call. Zero cache
    #   = asyncpg re-parses each statement (~sub-ms). Non-pooled
    #   Postgres (local Docker, direct Neon endpoint) is unaffected.
    # - timeout=90: Neon's free tier suspends computes after 5 min
    #   idle; the first reconnect triggers a cold-start of ~10-30 s
    #   (occasionally longer). asyncpg's default connect timeout is
    #   60s which can trip on a slow cold-start. 90s rides those out.
    #   Covers production too — a lender's first API call after a
    #   quiet period shouldn't 500.
    connect_args={"statement_cache_size": 0, "timeout": 90},
    # Note: pool_pre_ping is deliberately NOT enabled.
    # When Neon's free-tier auto-suspend was in play, pre-ping was
    # the defence against stale pooled connections surviving a
    # compute suspension. We upgraded to Neon's Launch plan + set
    # scale-to-zero to "off" on both branches (2026-10-27), so the
    # compute never suspends in normal operation. Keeping pre-ping
    # on would just add one ~160 ms Frankfurt-RTT round-trip per
    # request for no benefit. If we ever revert Neon to a tier that
    # auto-suspends, re-enable this.
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ---- Parallel reads --------------------------------------------------
#
# Running two `db.execute()` calls on the same AsyncSession via
# `asyncio.gather` is unsafe (SQLAlchemy's AsyncSession is not safe
# for concurrent use; raises MissingGreenlet). To truly run queries
# in parallel each coroutine needs its own session + connection.
#
# `run_parallel` is the production path — fresh sessions, true
# parallelism, saves N × 160 ms of Frankfurt round-trips. Tests
# override via conftest to use the test's single session
# SEQUENTIALLY — the test infra binds one session to one connection
# + transaction rollback, and fresh sessions would escape that
# rollback and pollute the test DB.


T = TypeVar("T")

QueryFn = Callable[[AsyncSession], Awaitable[T]]


async def _run_in_fresh_session(fn: QueryFn[T]) -> T:
    """Default implementation: open a fresh session for the query."""
    async with async_session() as session:
        return await fn(session)


# Indirection the test fixture replaces so the test session (which
# owns the open transaction and savepoint) is reused instead of a
# fresh session escaping the rollback. Production: real fresh
# session via `_run_in_fresh_session`. Tests: wrapped to reuse the
# fixture session.
_parallel_runner: Callable[[QueryFn], Awaitable] = _run_in_fresh_session


async def run_parallel(*fns: QueryFn) -> tuple:
    """Run N read-only query functions in parallel against the DB.

    Each `fn` receives a fresh `AsyncSession` (production) or the
    shared test session (tests). Results come back in order,
    tupled.

    Use for independent READ queries where the only reason they
    were serial was that they share a session — e.g. the four
    aggregations in `analytics_service.get_summary`. Not for
    writes; those should stay on the request's shared session so
    `get_db`'s commit covers them atomically.
    """
    return tuple(await asyncio.gather(*(_parallel_runner(fn) for fn in fns)))
