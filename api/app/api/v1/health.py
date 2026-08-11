from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/detailed")
async def health_check_detailed(
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    # Check database connectivity
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"

    # Report schema version + expected head. External monitoring can
    # alert on any drift, even though the startup check refuses to boot
    # a mismatched DB — belt and braces.
    from app.startup_checks import current_db_version, expected_head

    try:
        db_version = await current_db_version(db.bind)  # type: ignore[arg-type]
        code_head = expected_head()
        schema_status = "ok" if db_version == code_head else "mismatch"
    except Exception:
        db_version = None
        code_head = None
        schema_status = "unknown"

    overall = "ok"
    if db_status != "ok" or schema_status != "ok":
        overall = "degraded"

    return {
        "status": overall,
        "database": db_status,
        "schema": schema_status,
        "schema_version": db_version or "unknown",
        "schema_expected": code_head or "unknown",
    }
