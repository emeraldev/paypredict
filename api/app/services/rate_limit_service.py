"""Fixed-window per-tenant rate limiter backed by Redis.

Each lender-facing API request increments a counter keyed by tenant id
and the current minute. When the counter exceeds the tenant's plan
limit, the request is rejected with the documented 429 contract.

Design notes:
  - We use a *fixed* one-minute window, not sliding. At the documented
    60-2000 req/min scales, the boundary jitter is invisible, and the
    Redis bookkeeping is a single INCR + EXPIRE.
  - The Redis key auto-expires `RATE_LIMIT_WINDOW_SECONDS + 10` seconds
    after the window opens, so leftover state from a previous minute is
    never read.
  - Bulk endpoints count as one ticket regardless of batch size — matches
    the existing rate-limit contract in docs/api-reference.md.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

import redis

from app.config import PLAN_RATE_LIMITS, RATE_LIMIT_WINDOW_SECONDS


@dataclass(frozen=True)
class RateLimitResult:
    """Outcome of a single rate-limit check + increment.

    `allowed` is False iff the count exceeded the tier limit. When False,
    the count was *not* incremented — the request never spent a ticket.
    `retry_after` is the seconds until the window resets.
    """

    allowed: bool
    limit: int
    remaining: int
    reset: int  # unix timestamp
    retry_after: int


def get_limit_for_plan(plan: str) -> int:
    """Look up the per-minute request limit for a plan tier.

    Unknown plans fall back to the most restrictive tier so a typo never
    accidentally grants unlimited access. Exists as a function (rather
    than a direct dict lookup) so tests can monkeypatch limits without
    rebuilding the dict.
    """
    return PLAN_RATE_LIMITS.get(plan, PLAN_RATE_LIMITS["PILOT"])


def _bucket_key(tenant_id: uuid.UUID, now: int) -> str:
    window = now // RATE_LIMIT_WINDOW_SECONDS
    return f"ratelimit:{tenant_id}:{window}"


def check_and_increment(
    tenant_id: uuid.UUID,
    plan: str,
    redis_client: redis.Redis,
    *,
    now: int | None = None,
) -> RateLimitResult:
    """Atomically count this request against the tenant's window.

    `now` is injectable to make per-window tests deterministic without
    monkeypatching `time.time()` globally.
    """
    limit = get_limit_for_plan(plan)
    now = int(time.time()) if now is None else now
    key = _bucket_key(tenant_id, now)
    window_end = ((now // RATE_LIMIT_WINDOW_SECONDS) + 1) * RATE_LIMIT_WINDOW_SECONDS
    retry_after = max(1, window_end - now)

    # Read current count first — if already at limit, don't burn a ticket.
    current_raw = redis_client.get(key)
    current = int(current_raw) if current_raw is not None else 0
    if current >= limit:
        return RateLimitResult(
            allowed=False,
            limit=limit,
            remaining=0,
            reset=window_end,
            retry_after=retry_after,
        )

    # Increment + set TTL atomically. EXPIRE is idempotent; resetting it
    # each increment is fine because the key is keyed by the window
    # itself — the TTL just keeps stale keys from accumulating.
    pipe = redis_client.pipeline()
    pipe.incr(key)
    pipe.expire(key, RATE_LIMIT_WINDOW_SECONDS + 10)
    new_count, _ = pipe.execute()
    new_count = int(new_count)

    return RateLimitResult(
        allowed=True,
        limit=limit,
        remaining=max(0, limit - new_count),
        reset=window_end,
        retry_after=retry_after,
    )


def headers_for(result: RateLimitResult) -> dict[str, str]:
    """Standard rate-limit headers to attach to every response.

    Matches the contract documented on the 429 response in the public
    OpenAPI schema (Retry-After is added separately on 429).
    """
    return {
        "X-RateLimit-Limit": str(result.limit),
        "X-RateLimit-Remaining": str(result.remaining),
        "X-RateLimit-Reset": str(result.reset),
    }
