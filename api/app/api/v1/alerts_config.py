"""Dashboard alert configuration endpoints.

Implemented in Phase 2.5 step 6 (config). Stubs raise 501.
"""
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/config/alerts", tags=["config"])

_NOT_IMPLEMENTED = HTTPException(
    status_code=501,
    detail="Alert config endpoints land in Phase 2.5 step 6",
)


@router.get("")
async def get_alerts_config() -> dict[str, str]:
    raise _NOT_IMPLEMENTED


@router.put("")
async def update_alerts_config() -> dict[str, str]:
    raise _NOT_IMPLEMENTED
