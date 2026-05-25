# PayPredict — API Reference

## Authentication

All API endpoints require an API key in the Authorization header:

```
Authorization: Bearer pk_live_abc123def456...
```

API keys are scoped to a tenant. The key determines which tenant's data and factor configuration to use. Keys are hashed at rest — once generated, the raw key cannot be retrieved again.

Key prefixes:
- `pk_live_` — production keys
- `pk_test_` — sandbox/test keys (against test data, no billing)

---

## Endpoints

### Score a single collection

```
POST /v1/score
```

Score one upcoming collection. Synchronous — returns immediately (~15ms).

**Request body:**

```json
{
  "customer_id": "string, required",
  "collection_id": "string, required",
  "collection_amount": "decimal, required",
  "collection_currency": "enum: ZAR | ZMW, required",
  "collection_due_date": "date (YYYY-MM-DD), required",
  "collection_method": "enum: CARD | DEBIT_ORDER | MOBILE_MONEY, required",
  "customer_data": {
    // --- Common fields (all factor sets) ---
    "total_payments": "integer, optional (default 0)",
    "successful_payments": "integer, optional (default 0)",
    "last_successful_payment_date": "date, optional",
    "average_collection_amount": "decimal, optional",
    "instalment_number": "integer, optional",
    "total_instalments": "integer, optional",

    // --- CARD_DEBIT fields ---
    "card_type": "string: credit | debit, optional",
    "card_expiry_date": "date, optional",
    "last_decline_code": "string, optional",
    "debit_order_returns": "array of strings, optional",
    "known_salary_day": "integer (1-31), optional",

    // --- MOBILE_WALLET fields ---
    "wallet_balance_7d_avg": "decimal, optional",
    "wallet_balance_current": "decimal, optional",
    "hours_since_last_inflow": "integer, optional",
    "regular_inflow_day": "string: monday-sunday, optional",
    "active_loan_count": "integer, optional",
    "transactions_last_7d": "integer, optional",
    "transactions_avg_7d": "integer, optional",
    "last_airtime_purchase_days_ago": "integer, optional",
    "new_loan_within_repayment_period": "boolean, optional",
    "loans_taken_last_90d": "integer, optional"
  }
}
```

**Response (200):**

```json
{
  "score_id": "sr_uuid",
  "score": 0.68,
  "risk_level": "HIGH",
  "recommended_action": "shift_date",
  "recommended_collection_date": "2026-04-25",
  "recommended_score": 0.51,
  "score_improvement": 0.17,
  "factors": [
    {
      "factor": "historical_failure_rate",
      "raw_score": 0.375,
      "weight": 0.25,
      "weighted_score": 0.094,
      "explanation": "37.5% of past collections have failed"
    }
  ],
  "model_version": "heuristic_card_v1",
  "scored_at": "2026-04-08T14:23:01Z",
  "scoring_duration_ms": 32
}
```

**Notes:**
- All customer_data fields are optional. Missing data results in moderate default scores for affected factors (typically 0.3-0.5). More data = more accurate scores.
- The engine automatically selects the correct factor set based on the tenant's `factor_set` configuration (CARD_DEBIT or MOBILE_WALLET). Card fields are ignored for wallet tenants and vice versa.
- `recommended_action` values: `collect_normally`, `shift_date`, `flag_for_review`, `pre_collection_sms`

### Timing optimiser

Every score also runs through a timing search across ±14 days around the supplied `collection_due_date`. When the search finds a strictly better date and the predicted improvement is at least **0.10**, the response carries:

- `recommended_action: "shift_date"` (overrides the risk-level action)
- `recommended_collection_date` — the optimal date (never in the past)
- `recommended_score` — what the score would be if collected on that date
- `score_improvement` — how much risk drops (`score` − `recommended_score`)

When no shift is worthwhile, all three fields are `null` and `recommended_action` falls back to the risk-level mapping. The bulk endpoint applies the same optimiser per item.

Latency budget grows from ~1ms to ~30ms per request (28 extra factor evaluations); bulk-of-50 sync stays well under 2s.

---

### Score a batch (async)

```
POST /v1/score/bulk
```

Score multiple collections. Returns a job_id immediately. Results delivered via webhook or polling.

**Request body:**

