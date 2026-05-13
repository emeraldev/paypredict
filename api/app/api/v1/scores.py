from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.docs_config import LENDER_API_RESPONSES
from app.dependencies import enforce_rate_limit
from app.models.tenant import Tenant
from app.schemas.score import ScoreRequest, ScoreResponse
from app.services.scoring_service import score_collection

router = APIRouter(tags=["Scoring"], responses=LENDER_API_RESPONSES)


@router.post("/score", response_model=ScoreResponse)
async def score_single_collection(
    request: ScoreRequest,
    tenant: Tenant = Depends(enforce_rate_limit),
    db: AsyncSession = Depends(get_db),
) -> ScoreResponse:
    """Score a single upcoming collection. Returns risk score, level, and factor breakdown."""
    return await score_collection(request, tenant, db)
