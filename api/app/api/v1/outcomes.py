from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.docs_config import LENDER_API_RESPONSES
from app.database import get_db
from app.dependencies import enforce_rate_limit
from app.models.tenant import Tenant
from app.schemas.outcome import OutcomeRequest, OutcomeResponse
from app.services.outcome_service import record_outcome

router = APIRouter(tags=["Outcomes"], responses=LENDER_API_RESPONSES)


@router.post(
    "/outcomes",
    response_model=OutcomeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def report_outcome(
    request: OutcomeRequest,
    tenant: Tenant = Depends(enforce_rate_limit),
    db: AsyncSession = Depends(get_db),
) -> OutcomeResponse:
    """Report the result of a collection attempt."""
    return await record_outcome(request, tenant, db)
