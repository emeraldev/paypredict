"""Two OpenAPI surfaces from a single FastAPI app.

The public schema is the full schema with non-public-tagged paths
removed AND unreferenced component schemas pruned, so internal Pydantic
models (BacktestRequest, TeamInviteRequest, NotificationItem, etc.) do
not leak into the public docs even though they live in the same app.
Endpoint paths and behaviour are identical between the two schemas —
only documentation visibility differs.

Schemas are memoised on the FastAPI app instance on first build; routes
don't change after startup, so re-running the filter on every Swagger
load is wasted CPU.
"""
import json
import re

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.api.docs_config import (
    INTERNAL_API_DESCRIPTION,
    PUBLIC_API_DESCRIPTION,
    PUBLIC_TAG_METADATA,
    PUBLIC_TAGS,
)
from app.config import APP_VERSION, settings

_REF_RE = re.compile(r'"\$ref"\s*:\s*"#/components/schemas/([^"]+)"')


def get_public_openapi_schema(app: FastAPI) -> dict:
    """Memoised public OpenAPI schema — tag-filtered + schema-pruned."""
    cached = getattr(app.state, "_public_openapi_schema", None)
    if cached is not None:
        return cached
    full = get_openapi(
        title="PayPredict API",
        version=APP_VERSION,
        description=PUBLIC_API_DESCRIPTION,
        routes=app.routes,
        tags=PUBLIC_TAG_METADATA,
        servers=_servers_block(),
    )
    schema = _filter_schema_by_tags(full, PUBLIC_TAGS)
    app.state._public_openapi_schema = schema
    return schema


def get_internal_openapi_schema(app: FastAPI) -> dict:
    """Memoised internal OpenAPI schema — every endpoint included."""
    cached = getattr(app.state, "_internal_openapi_schema", None)
    if cached is not None:
        return cached
    schema = get_openapi(
        title="PayPredict Internal API",
        version=APP_VERSION,
        description=INTERNAL_API_DESCRIPTION,
        routes=app.routes,
        servers=_servers_block(),
    )
    app.state._internal_openapi_schema = schema
    return schema


def _servers_block() -> list[dict] | None:
    """Return the OpenAPI `servers` array, or None if no public URL is set.

    Declaring a servers block makes lender SDK code-generators
    (openapi-generator, Speakeasy, etc.) emit the right base URL by
    default. With `public_api_url` empty, omit the block so Swagger UI
    falls back to the current host.
    """
    if not settings.public_api_url:
        return None
    return [{"url": settings.public_api_url, "description": settings.environment}]


def _filter_schema_by_tags(schema: dict, allowed_tags: list[str]) -> dict:
    """Drop paths whose operations don't reference any of the allowed tags,
    then drop component schemas no longer reachable from the surviving
    paths so internal Pydantic models don't leak via `components.schemas`.
    """
    allowed = set(allowed_tags)

    filtered_paths: dict = {}
    for path, methods in schema.get("paths", {}).items():
        kept_methods = {
            method: op
            for method, op in methods.items()
            if any(tag in allowed for tag in op.get("tags", []))
        }
        if kept_methods:
            filtered_paths[path] = kept_methods

    out = {**schema, "paths": filtered_paths}
    if "tags" in out:
        out["tags"] = [t for t in out["tags"] if t["name"] in allowed]

    out["components"] = _prune_components(
        schema.get("components", {}),
        roots=filtered_paths,
    )
    return out


def _prune_components(components: dict, roots: dict) -> dict:
    """Walk every `$ref` reachable from `roots`, then drop component
    schemas that aren't in the reachable set.

    We serialize-and-regex rather than recursively introspecting the
    dict because $refs can appear anywhere — inside oneOf, allOf,
    properties, additionalProperties, items, etc. Regex over the JSON
    text is robust to all of those without us having to mirror the
    full OpenAPI nesting rules.
    """
    schemas = components.get("schemas", {})
    if not schemas:
        return components

    reachable: set[str] = set()
    frontier = set(_find_refs(json.dumps(roots)))
    while frontier:
        new = frontier - reachable
        if not new:
            break
        reachable |= new
        next_frontier: set[str] = set()
        for name in new:
            target = schemas.get(name)
            if target is not None:
                next_frontier |= _find_refs(json.dumps(target))
        frontier = next_frontier

    return {
        **components,
        "schemas": {name: defn for name, defn in schemas.items() if name in reachable},
    }


def _find_refs(blob: str) -> set[str]:
    """Extract every component schema name referenced inside a JSON blob."""
    return set(_REF_RE.findall(blob))
