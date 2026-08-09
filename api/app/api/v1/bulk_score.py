"""Bulk scoring endpoints — score multiple collections in one call."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.docs_config import LENDER_API_RESPONSES
from app.database import get_db
from app.dependencies import enforce_rate_limit
from app.models.tenant import Tenant
from app.schemas.bulk_score import BulkScoreRequest
from app.services.bulk_scoring_service import (
    SYNC_THRESHOLD,
    get_job_status,
    queue_bulk_job,
    score_bulk_sync,
)
from app.services.weights_service import load_all_weights_by_method

router = APIRouter(tags=["Scoring"], responses=LENDER_API_RESPONSES)


@router.post("/score/bulk")
async def score_bulk(
    body: BulkScoreRequest,
    tenant: Tenant = Depends(enforce_rate_limit),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Score a batch of collections.

    <= 50 items: processed synchronously, results returned inline.
    > 50 items: queued to Celery, returns job_id for polling.
    """
    # Convert Pydantic models to dicts — keep date objects for the scoring engine
    collections = [
        item.model_dump(mode="python") for item in body.collections
    ]

    if len(collections) <= SYNC_THRESHOLD:
        result = await score_bulk_sync(db, tenant, collections)
        await db.commit()
        return result

    # Async path: queue to Celery
    weights_by_method = await load_all_weights_by_method(db, tenant.id)
    return queue_bulk_job(
        tenant_id=str(tenant.id),
        collections=collections,
        weights_by_method=weights_by_method,
    )


@router.get("/score/bulk/{job_id}")
async def poll_bulk_job(
    job_id: str,
    tenant: Tenant = Depends(enforce_rate_limit),
) -> dict:
    """Poll the status of an async bulk scoring job."""
    result = get_job_status(job_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Job not found or expired")
    return result
