"""Tag definitions and human-readable copy for the public + internal docs.

The set of tags here drives which endpoints appear in the public Swagger
UI at `/docs`. Anything tagged with a value in `PUBLIC_TAGS` is exposed
to lenders; everything else is internal (visible only at
`/docs/internal`, which is disabled in production).

When you add a new endpoint, set its `tags=[...]` value to one of the
strings below — that's the only place the public/internal decision is
made.

`Webhooks` is a description-only tag (no operations reference it). It
exists so the public Swagger UI carries the signature-verification
guide lenders need to consume outbound webhooks.
"""

from app.schemas.errors import HTTPError


PUBLIC_TAGS = [
    "Scoring",
    "Outcomes",
    "Analytics",
    "Configuration",
    "Webhooks",
    "Health",
]

INTERNAL_TAGS = [
    "Auth",
    "Dashboard Scores",
    "Dashboard Outcomes",
    "Notifications",
    "Backtest",
    "API Keys",
    "Team",
    "Alert Settings",
    "Alerts (legacy)",
]

ALL_TAGS = PUBLIC_TAGS + INTERNAL_TAGS


PUBLIC_API_DESCRIPTION = """\
## Pre-collection risk scoring for instalment lenders

Score upcoming collections before attempting payment. Predict failures,
report outcomes to refine the model, and surface analytics for your
portfolio.

### Authentication

All endpoints require an API key in the Authorization header:

```
Authorization: Bearer pk_live_your_key_here
```

Use `pk_test_` prefixed keys for sandbox / integration testing.

### Quick start

1. Get an API key from your PayPredict dashboard.
2. Send a collection to `POST /v1/score` with customer + collection data.
3. Use the returned risk score to prioritise your collections.
4. Report outcomes via `POST /v1/outcomes` to improve accuracy over time.
"""

INTERNAL_API_DESCRIPTION = """\
## PayPredict Internal API

All endpoints — public and dashboard-only. Disabled in production.
"""


PUBLIC_TAG_METADATA = [
    {
        "name": "Scoring",
        "description": (
            "Score upcoming collections by risk of failure. Send customer and "
            "collection data, receive a risk score with factor breakdown and "
            "recommended action. Supports single (`POST /v1/score`) and bulk "
            "(`POST /v1/score/bulk`) modes."
        ),
    },
    {
        "name": "Outcomes",
        "description": (
            "Report collection outcomes (success / failure) back to "
            "PayPredict. This is what builds the labelled dataset used to "
            "improve prediction accuracy over time."
        ),
    },
    {
        "name": "Analytics",
        "description": (
            "Collection rate trends, prediction accuracy, risk distribution, "
            "and factor contribution analytics for your portfolio."
        ),
    },
    {
        "name": "Configuration",
        "description": (
            "Read and update scoring factor weights. Weights control how "
            "much each risk factor contributes to the final score."
        ),
    },
    {
        "name": "Webhooks",
        "description": """\
PayPredict POSTs signed webhooks to the URL you configure in the
dashboard's Alert Settings. Use them to react to high-risk batches and
async events without polling.

### Headers on every delivery

| Header | Description |
|---|---|
| `X-PayPredict-Event` | Event name (e.g. `high_risk_alert`). |
| `X-PayPredict-Signature` | `sha256=<hex>` HMAC of the raw request body, computed with your tenant's webhook secret. |
| `X-PayPredict-Delivery` | UUID — unique per attempt (3 retries with exponential backoff). |
| `Content-Type` | `application/json`. |

### Verify the signature (Python)

```python
import hmac, hashlib

def verify(body: bytes, header: str, secret: str) -> bool:
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", header)
```

### Verify the signature (Node)

```js
const crypto = require("crypto");

function verify(body, header, secret) {
  const expected = "sha256=" + crypto
    .createHmac("sha256", secret)
    .update(body)
    .digest("hex");
  return crypto.timingSafeEqual(Buffer.from(expected), Buffer.from(header));
}
```

Use the **raw** request body before any JSON parsing — re-serialising
changes whitespace and breaks the signature.

### Rotate the secret

If a secret is compromised, rotate it from the dashboard's Alert
Settings page. The previous value is invalidated immediately, so any
in-flight retries signed with the old secret will fail verification.
""",
    },
    {
        "name": "Health",
        "description": "API health check endpoints. No authentication required.",
    },
]


# ---- Standard error responses (documented on every protected route) ----

_RATE_LIMIT_HEADERS = {
    "Retry-After": {
        "description": "Seconds to wait before retrying.",
        "schema": {"type": "integer"},
    },
    "X-RateLimit-Limit": {
        "description": "Requests allowed in the current window for this API key tier.",
        "schema": {"type": "integer"},
    },
    "X-RateLimit-Remaining": {
        "description": "Requests remaining in the current window.",
        "schema": {"type": "integer"},
    },
    "X-RateLimit-Reset": {
        "description": "Unix timestamp when the current window resets.",
        "schema": {"type": "integer"},
    },
}


AUTH_RESPONSES: dict = {
    401: {"model": HTTPError, "description": "Missing or invalid credentials."},
}

ADMIN_RESPONSES: dict = {
    **AUTH_RESPONSES,
    403: {"model": HTTPError, "description": "Admin role required."},
}

NOT_FOUND_RESPONSES: dict = {
    404: {"model": HTTPError, "description": "Resource not found."},
}

RATE_LIMIT_RESPONSES: dict = {
    429: {
        "model": HTTPError,
        "description": (
            "Rate limit exceeded for your API-key tier. Inspect `Retry-After` "
            "and the `X-RateLimit-*` response headers to back off correctly."
        ),
        "headers": _RATE_LIMIT_HEADERS,
    },
}


# Lender-facing API-key routes: auth + rate-limit applies to every operation.
LENDER_API_RESPONSES: dict = {**AUTH_RESPONSES, **RATE_LIMIT_RESPONSES}

# Dashboard JWT routes: auth applies; rate limit is dashboard-side only.
DASHBOARD_API_RESPONSES: dict = {**AUTH_RESPONSES}

# Admin-only dashboard routes (team management).
DASHBOARD_ADMIN_RESPONSES: dict = {**ADMIN_RESPONSES}
