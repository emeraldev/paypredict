"""Backtest endpoints — score historical collections and compare to actual outcomes."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, UserRole
from app.schemas.backtest import (
    BacktestListResponse,
    BacktestRequest,
    BacktestResponse,
    CsvUploadResponse,
)
from app.services.backtest_service import get_backtest, list_backtests, run_backtest
from app.services.csv_parser import parse_backtest_csv

router = APIRouter(prefix="/backtest", tags=["backtest"])

CSV_TEMPLATE = (
    "external_customer_id,external_collection_id,collection_amount,"
    "collection_currency,collection_date,collection_method,"
    "instalment_number,total_instalments,total_payments,"
    "successful_payments,card_type,card_expiry,actual_outcome,failure_reason\n"
    "cust_001,inst_001,833.33,ZAR,2025-11-15,CARD,3,6,8,5,debit,2026-09-01,FAILED,insufficient_funds\n"
    "cust_002,inst_002,500.00,ZAR,2025-11-15,DEBIT_ORDER,1,3,0,0,,,SUCCESS,\n"
    "cust_003,inst_003,250.00,ZMW,2025-11-20,MOBILE_MONEY,2,4,3,2,,,FAILED,wallet_empty\n"
)


def _require_manager_or_admin(user: User) -> User:
    if user.role not in (UserRole.ADMIN, UserRole.MANAGER):
        raise HTTPException(
            status_code=403, detail="Admin or Manager role required for backtests"
        )
    return user


@router.post("", response_model=BacktestResponse, status_code=status.HTTP_201_CREATED)
async def create_backtest(
    body: BacktestRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BacktestResponse:
    """Run a backtest on a batch of historical collections (max 500, sync)."""
    _require_manager_or_admin(user)
    result = await run_backtest(db, user.tenant, body.collections, name=body.name)
    await db.commit()
    return result


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_csv(
    file: UploadFile,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BacktestResponse | CsvUploadResponse:
    """Upload a CSV of historical collections for backtesting."""
    _require_manager_or_admin(user)

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400, detail="File must be a .csv file"
        )

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    items, errors = parse_backtest_csv(content)

    if errors:
        return CsvUploadResponse(errors=errors)

    if len(items) > 500:
        raise HTTPException(
            status_code=400,
            detail=f"CSV contains {len(items)} rows (max 500). Reduce the file size.",
        )

    if not items:
        raise HTTPException(status_code=400, detail="CSV contains no valid rows")

    result = await run_backtest(db, user.tenant, items)
    await db.commit()
    return result


@router.get("/template")
async def download_template() -> StreamingResponse:
    """Download a CSV template with correct headers and example rows."""
    return StreamingResponse(
        iter([CSV_TEMPLATE]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=backtest_template.csv"},
    )


@router.get("s", response_model=BacktestListResponse)
async def list_all(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BacktestListResponse:
    """List all backtest runs for the tenant."""
    return await list_backtests(db, user.tenant_id)


@router.get("/{backtest_id}", response_model=BacktestResponse)
async def get_one(
    backtest_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BacktestResponse:
    """Get a backtest run by ID."""
    result = await get_backtest(db, user.tenant_id, backtest_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Backtest not found")
    return result
