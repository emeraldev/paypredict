"""Dashboard team management endpoints (admin-only).

Implemented in Phase 2.5 step 6 (config). Stubs raise 501.
"""
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/config/team", tags=["config"])

_NOT_IMPLEMENTED = HTTPException(
    status_code=501,
    detail="Team management endpoints land in Phase 2.5 step 6",
)


@router.get("")
async def list_team() -> dict[str, str]:
    raise _NOT_IMPLEMENTED


@router.post("")
async def invite_member() -> dict[str, str]:
    raise _NOT_IMPLEMENTED


@router.patch("/{user_id}")
async def update_member(user_id: str) -> dict[str, str]:
    raise _NOT_IMPLEMENTED


@router.delete("/{user_id}")
async def remove_member(user_id: str) -> dict[str, str]:
    raise _NOT_IMPLEMENTED
