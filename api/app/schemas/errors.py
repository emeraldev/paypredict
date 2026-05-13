"""Shared error response models for OpenAPI documentation.

Every protected endpoint declares these in its `responses=` block so the
public Swagger UI shows lender SDKs exactly what shape to expect for
401/403/404/422/429. The runtime body comes from FastAPI's
`HTTPException(detail=...)` — the schema below matches that.
"""
from pydantic import BaseModel, Field


class HTTPError(BaseModel):
    """Standard FastAPI error envelope."""

    detail: str = Field(..., examples=["Invalid API key"])
