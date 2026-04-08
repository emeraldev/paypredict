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
  "external_customer_id": "string, required",
  "external_collection_id": "string, required",
  "collection_amount": "decimal, required",
  "collection_currency": "enum: ZAR | ZMW, required",
  "collection_due_date": "date (YYYY-MM-DD), required",
  "collection_method": "enum: CARD | DEBIT_ORDER | MOBILE_MONEY, required",
  "customer_data": {
    // --- Common fields (all markets) ---
    "total_payments": "integer, optional (default 0)",
    "successful_payments": "integer, optional (default 0)",
    "last_successful_payment_date": "date, optional",
    "average_collection_amount": "decimal, optional",
    "instalment_number": "integer, optional",
    "total_instalments": "integer, optional",

    // --- SA card-based fields ---
    "card_type": "string: credit | debit, optional",
    "card_expiry_date": "date, optional",
    "last_decline_code": "string, optional",
    "debit_order_returns": "array of strings, optional",
    "known_salary_day": "integer (1-31), optional",

    // --- Zambia mobile money fields ---
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
  "recommended_action": "flag_for_review",
  "recommended_collection_date": "2026-04-02",
  "factors": [
    {
      "factor": "historical_failure_rate",
      "raw_score": 0.375,
      "weight": 0.25,
      "weighted_score": 0.094,
      "explanation": "37.5% of past collections have failed"
    }
  ],
  "model_version": "heuristic_sa_v1",
  "scored_at": "2026-04-08T14:23:01Z",
  "scoring_duration_ms": 12
}
```

**Notes:**
- All customer_data fields are optional. Missing data results in moderate default scores for affected factors (typically 0.3-0.5). More data = more accurate scores.
- The engine automatically selects the correct factor set based on the tenant's market configuration. SA fields are ignored for Zambia tenants and vice versa.
- `recommended_action` values: `collect_normally`, `shift_date`, `flag_for_review`, `pre_collection_sms`

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
      "external_customer_id": "cust_001",
      "external_collection_id": "inst_001",
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
      "external_collection_id": "inst_001",
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
  "external_collection_id": "string, required",
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
      "external_collection_id": "inst_001",
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

Returns the list of available factors for the tenant's market, with descriptions and current weights.

---

### Webhooks

```
POST   /v1/webhooks    # Register a new webhook endpoint
GET    /v1/webhooks    # List registered webhooks
DELETE /v1/webhooks/{id}
```

**Register request:**

```json
{
  "url": "https://api.lender.com/paypredict-webhook",
  "events": ["bulk_scoring_complete", "high_risk_alert"],
  "secret": "whsec_your_signing_secret"
}
```

Webhook payloads are signed with the secret using HMAC-SHA256 in the `X-PayPredict-Signature` header.

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

| Plan | Requests/minute | Bulk batch size |
|------|----------------|----------------|
| Pilot | 60 | 100 |
| Starter | 200 | 500 |
| Growth | 500 | 1,000 |
| Scale | Custom | Custom |

Rate limit headers included in every response:
```
X-RateLimit-Limit: 200
X-RateLimit-Remaining: 187
X-RateLimit-Reset: 1712678400
```