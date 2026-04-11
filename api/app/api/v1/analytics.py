"""Dashboard analytics endpoints.

Implemented in Phase 2.5 step 5 (analytics). Stubs raise 501.
"""
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/analytics", tags=["analytics"])

_NOT_IMPLEMENTED = HTTPException(
    status_code=501,
    detail="Analytics endpoints land in Phase 2.5 step 5",
)


@router.get("/summary")
async def summary() -> dict[str, str]:
    raise _NOT_IMPLEMENTED


@router.get("/collection-rate")
async def collection_rate() -> dict[str, str]:
    raise _NOT_IMPLEMENTED


@router.get("/factors")
async def factors() -> dict[str, str]:
    raise _NOT_IMPLEMENTED


@router.get("/accuracy")
async def accuracy() -> dict[str, str]:
    raise _NOT_IMPLEMENTED
