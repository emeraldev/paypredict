"""Shared Pydantic field validators.

Currently one thing: `validate_opaque_id`, used on every lender-
facing `customer_id` / `collection_id` field so obvious PII shapes
(emails, whitespace-separated names, formatted phone numbers)
never land in `score_requests.external_customer_id`.
"""
from __future__ import annotations

import re

# URL-safe opaque token. Naturally forbids:
# - whitespace (names, addresses)
# - `@` (emails)
# - `+` `(` `)` (formatted phone numbers)
# - `,` `;` (CSV-shaped junk)
# - length > 128 (paragraphs, dumped documents)
#
# Length floor of 1 rejects the empty string (would otherwise slip
# through — pydantic doesn't reject empty strings by default).
OPAQUE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_\-.:]{1,128}$")


def validate_opaque_id(value: str) -> str:
    """Reject the most common PII shapes in customer/collection ids.

    Accepts URL-safe opaque tokens: UUIDs (`550e8400-...`), internal
    DB ids (`500000123`), prefixed strings (`EMP_ROSE_001`,
    `cust.sa.001`, `col:2026:08:13`). Length capped at 128 chars.

    Purely numeric IDs pass on purpose — some lenders' internal
    customer numbers look like `500000123` and it's not our call to
    decide whether that's a phone number in disguise. Our contract
    is to reject the OBVIOUSLY unsafe shapes (emails, names, phone
    numbers with formatting) and document the recommended shape in
    the public API description.

    Raises ValueError on rejection so Pydantic surfaces it as a
    422 with a clear message.
    """
    if not OPAQUE_ID_PATTERN.fullmatch(value):
        raise ValueError(
            "must be an opaque URL-safe token (1-128 characters, "
            "letters / digits / _ / - / . / : only). Personal data "
            "(names, emails, phone numbers, national IDs) is not "
            "accepted — hash or replace with an internal reference."
        )
    return value
