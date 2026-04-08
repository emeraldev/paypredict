# PayPredict — Data Model

## Overview

All tables use UUID primary keys. Every table except Tenant includes tenant_id for row-level isolation. No PII is stored — only external reference IDs from the lender's system.

---

## Tables

### TENANT

The top-level entity. Each lender is a tenant.

```
id:                  uuid, PK
name:                string, not null          # "PayJustNow", "MTN Kongola"
market:              enum (SA, ZM), not null   # Determines default factor set
factor_set:          enum (CARD_SA, MOBILE_ZM, CUSTOM), not null
is_active:           boolean, default true
plan:                enum (PILOT, STARTER, GROWTH, SCALE), default PILOT
webhook_url:         string, nullable          # For async results + alerts
slack_webhook_url:   string, nullable
alert_threshold:     float, default 0.20       # Alert when >20% of batch is high-risk
created_at:          datetime, not null
updated_at:          datetime, not null
```

### API_KEY

Per-tenant API authentication. Keys are hashed, never stored in plain text.

```
id:                  uuid, PK
tenant_id:           uuid, FK → Tenant, not null
key_hash:            string, not null          # bcrypt or argon2 hash
key_prefix:          string, not null          # First 8 chars, e.g. "pk_live_"
label:               string, not null          # "Production", "Staging", "Test"
is_active:           boolean, default true
last_used_at:        datetime, nullable
created_at:          datetime, not null

INDEX: (key_prefix) — for fast lookup during auth
INDEX: (tenant_id, is_active)
```

### FACTOR_WEIGHT

Per-tenant configurable scoring weights. Seeded with defaults on tenant creation.

```
id:                  uuid, PK
tenant_id:           uuid, FK → Tenant, not null
factor_name:         string, not null          # "historical_failure_rate", "wallet_balance_trend"
weight:              float, not null           # 0.0 to 1.0
updated_at:          datetime, not null
updated_by:          uuid, FK → User, nullable

UNIQUE: (tenant_id, factor_name)
```

### SCORE_REQUEST

Every scoring request is logged. Contains the full input payload for audit and reprocessing.

```
id:                  uuid, PK
tenant_id:           uuid, FK → Tenant, not null
external_customer_id:    string, not null      # Lender's customer reference
external_collection_id:  string, not null      # Lender's collection/instalment reference
collection_amount:       decimal(12,2), not null
collection_currency:     enum (ZAR, ZMW), not null
collection_due_date:     date, not null
collection_method:       enum (CARD, DEBIT_ORDER, MOBILE_MONEY), not null
request_payload:         jsonb, not null        # Full request body for audit
created_at:              datetime, not null

INDEX: (tenant_id, created_at DESC)
INDEX: (tenant_id, external_customer_id)
INDEX: (tenant_id, external_collection_id)
```

### SCORE_RESULT

The computed score. Immutable — never updated after creation. One per ScoreRequest.

```
id:                  uuid, PK
score_request_id:    uuid, FK → ScoreRequest, unique, not null
tenant_id:           uuid, FK → Tenant, not null
score:               float, not null           # 0.0 to 1.0
risk_level:          enum (LOW, MEDIUM, HIGH), not null
factors:             jsonb, not null           # Array of factor breakdowns
                     # [{ factor_name, raw_score, weight, weighted_score, explanation }]
recommended_action:  string, not null          # "collect_normally", "shift_date", "flag_for_review", "pre_collection_sms"
recommended_collection_date: date, nullable
model_version:       string, not null          # "heuristic_sa_v1", "heuristic_zm_v1", "ml_sa_v1"
scoring_duration_ms: integer, not null
created_at:          datetime, not null

INDEX: (tenant_id, created_at DESC)
INDEX: (tenant_id, risk_level)
INDEX: (score_request_id) — unique, for 1:1 lookup
```

### OUTCOME

Collection result reported back by the lender. Links to a ScoreResult to create labelled training data.

```
id:                  uuid, PK
score_result_id:     uuid, FK → ScoreResult, unique, nullable
                     # Nullable because lenders might report outcomes for collections we didn't score
tenant_id:           uuid, FK → Tenant, not null
external_collection_id:  string, not null
outcome:             enum (SUCCESS, FAILED, PENDING), not null
failure_reason:      string, nullable          # "insufficient_funds", "card_expired", "wallet_empty", etc.
failure_category:    enum (SOFT_DECLINE, HARD_DECLINE, TECHNICAL), nullable
amount_collected:    decimal(12,2), nullable    # For partial collections
attempted_at:        datetime, not null         # When the collection was attempted
reported_at:         datetime, not null         # When the lender told us
created_at:          datetime, not null

INDEX: (tenant_id, reported_at DESC)
INDEX: (score_result_id) — for joining scores to outcomes
INDEX: (tenant_id, outcome) — for analytics queries
```

### USER

Dashboard users. Scoped to a tenant.

```
id:                  uuid, PK
tenant_id:           uuid, FK → Tenant, not null
email:               string, not null
name:                string, not null
password_hash:       string, not null
role:                enum (ADMIN, MANAGER, VIEWER), not null, default VIEWER
last_login_at:       datetime, nullable
created_at:          datetime, not null
updated_at:          datetime, not null

UNIQUE: (email)
INDEX: (tenant_id, role)
```

### ALERT

System-generated alerts for ops teams.

```
id:                  uuid, PK
tenant_id:           uuid, FK → Tenant, not null
alert_type:          enum (HIGH_RISK_BATCH, COLLECTION_RATE_DROP, PREDICTION_DRIFT), not null
message:             string, not null
metadata:            jsonb, nullable            # Batch details, thresholds, counts
is_read:             boolean, default false
created_at:          datetime, not null

INDEX: (tenant_id, is_read, created_at DESC)
```

---

## Relationships

```
Tenant (1) ──→ (many) ApiKey
Tenant (1) ──→ (many) FactorWeight
Tenant (1) ──→ (many) ScoreRequest
Tenant (1) ──→ (many) User
Tenant (1) ──→ (many) Alert

ScoreRequest (1) ──→ (1) ScoreResult
ScoreResult  (1) ──→ (0..1) Outcome
```

---

## Design notes

### Why no Customer or Collection tables?

We don't model the lender's domain entities. We receive data about customers and collections in each API request and return a score. The lender owns their customer and collection data. We store only what we need for scoring, audit, and training:

- `external_customer_id` — lets us aggregate a customer's scoring history
- `external_collection_id` — lets us link scores to outcomes
- `request_payload` (JSONB) — captures everything the lender sent, for reprocessing and audit

This keeps our schema simple and avoids duplicating the lender's data model, which varies wildly between lenders.

### Why JSONB for factors?

Factor sets differ between markets (SA has 8, Zambia has 8, some overlap). New factors can be added without schema changes. The JSONB column stores the full breakdown array. Querying individual factors is possible via PostgreSQL JSONB operators when needed for analytics.

### Why separate ScoreRequest and ScoreResult?

ScoreRequest captures input. ScoreResult captures output. This separation means:
- We can log a request even if scoring fails (for debugging)
- ScoreResult is immutable — the input context is preserved separately
- Clean foreign key from Outcome → ScoreResult (the thing we're validating)

### Tenant seeding

When a new tenant is created:
1. Generate default FactorWeight records based on their market (SA or ZM defaults)
2. Generate a first API key (return the raw key once, then only store the hash)
3. Create an ADMIN user for the dashboard