```json
{
  "collections": [
    {
      "customer_id": "cust_001",
      "collection_id": "inst_001",
      "collection_amount": 500.00,
      "collection_currency": "ZAR",
      "collection_due_date": "2026-04-15",
      "collection_method": "CARD",
      "customer_data": { ... }
    },
    { ... }
  ]
}
```

**Response (202 Accepted):**

```json
{
  "job_id": "job_uuid",
  "total_items": 150,
  "status": "processing",
  "estimated_completion_seconds": 15
}
```

**Limits:** Max 1,000 collections per batch. For larger batches, split into multiple requests.

---

### Poll bulk results

```
GET /v1/score/bulk/{job_id}
```

**Response (200):**

```json
{
  "job_id": "job_uuid",
  "status": "completed",
  "total_items": 150,
  "completed_items": 150,
  "summary": {
    "high_risk": 12,
    "medium_risk": 45,
    "low_risk": 93,
    "total_value_at_risk": 28500.00
  },
  "results": [
    {
      "score_id": "sr_uuid",
      "collection_id": "inst_001",
      "score": 0.72,
      "risk_level": "HIGH",
      "recommended_action": "flag_for_review"
    }
  ]
}
```

Status values: `processing`, `completed`, `failed`

---

### Report outcome

```
POST /v1/outcomes
```

Report the result of a collection attempt. This is critical — it builds the labelled dataset for improving accuracy and future ML training.

**Request body:**

```json
{
  "score_id": "sr_uuid (optional — links to our score if we scored it)",
  "collection_id": "string, required",
  "outcome": "enum: SUCCESS | FAILED, required",
  "failure_reason": "string, optional (e.g. insufficient_funds, card_expired, wallet_empty)",
  "amount_collected": "decimal, optional (for partial collections)",
  "attempted_at": "datetime, required"
}
```

**Response (201):**

```json
{
  "outcome_id": "out_uuid",
  "linked_score_id": "sr_uuid or null",
  "received_at": "2026-04-15T09:00:01Z"
}
```

---

### Report outcomes in batch

```
POST /v1/outcomes/bulk
```

**Request body:**

```json
{
  "outcomes": [
    {
      "score_id": "sr_uuid",
      "collection_id": "inst_001",
      "outcome": "SUCCESS",
      "attempted_at": "2026-04-15T08:00:00Z"
    },
    { ... }
  ]
}
```

**Response (201):**

```json
{
  "received": 150,
  "linked_to_scores": 142,
  "unlinked": 8
}
```

---

### Analytics

```
GET /v1/analytics/summary
GET /v1/analytics/collection-rate?period=7d|30d|90d
GET /v1/analytics/factors?period=30d
GET /v1/analytics/accuracy?period=30d
```

Query parameters:
- `period`: `7d`, `30d`, `90d`, `12m`
- `collection_method`: `CARD`, `DEBIT_ORDER`, `MOBILE_MONEY`
- `risk_level`: `LOW`, `MEDIUM`, `HIGH`

**Summary response (200):**

```json
{
  "period": "30d",
  "total_scored": 4521,
  "total_outcomes_reported": 3890,
  "collection_rate": 0.78,
  "risk_distribution": {
    "high": 312,
    "medium": 1205,
    "low": 3004
  },
  "prediction_accuracy": {
    "high_risk_actually_failed": 0.82,
    "low_risk_actually_succeeded": 0.94
  },
  "value_at_risk": 156000.00,
  "value_recovered_vs_baseline": 23400.00
}
```

---

### Configuration

```
GET /v1/config/weights
```

Returns current factor weights for the tenant.

```
PUT /v1/config/weights
```

**Request body:**

```json
{
  "weights": {
    "historical_failure_rate": 0.30,
    "day_of_month_vs_payday": 0.15,
    "card_health": 0.15
  }
}
```

Partial updates — only include weights you want to change. Weights must sum to 1.0 across all factors (validated server-side).

```
GET /v1/config/factors
```

Returns the list of available factors for the tenant's factor_set, with descriptions and current weights.

---

### Webhooks

Webhooks are configured per tenant on the alert settings, not via a separate registration endpoint. Each tenant has a single webhook URL and a tenant-scoped signing secret.

**Configure webhook URL:**

```
GET   /v1/config/alerts            # Returns webhook_url + webhook_secret
PUT   /v1/config/alerts            # Update webhook_url, slack_webhook_url, threshold
POST  /v1/config/alerts/regenerate-secret   # Rotate webhook_secret
```

