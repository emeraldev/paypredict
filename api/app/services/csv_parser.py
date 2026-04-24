"""CSV parser for backtest uploads.

Parses lender-exported CSVs into BacktestCollectionInput objects.
Handles BOM characters (Excel exports), empty rows, and provides
row-level validation errors.
"""
from __future__ import annotations

import csv
import io
from datetime import date
from decimal import Decimal, InvalidOperation

from app.schemas.backtest import (
    BacktestCollectionInput,
    BacktestCustomerData,
    CsvValidationError,
)

REQUIRED_COLUMNS = {
    "external_customer_id",
    "external_collection_id",
    "collection_amount",
    "collection_currency",
    "collection_date",
    "collection_method",
    "actual_outcome",
}

VALID_CURRENCIES = {"ZAR", "ZMW"}
VALID_METHODS = {"CARD", "DEBIT_ORDER", "MOBILE_MONEY"}
VALID_OUTCOMES = {"SUCCESS", "FAILED"}


def parse_backtest_csv(
    file_content: bytes,
) -> tuple[list[BacktestCollectionInput], list[CsvValidationError]]:
    """Parse CSV bytes into validated backtest inputs.

    Returns (valid_items, errors). If errors is non-empty, the caller
    should return them to the user and not proceed with the backtest.
    """
    # Handle BOM from Excel exports
    text = file_content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    if reader.fieldnames is None:
        return [], [CsvValidationError(row=0, field="", message="Empty CSV file")]

    # Normalize headers (strip whitespace, lowercase)
    headers = {h.strip().lower() for h in reader.fieldnames}

    missing = REQUIRED_COLUMNS - headers
    if missing:
        return [], [
            CsvValidationError(
                row=0,
                field=col,
                message=f"Missing required column: {col}",
            )
            for col in sorted(missing)
        ]

    items: list[BacktestCollectionInput] = []
    errors: list[CsvValidationError] = []

    for row_num, raw_row in enumerate(reader, start=2):  # row 1 = headers
        # Normalize keys
        row = {k.strip().lower(): (v.strip() if v else "") for k, v in raw_row.items()}

        # Skip fully empty rows
        if all(not v for v in row.values()):
            continue

        row_errors = _validate_row(row_num, row)
        if row_errors:
            errors.extend(row_errors)
            continue

        try:
            item = _row_to_input(row)
            items.append(item)
        except Exception as exc:
            errors.append(
                CsvValidationError(row=row_num, field="", message=str(exc))
            )

    return items, errors


def _validate_row(row_num: int, row: dict[str, str]) -> list[CsvValidationError]:
    errs: list[CsvValidationError] = []

    for col in REQUIRED_COLUMNS:
        if not row.get(col):
            errs.append(CsvValidationError(row=row_num, field=col, message=f"Missing {col}"))

    if row.get("collection_currency", "").upper() not in VALID_CURRENCIES and not any(
        e.field == "collection_currency" for e in errs
    ):
        errs.append(
            CsvValidationError(
                row=row_num,
                field="collection_currency",
                message=f"Invalid currency: {row['collection_currency']}. Must be ZAR or ZMW",
            )
        )

    if row.get("collection_method", "").upper() not in VALID_METHODS and not any(
        e.field == "collection_method" for e in errs
    ):
        errs.append(
            CsvValidationError(
                row=row_num,
                field="collection_method",
                message=f"Invalid method: {row['collection_method']}. Must be CARD, DEBIT_ORDER, or MOBILE_MONEY",
            )
        )

    if row.get("actual_outcome", "").upper() not in VALID_OUTCOMES and not any(
        e.field == "actual_outcome" for e in errs
    ):
        errs.append(
            CsvValidationError(
                row=row_num,
                field="actual_outcome",
                message=f"Invalid outcome: {row['actual_outcome']}. Must be SUCCESS or FAILED",
            )
        )

    amt = row.get("collection_amount", "")
    if amt:
        try:
            val = Decimal(amt)
            if val <= 0:
                errs.append(
                    CsvValidationError(
                        row=row_num, field="collection_amount", message="Amount must be > 0"
                    )
                )
        except InvalidOperation:
            errs.append(
                CsvValidationError(
                    row=row_num, field="collection_amount", message=f"Invalid number: {amt}"
                )
            )

    dt = row.get("collection_date", "")
    if dt:
        try:
            date.fromisoformat(dt)
        except ValueError:
            errs.append(
                CsvValidationError(
                    row=row_num,
                    field="collection_date",
                    message=f"Invalid date: {dt}. Use YYYY-MM-DD format",
                )
            )

    return errs


def _row_to_input(row: dict[str, str]) -> BacktestCollectionInput:
    """Convert a validated CSV row dict to a BacktestCollectionInput."""

    def _int_or_none(val: str) -> int | None:
        return int(val) if val else None

    def _decimal_or_none(val: str) -> Decimal | None:
        return Decimal(val) if val else None

    customer_data = BacktestCustomerData(
        total_payments=int(row.get("total_payments", "0") or "0"),
        successful_payments=int(row.get("successful_payments", "0") or "0"),
        instalment_number=_int_or_none(row.get("instalment_number", "")),
        total_instalments=_int_or_none(row.get("total_instalments", "")),
        card_type=row.get("card_type") or None,
        card_expiry_date=(
            date.fromisoformat(row["card_expiry"])
            if row.get("card_expiry")
            else None
        ),
    )

    return BacktestCollectionInput(
        external_customer_id=row["external_customer_id"],
        external_collection_id=row["external_collection_id"],
        collection_amount=Decimal(row["collection_amount"]),
        collection_currency=row["collection_currency"].upper(),
        collection_date=date.fromisoformat(row["collection_date"]),
        collection_method=row["collection_method"].upper(),
        customer_data=customer_data,
        actual_outcome=row["actual_outcome"].upper(),
        failure_reason=row.get("failure_reason") or None,
    )
