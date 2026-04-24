"""Bulk scoring endpoints — score multiple collections in one call."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_tenant
from app.models.tenant import Tenant
from app.schemas.bulk_score import BulkScoreRequest
from app.services.bulk_scoring_service import (
    SYNC_THRESHOLD,
    get_job_status,
    queue_bulk_job,
    score_bulk_sync,
    _load_weights,
)

router = APIRouter(tags=["scoring"])


@router.post("/score/bulk")
async def score_bulk(
    body: BulkScoreRequest,
    tenant: Tenant = Depends(get_current_tenant),
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
    weights = await _load_weights(db, tenant.id)
    return queue_bulk_job(
        tenant_id=str(tenant.id),
        factor_set=tenant.factor_set.value,
        collections=collections,
        weights=weights,
    )


@router.get("/score/bulk/{job_id}")
async def poll_bulk_job(
    job_id: str,
    tenant: Tenant = Depends(get_current_tenant),
) -> dict:
    """Poll the status of an async bulk scoring job."""
    result = get_job_status(job_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Job not found or expired")
    return result