**Sample `GET /v1/config/alerts` response:**

```json
{
  "high_risk_threshold": 0.20,
  "webhook_url": "https://api.lender.com/paypredict-webhook",
  "webhook_secret": "whsec_xY9zK2mP4nQ8rT3vW5xY...",
  "slack_webhook_url": null,
  "email_digest": "OFF",
  "email_recipients": []
}
```

The secret is auto-generated when the tenant is created and is fully visible to authenticated tenant admins. Rotate it via `POST /v1/config/alerts/regenerate-secret` if compromised — the old value is invalidated immediately.

#### Signature verification

Every webhook delivery includes these headers:

| Header | Description |
|--------|-------------|
| `X-PayPredict-Event` | Event name (e.g. `high_risk_alert`) |
| `X-PayPredict-Signature` | `sha256=<hex>` HMAC of the raw request body using your tenant's `webhook_secret` |
| `X-PayPredict-Delivery` | UUID, unique per attempt (3 retries with exponential backoff) |
| `Content-Type` | `application/json` |

**Verify in Python:**

```python
import hmac, hashlib

def verify_paypredict_signature(body: bytes, header: str, secret: str) -> bool:
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", header)
```

**Verify in Node:**

```js
const crypto = require("crypto");

function verifyPaypredictSignature(body, header, secret) {
  const expected = "sha256=" + crypto.createHmac("sha256", secret).update(body).digest("hex");
  return crypto.timingSafeEqual(Buffer.from(expected), Buffer.from(header));
}
```

Use the raw request body before any JSON parsing — re-serialising changes whitespace and breaks the signature.

---

### Health

```
GET /v1/health           # Simple 200 OK
GET /v1/health/detailed  # DB, Redis, queue status (auth required)
```

---

## Error responses

All errors return JSON with consistent structure:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "collection_amount must be a positive number",
    "details": { ... }
  }
}
```

HTTP status codes:
- `400` — Bad request (malformed JSON, missing fields)
- `401` — Unauthorized (missing or invalid API key)
- `404` — Not found (invalid score_id, job_id, or webhook_id)
- `422` — Validation error (fields present but invalid values)
- `429` — Rate limited (too many requests for this API key tier)
- `500` — Server error (our fault — logged and alerted)

---

## Rate limits

| Plan | Requests/minute |
|------|----------------|
| Pilot | 60 |
| Starter | 200 |
| Growth | 500 |
| Scale | 2,000 (custom on request) |

### How it works

- **Per tenant, per minute.** Each API request increments a counter scoped to your tenant and the current calendar minute. The window resets cleanly on each minute boundary — no sliding-window jitter to model.
- **Bulk endpoints count as one request.** `POST /v1/score/bulk` with 1,000 collections burns a single ticket. The hard cap on items per bulk call (also 1,000) is enforced separately and unrelated to the rate limit.
- **Rate-limited endpoints**:
  - Scoring + outcomes: `POST /v1/score`, `POST /v1/score/bulk`, `GET /v1/score/bulk/{job_id}`, `POST /v1/outcomes`.
  - Shared endpoints **when called via API key**: `GET /v1/analytics/*`, `GET /v1/config/weights`, `PUT /v1/config/weights`. The same endpoints called by your dashboard team via the UI session bypass the limit entirely — your own ops team can never throttle itself.
- **Dashboard endpoints** (your team logging into the PayPredict UI) are **not** rate-limited.

### Headers on every response

```
X-RateLimit-Limit: 200          # Your tier ceiling per minute
X-RateLimit-Remaining: 187      # Requests left in this window
X-RateLimit-Reset: 1712678400   # Unix timestamp when the window resets
```

### When you exceed the limit

```
HTTP/1.1 429 Too Many Requests
Retry-After: 23
X-RateLimit-Limit: 200
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1712678400
Content-Type: application/json

{"detail": "Rate limit exceeded (200 requests/min for the STARTER plan). Retry in 23s."}
```

`Retry-After` is the number of seconds until the window resets. Once over the limit, retries before the reset **do not** burn additional tickets — so a tight retry loop won't extend the cool-off period. The recommended client behaviour is to back off using `Retry-After` and resume after the indicated delay.

### When you might need a higher tier

If you're consistently hitting `X-RateLimit-Remaining: 0` near the window boundary, your effective throughput is capped by the tier. Contact support to discuss a Custom limit.