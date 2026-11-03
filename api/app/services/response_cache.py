"""Redis-backed response cache, parameterised by namespace.

Three dashboard endpoints hit this today: analytics (summary +
collection_rate + factors + accuracy), config/weights, and the
scores list summary. All share the same shape: a Pydantic response
model keyed per tenant + request params, short-lived enough that
dashboards still feel fresh, long enough that back-to-back clicks
are cache hits.

Keys: `<namespace>:<endpoint>:<tenant_id>:<param-hash>`. One line
per endpoint so a cache miss on one doesn't invalidate the others.
All stored as JSON (the model's `.model_dump_json()`); read via
`.model_validate_json()` so types stay honest without a separate
schema version.

Failures (Redis down, serialisation hiccup) are swallowed: the
caller falls back to a direct query, slower but correct. We never
want cache infra to cause a 500.
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
# effect within ~1 min, long enough that back-to-back clicks are hits.
DEFAULT_TTL_SECONDS = 60

T = TypeVar("T", bound=BaseModel)


def _key(
    namespace: str,
    endpoint: str,
    tenant_id: uuid.UUID,
    params: dict[str, Any],
) -> str:
    """`<namespace>:<endpoint>:<tenant>:<param-hash>`.

    Params are serialised deterministically (`sort_keys=True`) and
    hashed with sha1. Short enough for a key, stable across
    equivalent inputs.
    """
    serialised = json.dumps(params, sort_keys=True, default=str)
    param_hash = hashlib.sha1(serialised.encode("utf-8")).hexdigest()[:16]
    return f"{namespace}:{endpoint}:{tenant_id}:{param_hash}"


def get(
    namespace: str,
    model_cls: type[T],
    endpoint: str,
    tenant_id: uuid.UUID,
    params: dict[str, Any],
) -> T | None:
    """Return cached response if present, else None.

    Cache misses and Redis failures both return None. The caller
    runs the real query. The None path is the normal path on a
    fresh deploy or after an invalidation.
    """
    try:
        raw = _cache_redis.get(_key(namespace, endpoint, tenant_id, params))
    except Exception:
        _logger.warning(
            "%s cache GET failed for %s", namespace, endpoint, exc_info=True
        )
        return None
    if raw is None:
        return None
    try:
        return model_cls.model_validate_json(raw)
    except Exception:
        _logger.warning(
            "%s cache decode failed for %s (stale schema?)",
            namespace,
            endpoint,
            exc_info=True,
        )
        try:
            _cache_redis.delete(_key(namespace, endpoint, tenant_id, params))
        except Exception:
            pass
        return None


def set_(
    namespace: str,
    endpoint: str,
    tenant_id: uuid.UUID,
    params: dict[str, Any],
    value: BaseModel,
    ttl: int = DEFAULT_TTL_SECONDS,
) -> None:
    """Store value under the computed key. Failures logged and swallowed."""
    try:
        _cache_redis.setex(
            _key(namespace, endpoint, tenant_id, params),
            ttl,
            value.model_dump_json(),
        )
    except Exception:
        _logger.warning(
            "%s cache SET failed for %s", namespace, endpoint, exc_info=True
        )


def invalidate(namespace: str, tenant_id: uuid.UUID) -> None:
    """Drop every cached response in this namespace for this tenant.

    Called after mutations that would change the cached output
    (weight edits, bulk score imports, outcome edits). Uses `SCAN`
    rather than `KEYS` so we don't block Redis under load.
    """
    pattern = f"{namespace}:*:{tenant_id}:*"
    try:
        for key in _cache_redis.scan_iter(match=pattern, count=100):
            _cache_redis.delete(key)
    except Exception:
        _logger.warning(
            "%s cache invalidate failed for tenant %s",
            namespace,
            tenant_id,
            exc_info=True,
        )
