"""Dashboard outcomes list endpoint.

Implemented in Phase 2.5 step 4 (outcomes list). Stub raises 501.
"""
from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["outcomes"])

_NOT_IMPLEMENTED = HTTPException(
    status_code=501,
    detail="Outcomes list endpoint lands in Phase 2.5 step 4",
)


@router.get("/outcomes")
async def list_outcomes() -> dict[str, str]:
    raise _NOT_IMPLEMENTED
