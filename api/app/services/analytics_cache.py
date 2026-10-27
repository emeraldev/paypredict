"""Redis-backed cache for the four analytics endpoints.

Analytics queries are expensive (`get_summary` was 8+ seconds in
staging before this landed because it fires 4 serial aggregations
over the full tenant dataset). Caching short-lived enough that
dashboards still feel fresh (60 s) but long enough that a user
clicking through pages hits warm cache repeatedly.

Keys: `analytics:<endpoint>:<tenant_id>:<param-hash>`. One line
per endpoint so a cache miss on summary doesn't invalidate
factors. All stored as JSON.

Values: the Pydantic response model's `.model_dump_json()` output.
On read, deserialise via the model's `.model_validate_json()`.
Keeps types honest without a separate schema version.

Failures (Redis down, serialisation hiccup) are swallowed: the
endpoint falls back to a direct query, slower but correct. We
never want cache infra to cause a 500.
"""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from typing import Any, TypeVar

import redis
from pydantic import BaseModel

from app.config import settings

_logger = logging.getLogger(__name__)

# One process-wide Redis client. Same connection-pool as rate limiting
# but a separate client instance so pipeline work on one doesn't
# collide with the other. redis-py is thread-safe.
_cache_redis = redis.from_url(settings.redis_url, decode_responses=True)

# Default TTL. Short enough that an admin updating weights sees the
# effect within ~1 min, long enough that back-to-back clicks on
# analytics are cache hits.
DEFAULT_TTL_SECONDS = 60

T = TypeVar("T", bound=BaseModel)


def _key(endpoint: str, tenant_id: uuid.UUID, params: dict[str, Any]) -> str:
    """Namespace: `analytics:<endpoint>:<tenant>:<param-hash>`.

    Params are serialised deterministically (`sort_keys=True`) and
    hashed with sha1 — short enough for a key, stable across
    equivalent inputs."""
    serialised = json.dumps(params, sort_keys=True, default=str)
    param_hash = hashlib.sha1(serialised.encode("utf-8")).hexdigest()[:16]
    return f"analytics:{endpoint}:{tenant_id}:{param_hash}"


def get(
    model_cls: type[T],
    endpoint: str,
    tenant_id: uuid.UUID,
    params: dict[str, Any],
) -> T | None:
    """Return cached response if present, else None.

    Cache misses + Redis failures both return None — the caller
    runs the real query. The None path is the normal path on a
    fresh deploy or after a weights change.
    """
    try:
        raw = _cache_redis.get(_key(endpoint, tenant_id, params))
    except Exception:
        _logger.warning(
            "analytics cache GET failed for %s", endpoint, exc_info=True
        )
        return None
    if raw is None:
        return None
    try:
        return model_cls.model_validate_json(raw)
    except Exception:
        _logger.warning(
            "analytics cache decode failed for %s — stale schema?",
            endpoint,
            exc_info=True,
        )
        # Delete the stale entry so the next call re-populates it fresh.
        try:
            _cache_redis.delete(_key(endpoint, tenant_id, params))
        except Exception:
            pass
        return None


def set_(
    endpoint: str,
    tenant_id: uuid.UUID,
    params: dict[str, Any],
    value: BaseModel,
    ttl: int = DEFAULT_TTL_SECONDS,
) -> None:
    """Store value under the computed key. Failures logged + swallowed."""
    try:
        _cache_redis.setex(
            _key(endpoint, tenant_id, params),
            ttl,
            value.model_dump_json(),
        )
    except Exception:
        _logger.warning(
            "analytics cache SET failed for %s", endpoint, exc_info=True
        )


def invalidate(tenant_id: uuid.UUID) -> None:
    """Drop every cached analytics response for this tenant.

    Called after mutations that would change analytics outputs —
    weight edits, bulk score imports, outcome edits. Uses `SCAN`
    rather than `KEYS` so we don't block Redis under load.
    """
    pattern = f"analytics:*:{tenant_id}:*"
    try:
        for key in _cache_redis.scan_iter(match=pattern, count=100):
            _cache_redis.delete(key)
    except Exception:
        _logger.warning(
            "analytics cache invalidate failed for tenant %s",
            tenant_id,
            exc_info=True,
        )
