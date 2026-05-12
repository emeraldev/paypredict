"""Two OpenAPI surfaces from a single FastAPI app.

The public schema is the full schema with non-public-tagged paths
removed. Endpoint paths and behaviour are identical between the two
schemas — only documentation visibility differs.
"""
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.api.docs_config import (
    INTERNAL_API_DESCRIPTION,
    PUBLIC_API_DESCRIPTION,
    PUBLIC_TAG_METADATA,
    PUBLIC_TAGS,
)


def get_public_openapi_schema(app: FastAPI) -> dict:
    """OpenAPI schema with only the public-tagged endpoints."""
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
    """Drop paths whose operations don't reference any of the allowed tags."""
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
    return out
