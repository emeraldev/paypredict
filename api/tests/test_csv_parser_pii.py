"""CSV parser must surface PII validation errors per-row.

Unlike the JSON bulk endpoint (which fails the whole batch on a single
validation error), the CSV parser has a per-row try/except that
attaches errors to the parser's `CsvValidationError` list. That means
one PII row in a 500-row upload lands the bad row in the errors list;
the other 499 parse cleanly.
"""
from __future__ import annotations

import pytest

from app.services.csv_parser import parse_backtest_csv, parse_scoring_csv


BACKTEST_HEADER = (
    "customer_id,collection_id,collection_amount,collection_currency,"
    "collection_date,collection_method,actual_outcome"
)

SCORING_HEADER = (
    "customer_id,collection_id,collection_amount,collection_currency,"
    "collection_due_date,collection_method"
)


def _rows(header: str, *rows: str) -> bytes:
    """Assemble a CSV body from a header + row strings."""
    return ("\n".join([header, *rows])).encode("utf-8")


def test_backtest_csv_flags_pii_customer_id_per_row():
    """One PII row + one clean row → 1 error, 1 parsed input."""
    csv = _rows(
        BACKTEST_HEADER,
        "cust_valid_001,col_001,1500,ZAR,2026-04-15,CARD,SUCCESS",
        "jane@example.com,col_002,1500,ZAR,2026-04-15,CARD,FAILED",
    )
    items, errors = parse_backtest_csv(csv)
    assert len(items) == 1
    assert items[0].customer_id == "cust_valid_001"
    # The bad row's error names the field.
    assert len(errors) == 1
    assert "customer_id" in str(errors[0]).lower() or "opaque" in str(errors[0]).lower()


def test_scoring_csv_flags_pii_customer_id_per_row():
    """Same behaviour on the scoring-upload CSV path."""
    csv = _rows(
        SCORING_HEADER,
        "cust_valid_001,col_001,1500,ZAR,2026-04-15,CARD",
        "+27 82 555 1234,col_002,1500,ZAR,2026-04-15,CARD",
    )
    items, errors = parse_scoring_csv(csv)
    assert len(items) == 1
    assert len(errors) == 1


def test_backtest_csv_flags_overlong_customer_id():
    csv = _rows(
        BACKTEST_HEADER,
        f"{'a' * 200},col_001,1500,ZAR,2026-04-15,CARD,SUCCESS",
    )
    items, errors = parse_backtest_csv(csv)
    assert len(items) == 0
    assert len(errors) == 1
