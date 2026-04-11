"""Dashboard session auth endpoints.

Implemented in Phase 2 of the dashboard-endpoints branch. Stubs raise 501.
"""
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/auth", tags=["auth"])

_NOT_IMPLEMENTED = HTTPException(
    status_code=501,
    detail="Auth endpoints land in Phase 2.5 step 2 (auth implementation)",
)


@router.post("/login")
async def login() -> dict[str, str]:
    raise _NOT_IMPLEMENTED


@router.get("/me")
async def me() -> dict[str, str]:
    raise _NOT_IMPLEMENTED


@router.post("/logout")
async def logout() -> dict[str, str]:
    raise _NOT_IMPLEMENTED
