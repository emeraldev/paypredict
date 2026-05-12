"""Two OpenAPI surfaces from a single FastAPI app.

The public schema is the full schema with non-public-tagged paths
removed AND unreferenced component schemas pruned, so internal Pydantic
models (BacktestRequest, TeamInviteRequest, NotificationItem, etc.) do
not leak into the public docs even though they live in the same app.
Endpoint paths and behaviour are identical between the two schemas —
only documentation visibility differs.
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

_REF_RE = re.compile(r'"\$ref"\s*:\s*"#/components/schemas/([^"]+)"')


def get_public_openapi_schema(app: FastAPI) -> dict:
    """OpenAPI schema with only the public-tagged endpoints and only the
    component schemas those endpoints actually reference."""
    full = get_openapi(
        title="PayPredict API",
        version="1.0.0",
        description=PUBLIC_API_DESCRIPTION,
        routes=app.routes,
        tags=PUBLIC_TAG_METADATA,
    )
    return _filter_schema_by_tags(full, PUBLIC_TAGS)


def get_internal_openapi_schema(app: FastAPI) -> dict:
    """OpenAPI schema with every endpoint included — dev/dashboard view."""
    return get_openapi(
        title="PayPredict Internal API",
        version="1.0.0",
        description=INTERNAL_API_DESCRIPTION,
        routes=app.routes,
    )


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
