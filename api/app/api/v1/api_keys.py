"""Dashboard API key management endpoints.

Implemented in Phase 2.5 step 6 (config). Stubs raise 501.
"""
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/config/api-keys", tags=["config"])

_NOT_IMPLEMENTED = HTTPException(
    status_code=501,
    detail="API key management endpoints land in Phase 2.5 step 6",
)


@router.get("")
async def list_api_keys() -> dict[str, str]:
    raise _NOT_IMPLEMENTED


@router.post("")
async def create_api_key() -> dict[str, str]:
    raise _NOT_IMPLEMENTED


@router.patch("/{key_id}")
async def update_api_key(key_id: str) -> dict[str, str]:
    raise _NOT_IMPLEMENTED


@router.delete("/{key_id}")
async def delete_api_key(key_id: str) -> dict[str, str]:
    raise _NOT_IMPLEMENTED
