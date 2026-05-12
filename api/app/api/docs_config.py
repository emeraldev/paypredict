"""Tag definitions and human-readable copy for the public + internal docs.

The set of tags here drives which endpoints appear in the public Swagger
UI at `/docs`. Anything tagged with a value in `PUBLIC_TAGS` is exposed
to lenders; everything else is internal (visible only at
`/docs/internal`, which is disabled in production).

When you add a new endpoint, set its `tags=[...]` value to one of the
strings below — that's the only place the public/internal decision is
made.
"""

PUBLIC_TAGS = [
    "Scoring",
    "Outcomes",
    "Analytics",
    "Configuration",
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
        "name": "Health",
        "description": "API health check endpoints.",
    },
]
