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


# ---- Startup: warm the connection pool ------------------------------
#
# asyncpg connections to Neon over Frankfurt RTT (~160 ms) take
# multiple round-trips to establish (TCP + TLS + Postgres auth), so
# a fresh connection costs ~500 ms-1 s before the first query even
# starts. On a freshly booted Fly machine the SQLAlchemy pool is
# empty — the first user request pays the full handshake cost, and
# the parallelized analytics endpoints pay it four times over
# (once per fresh session, in parallel but still bottlenecked by
# the slowest handshake).
#
# `warm_connection_pool` fires N trivial queries in parallel at
# startup to pre-establish N pooled connections. By the time
# traffic arrives, the pool has warm connections ready for the
# `run_parallel` helpers to check out.
#
# Failure is logged + swallowed: a warmup problem must not block
# serving. The lifespan hook already runs `assert_db_at_head`
# which fails hard on real DB issues — warmup is best-effort.


async def warm_connection_pool(n: int = 5, timeout: float = 15.0) -> int:
    """Pre-establish `n` pooled asyncpg connections.

    Returns the number that actually succeeded. Each warmup runs
    its own fresh session, holds the connection briefly via a
    `SELECT 1`, and releases it back to the pool warm. Any failure
    is logged and treated as 0 for that slot — the app keeps
    booting.

    Default `n=5` warms half of `pool_size=10`, enough that the
    four parallel analytics branches + one request's main session
    all check out warm. More would pay for cold-start wall-clock
    with diminishing returns.
    """
    from sqlalchemy import text

    async def _one() -> bool:
        try:
            async with async_session() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception:
            _logger.warning("connection pool warmup slot failed", exc_info=True)
            return False

    try:
        results = await asyncio.wait_for(
            asyncio.gather(*(_one() for _ in range(n))),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        _logger.warning(
            "connection pool warmup exceeded %.1fs timeout — continuing cold",
            timeout,
        )
        return 0
    succeeded = sum(1 for r in results if r)
    _logger.info(
        "connection pool warmup: %d/%d slots established", succeeded, n
    )
    return succeeded


# Logger used by the warmup. Kept here (not imported from a utils
# module) so this file has no app-internal dependencies — database.py
# is at the bottom of the import tree.
import logging  # noqa: E402

_logger = logging.getLogger(__name__)
