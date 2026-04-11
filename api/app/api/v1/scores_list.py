"""Dashboard scores list + detail endpoints.

Implemented in Phase 2.5 step 3 (scores list/detail). Stubs raise 501.
"""
from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["scores"])

_NOT_IMPLEMENTED = HTTPException(
    status_code=501,
    detail="Scores list/detail endpoints land in Phase 2.5 step 3",
)


@router.get("/scores")
async def list_scores() -> dict[str, str]:
    raise _NOT_IMPLEMENTED


@router.get("/scores/{score_id}")
async def get_score(score_id: str) -> dict[str, str]:
    raise _NOT_IMPLEMENTED
