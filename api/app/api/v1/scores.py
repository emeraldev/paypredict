from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_tenant
from app.models.tenant import Tenant
from app.schemas.score import ScoreRequest, ScoreResponse
from app.services.scoring_service import score_collection

router = APIRouter(tags=["scoring"])


@router.post("/score", response_model=ScoreResponse)
async def score_single_collection(
    request: ScoreRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> ScoreResponse:
    """Score a single upcoming collection. Returns risk score, level, and factor breakdown."""
    return await score_collection(request, tenant, db)
