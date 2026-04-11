"""Reusable query patterns for dashboard endpoints.

Pagination, period filtering, and aggregate helpers shared across the
scores list, outcomes list, analytics, and config services. Anything that
multiple services would otherwise duplicate lives here.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel
from sqlalchemy import Select, func
from sqlalchemy.ext.asyncio import AsyncSession

# Hard cap on page_size to prevent expensive scans.
MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 25


class PaginationMeta(BaseModel):
    """Pagination metadata returned by every list endpoint."""

    page: int
    page_size: int
    total_items: int
    total_pages: int


def clamp_page_size(page_size: int) -> int:
    """Clamp page_size into [1, MAX_PAGE_SIZE]."""
    if page_size < 1:
        return 1
    if page_size > MAX_PAGE_SIZE:
        return MAX_PAGE_SIZE
    return page_size


async def paginate(
    db: AsyncSession,
    query: Select[Any],
    page: int,
    page_size: int,
) -> tuple[list[Any], PaginationMeta]:
    """Run a paginated SELECT and return rows + pagination metadata.

    The query is executed twice: once wrapped in COUNT(*) for the total,
    once with LIMIT/OFFSET applied for the page. Always uses subqueries
    so JOINs and filters are preserved across both runs.
    """
    page = max(page, 1)
    page_size = clamp_page_size(page_size)

    count_query = func.count().select().select_from(query.subquery())
    total_items: int = (await db.execute(count_query)).scalar_one()

    total_pages = max(1, (total_items + page_size - 1) // page_size)

    paged = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(paged)
    rows = list(result.all())

    return rows, PaginationMeta(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
    )


# Supported period strings for analytics endpoints.
_PERIOD_DAYS: dict[str, int] = {
    "7d": 7,
    "14d": 14,
    "30d": 30,
    "60d": 60,
    "90d": 90,
}


def parse_period(period: str) -> timedelta:
    """Convert '7d'/'30d'/'90d' into a timedelta. Raises ValueError on unknown."""
    if period not in _PERIOD_DAYS:
        raise ValueError(
            f"Unsupported period '{period}'. "
            f"Supported: {sorted(_PERIOD_DAYS.keys())}"
        )
    return timedelta(days=_PERIOD_DAYS[period])


def period_start(period: str, now: datetime | None = None) -> datetime:
    """Return the UTC datetime that marks the start of the period."""
    base = now or datetime.now(timezone.utc)
    return base - parse_period(period)
