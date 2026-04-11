## PayPredict — MVP Project Specification

---

## Problem (Core Idea)

Lenders in Africa process thousands of instalment collections daily with zero intelligence about which ones will fail:

- Collections are treated equally — no prioritisation
- Ops teams react after failures instead of predicting them
- Retry timing is arbitrary (collect on due date regardless of payday cycles)
- Failed collections waste PSP/MNO transaction fees
- No visibility into why collection rates are dropping
- Spreadsheets are the "risk management tool"
- When an ops person leaves, their instincts leave with them

Default rates across African lending are staggering — 20-65% depending on the segment. BNPL providers in South Africa are struggling to profit. Mobile money lenders in Zambia and East Africa lose millions to failed auto-deductions.

PayPredict provides a pre-collection risk scoring API and ops dashboard that predicts which upcoming collections will fail, recommends optimal timing, and gets smarter over time through a feedback loop of real outcomes.

---

## Markets

### South Africa (Launch market)
- **Collection methods:** Card-on-file charges, debit orders (EFT)
- **Target lenders:** BNPL providers, personal lenders, vehicle finance, MNO lending (MTN QwikLoan, VodaLend)
- **Key players:** Float, PayJustNow, Payflex, Finchoice, Wonga, JUMO
- **Regulatory context:** BNPL currently unregulated, regulation coming 2026 (FINASA working group). National Credit Act covers formal credit.

### Zambia (Second market)
- **Collection methods:** Mobile money wallet auto-deduction (MTN MoMo, Airtel Money, Zamtel Kwacha)
- **Target lenders:** MNO embedded lending (Kongola, Nasova), JUMO, ExpressCredit, Kazang
- **Key players:** MTN Zambia, Airtel Zambia, JUMO, Tenga/Atlas Mara
- **Regulatory context:** Lighter regulation, Bank of Zambia oversees mobile money

---

## Users

- **Ops/Collections Manager:**
  Views risk-ranked collections each morning. Focuses manual outreach on high-risk accounts. Reviews collection performance by cohort. Configures alert thresholds.

- **Head of Risk / CTO:**
  Monitors overall collection health. Tunes scoring weights. Reviews prediction accuracy over time. Needs audit trail for regulators.

- **Engineering Team (at lender):**
  Integrates the scoring API into lender's collection workflow. Sends data, receives scores, acts on recommendations. Needs clean docs and sandbox.

- **Finance / Executive:**
  Views collection rate trends and monetary impact. Needs weekly/monthly reports showing ROI of the scoring system.

---

## Features

### A. Scoring Engine (Core)

The scoring engine is the heart of the product. It accepts data about a borrower and an upcoming collection, and returns a risk score with factor breakdown and recommended action.

**How it works:**
1. Lender sends customer + collection data via API
2. Engine loads the appropriate factor set (SA card-based OR Zambia mobile money) based on tenant configuration
3. Each factor class calculates a score between 0.0 (safe) and 1.0 (risky)
4. Scores are multiplied by configurable weights and summed
5. Final score is mapped to a risk level
6. Response includes score, risk level, factor breakdown, recommended action, and explanation

**Risk levels:**
- 0–30: Low risk (green) → collect normally
- 31–60: Medium risk (amber) → monitor, optimise timing
- 61–100: High risk (red) → flag for ops review, pre-collection outreach

**Scoring modes:**
- `single` — Score one collection (synchronous, ~15ms)
- `bulk` — Score a batch of upcoming collections (async via task queue, results via webhook or polling)

### B. Factor Sets

Factors are pluggable Python classes following the Strategy pattern. Each market has a different default factor set, but tenants can adjust weights.

#### Card & Debit Order Factor Set (CARD)

Applies to any country using card-on-file charges or debit order (EFT) collections.

| Factor | Default Weight | Logic |
|--------|---------------|-------|
| `HistoricalFailureRate` | 0.25 | Customer's past payment success/failure ratio. 100% failure = 1.0, 100% success = 0.0 |
| `DayOfMonthVsPayday` | 0.20 | Common payday patterns: 25th/1st in many African markets. Collecting on 28th (pre-payday) = high risk. Collecting on 2nd = low risk. Configurable per-customer if salary date is known |
| `DaysSinceLastPayment` | 0.15 | Recency of last successful payment. >90 days = 1.0. <7 days = 0.1 |
| `InstalmentPosition` | 0.10 | Later instalments (e.g., 5 of 6) carry more fatigue risk than earlier ones |
| `OrderValueVsAverage` | 0.10 | Collection amount significantly above customer's historical average = higher risk |
| `CardHealth` | 0.10 | Card expiry proximity, previous decline codes (hard vs soft), card age. Expired = 1.0 |
| `CardType` | 0.05 | Debit cards more prone to insufficient funds than credit. Unknown = 0.4 |
| `DebitOrderReturnHistory` | 0.05 | SA-specific: EFT return code patterns (insufficient funds, account closed, disputed) |

#### Mobile Money Factor Set (MOBILE_MONEY)

Applies to any country with mobile money wallet collections (M-Pesa, MTN MoMo, Airtel Money, etc.).

| Factor | Default Weight | Logic |
|--------|---------------|-------|
| `WalletBalanceTrend` | 0.25 | 7-day moving average of wallet balance. Declining trend = higher risk. Requires lender to send balance snapshots or we infer from transaction data |
| `HistoricalFailureRate` | 0.20 | Same concept as SA — past collection success/failure ratio |
| `TimeSinceLastInflow` | 0.15 | Hours since money last entered the wallet. >72 hours = high risk. <6 hours = low risk (just received funds) |
| `SalaryCycleAlignment` | 0.15 | Is the collection date aligned with the borrower's regular income pattern? Misaligned = higher risk |
| `ConcurrentLoanCount` | 0.10 | Number of active loans the borrower has across platforms (if data available). Over-leveraged = danger |
| `TransactionVelocity` | 0.05 | Sudden drop in send/receive frequency = financial stress signal |
| `AirtimePurchasePattern` | 0.05 | Regular airtime buyer who suddenly stops = proxy for income disruption |
| `LoanCyclingBehaviour` | 0.05 | Taking a new loan to repay an existing one. Classic default predictor |

#### Base Factor Class

All factors inherit from a base class:

```python
class BaseFactor:
    """Every factor returns a score 0.0 (safe) to 1.0 (risky)"""

    def calculate(self, customer_data: dict, collection_data: dict) -> float:
        raise NotImplementedError

    def explain(self, score: float) -> str:
        raise NotImplementedError

    def clamp(self, value: float) -> float:
        return max(0.0, min(1.0, value))
```

### C. Outcome Tracking (Feedback Loop)

This is what makes the product get smarter over time and what builds the dataset for ML.

- After each collection attempt, the lender reports the outcome back via API: `POST /v1/outcomes`
- Payload: `{ score_id, outcome: "success" | "failed", failure_reason?, attempted_at }`
- Every outcome is stored alongside the pre-collection risk score
- This creates labelled data: "we predicted risk 0.72, the collection failed" or "we predicted 0.35, it succeeded"
- Over time, this data is used to validate factor weights and eventually train ML models

### D. Collection Timing Optimiser

Recommends the optimal time to attempt collection based on:
- Customer's known income timing (salary date, mobile money inflow patterns)
- Historical success rates by day-of-week and time-of-day for this customer
- Market-level patterns (SA: post-25th, Zambia: varies by customer)

Returns: `{ recommended_date, recommended_time_window, confidence, reasoning }`

This is a Phase 2 feature but the data collection starts from day one.

### E. Dashboard (Ops Interface)

A web dashboard for lender ops teams to:

- View upcoming collections ranked by risk score (highest first)
- Filter by risk level (high / medium / low), date range, collection method
- Click into a collection to see full factor breakdown + customer context
- View collection rate analytics (by cohort, merchant, card type, time period)
- Configure scoring weights for their tenant
- Set alert thresholds (e.g., "notify me when >20% of a batch is high-risk")
- View prediction accuracy over time (predicted vs actual outcomes)

### F. Alerts & Notifications

- Webhook: push high-risk batch alerts to lender's own systems
- Slack integration: send daily risk summary to a Slack channel
- Email: weekly collection performance digest
- SMS (Zambia): pre-collection reminder to high-risk borrowers (lender triggers, we provide the data)

### G. Multi-Tenancy

Every lender is a tenant with complete data isolation:

- Separate API keys
- Separate scoring weights (can override defaults)
- Separate factor set configuration (SA or Zambia or custom)
- Separate outcome data
- Row-level security in PostgreSQL

### H. API Documentation

Auto-generated from Pydantic schemas via FastAPI:

- Interactive Swagger UI at `/docs`
- Hosted documentation site (Mintlify or GitBook) with:
  - Quick start guide
  - Authentication guide
  - API reference (every endpoint, request/response schemas)
  - Factor reference (what each factor means, how it scores)
  - Integration examples (Python, Node.js, Ruby, curl)
  - Sandbox environment with test data

---

## Data

### TENANT

```
- id: uuid
- name: string                        # "PayJustNow", "MTN Kongola"
- market: enum (SA, ZM, KE, TZ, UG, GH, NG, UK)  # Metadata: currency, timezone, regulatory context
- factor_set: enum (CARD, MOBILE_MONEY, CUSTOM)    # Drives which factors run (collection-method-based)
- is_active: boolean
- plan: enum (PILOT, STARTER, GROWTH, SCALE)
- webhook_url: string | null           # For async results + alerts
- slack_webhook_url: string | null
- alert_threshold: float               # e.g., 0.20 = alert when >20% high-risk
- created_at: datetime
- updated_at: datetime
```

### API_KEY

```
- id: uuid
- tenant_id: uuid (FK → Tenant)
- key_hash: string                     # Hashed, never stored in plain text
- key_prefix: string                   # First 8 chars for identification (e.g., "pk_live_")
- label: string                        # "Production", "Staging"
- is_active: boolean
- last_used_at: datetime | null
- created_at: datetime
```

### FACTOR_WEIGHT

```
- id: uuid
- tenant_id: uuid (FK → Tenant)
- factor_name: string                  # e.g., "historical_failure_rate"
- weight: float                        # 0.0 to 1.0
- updated_at: datetime
- updated_by: uuid (FK → User) | null
```

### SCORE_REQUEST

```
- id: uuid
- tenant_id: uuid (FK → Tenant)
- external_customer_id: string         # Lender's customer ID (we don't store PII)
- external_collection_id: string       # Lender's collection/instalment ID
- collection_amount: decimal
- collection_currency: enum (ZAR, ZMW)
- collection_due_date: date
- collection_method: enum (CARD, DEBIT_ORDER, MOBILE_MONEY)
- request_payload: jsonb               # Full request data (for audit + reprocessing)
- created_at: datetime
```

### SCORE_RESULT

```
- id: uuid
- score_request_id: uuid (FK → ScoreRequest)
- tenant_id: uuid (FK → Tenant)
- score: float                         # 0.0 to 1.0
- risk_level: enum (LOW, MEDIUM, HIGH)
- factors: jsonb                       # Array of { factor_name, raw_score, weight, weighted_score, explanation }
- recommended_action: string           # "collect_normally", "shift_date", "flag_for_review", "pre_collection_sms"
- recommended_collection_date: date | null
- model_version: string                # "heuristic_v1", "ml_v1", etc. (for A/B tracking)
- scoring_duration_ms: integer         # Latency tracking
- created_at: datetime
```

### OUTCOME

```
- id: uuid
- score_result_id: uuid (FK → ScoreResult)
- tenant_id: uuid (FK → Tenant)
- external_collection_id: string
- outcome: enum (SUCCESS, FAILED, PENDING)
- failure_reason: string | null        # "insufficient_funds", "card_expired", "wallet_empty", "account_closed", "disputed"
- failure_category: enum | null        # SOFT_DECLINE, HARD_DECLINE, TECHNICAL
- amount_collected: decimal | null     # Partial collection support
- attempted_at: datetime
- reported_at: datetime                # When the lender told us
- created_at: datetime
```

### USER (Dashboard users)

```
- id: uuid
- tenant_id: uuid (FK → Tenant)
- email: string
- name: string
- password_hash: string
- role: enum (ADMIN, MANAGER, VIEWER)
- last_login_at: datetime | null
- created_at: datetime
```

### ALERT

```
- id: uuid
- tenant_id: uuid (FK → Tenant)
- alert_type: enum (HIGH_RISK_BATCH, COLLECTION_RATE_DROP, PREDICTION_DRIFT)
- message: string
- metadata: jsonb                      # Batch details, threshold, etc.
- is_read: boolean
- created_at: datetime
```

### Key relationships:
```
Tenant (1) → (many) ApiKey
Tenant (1) → (many) FactorWeight
Tenant (1) → (many) ScoreRequest
Tenant (1) → (many) User
ScoreRequest (1) → (1) ScoreResult
ScoreResult (1) → (0..1) Outcome
```

### Data principles:
- **No PII stored.** We receive external_customer_id and external_collection_id from the lender. We never store names, phone numbers, ID numbers, or card numbers. The lender maps our scores back to their customers in their own system.
- **Immutable scores.** Once a ScoreResult is created, it is never updated. This is critical for audit trail and ML training. If a collection is re-scored, a new ScoreRequest + ScoreResult is created.
- **JSONB for flexibility.** Factor breakdowns and request payloads use JSONB so we can evolve factor sets without schema migrations for every change.
- **Tenant isolation.** Every query includes tenant_id. Row-level security policies enforce this at the database level.

---

## Tech Stack

### Backend API — Python 3.12+ / FastAPI

- FastAPI for REST API with automatic OpenAPI docs
- Pydantic v2 for request/response validation and serialisation
- Async request handling for high throughput
- One codebase/repo — API + scoring engine + task workers
- Type hints everywhere for safety

### Database — PostgreSQL 16 (Neon or AWS RDS)

- Primary data store for all tables above
- JSONB columns for flexible factor data and request payloads
- Row-level security for tenant isolation
- Connection pooling via PgBouncer or built-in Neon pooling

### ORM & Migrations — SQLAlchemy 2.0 + Alembic

- SQLAlchemy 2.0 with async support
- Alembic for database migrations
- **IMPORTANT: Never use auto-generate blindly. Review every migration. Run in dev first, then production.**

### Task Queue — Redis + Celery (or ARQ)

- Bulk scoring jobs (score hundreds/thousands of collections async)
- Webhook delivery (notify lender systems)
- Outcome processing
- Alert evaluation (check thresholds after each batch)
- Future: ML model retraining jobs

### Caching — Redis

- Cache frequently-accessed tenant configs and factor weights
- Cache recent scores for the dashboard (avoid re-querying for every page load)
- Rate limiting counters per API key

### Frontend Dashboard — Next.js 15 / React 19

- Server-side rendering for fast initial loads
- TypeScript throughout
- Tailwind CSS v4 + shadcn/ui components
- Dark mode default (ops teams work long hours)
- Responsive: desktop-first, mobile-usable

### Authentication (Dashboard)

- NextAuth v5 for dashboard user login
- Email/password for MVP
- API keys (hashed, prefixed) for lender API authentication
- Role-based access: Admin, Manager, Viewer

### Hosting — AWS af-south-1 (Cape Town)

- **API:** ECS Fargate or AWS App Runner (containerised FastAPI)
- **Database:** AWS RDS PostgreSQL or Neon (managed)
- **Cache/Queue:** AWS ElastiCache Redis
- **Dashboard:** Vercel (Next.js) or same ECS cluster
- **Monitoring:** Sentry (errors) + CloudWatch (logs/metrics)
- **CI/CD:** GitHub Actions → Docker → deploy

### AI/ML (Future — not MVP)

- scikit-learn / XGBoost for first ML models (logistic regression, gradient boosting)
- Trained on outcome data collected during heuristic phase
- Model artifacts stored in S3
- Shadow mode: ML scores alongside heuristic scores, compare accuracy
- Swap when ML consistently outperforms

### Documentation

- FastAPI auto-generated Swagger at `/docs`
- Hosted docs site via Mintlify or GitBook
- Integration guides, factor reference, sandbox access

---

## API Endpoints

### Scoring

```
POST   /v1/score                 # Score a single upcoming collection
POST   /v1/score/bulk            # Score a batch (async, returns job_id)
GET    /v1/score/bulk/{job_id}   # Poll for bulk scoring results
```

### Outcomes

```
POST   /v1/outcomes              # Report collection outcome (single)
POST   /v1/outcomes/bulk         # Report outcomes in batch
```

### Analytics

```
GET    /v1/analytics/summary           # Collection rates, prediction accuracy, risk distribution
GET    /v1/analytics/collection-rate   # Collection rate over time (daily/weekly/monthly)
GET    /v1/analytics/factors           # Which factors contribute most to failures
GET    /v1/analytics/accuracy          # Predicted risk vs actual outcomes
```

### Configuration

```
GET    /v1/config/weights              # Get current factor weights
PUT    /v1/config/weights              # Update factor weights
GET    /v1/config/factors              # List available factors for tenant's market
GET    /v1/config/tenant               # Get tenant configuration
```

### Webhooks

```
POST   /v1/webhooks                    # Register a webhook endpoint
GET    /v1/webhooks                    # List registered webhooks
DELETE /v1/webhooks/{id}               # Remove a webhook
```

### Health

```
GET    /v1/health                      # API health check
GET    /v1/health/detailed             # Detailed status (DB, Redis, queue)
```

### Authentication

All API endpoints require `Authorization: Bearer <api_key>` header.
Dashboard endpoints use session-based auth via NextAuth.

### Request/Response Examples

**Score a single collection:**

```
POST /v1/score
Authorization: Bearer pk_live_abc123...

{
  "external_customer_id": "cust_8291",
  "external_collection_id": "inst_44021",
  "collection_amount": 833.33,
  "collection_currency": "ZAR",
  "collection_due_date": "2026-04-15",
  "collection_method": "CARD",
  "customer_data": {
    "total_payments": 8,
    "successful_payments": 5,
    "last_successful_payment_date": "2026-03-02",
    "card_type": "debit",
    "card_expiry_date": "2026-09-01",
    "last_decline_code": "insufficient_funds",
    "average_collection_amount": 750.00,
    "instalment_number": 4,
    "total_instalments": 6
  }
}
```

**Response:**

```json
{
  "score_id": "sr_9f8e7d6c",
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
    },
    {
      "factor": "day_of_month_vs_payday",
      "raw_score": 0.7,
      "weight": 0.20,
      "weighted_score": 0.14,
      "explanation": "Due mid-month — elevated risk window"
    },
    {
      "factor": "card_health",
      "raw_score": 0.6,
      "weight": 0.10,
      "weighted_score": 0.06,
      "explanation": "Last decline was insufficient funds — soft decline"
    }
  ],
  "model_version": "heuristic_sa_v1",
  "scored_at": "2026-04-08T14:23:01Z",
  "scoring_duration_ms": 12
}
```

**Mobile money request (Zambia):**

```
POST /v1/score
Authorization: Bearer pk_live_zm_xyz789...

{
  "external_customer_id": "momo_user_5521",
  "external_collection_id": "loan_rep_8843",
  "collection_amount": 250.00,
  "collection_currency": "ZMW",
  "collection_due_date": "2026-04-10",
  "collection_method": "MOBILE_MONEY",
  "customer_data": {
    "total_payments": 3,
    "successful_payments": 2,
    "last_successful_payment_date": "2026-03-25",
    "wallet_balance_7d_avg": 180.00,
    "wallet_balance_current": 95.00,
    "hours_since_last_inflow": 48,
    "active_loan_count": 2,
    "last_airtime_purchase_days_ago": 1,
    "regular_inflow_day": "friday"
  }
}
```

---

## Monetization

### Pricing Model: Per-Score + Dashboard Subscription

**Pilot (Free — first 30 days)**
- Up to 1,000 scores
- Full factor breakdown
- Basic dashboard access
- Outcome reporting enabled
- Purpose: Prove ROI before converting to paid

**Starter (R5,000/month)**
- Up to 10,000 scores/month
- Full dashboard access (2 users)
- Webhook alerts
- Email support
- Weight configuration

**Growth (R15,000/month)**
- Up to 50,000 scores/month
- Full dashboard access (5 users)
- Slack integration
- Collection timing recommendations
- Analytics & reporting
- Priority support

**Scale (R40,000+/month — custom)**
- Unlimited scores (per-score pricing above 100K: R0.30/score)
- Unlimited dashboard users
- Custom factor development
- Dedicated account manager
- SLA guarantee (99.9% uptime)
- ML model training on tenant's data (when available)

### Zambia Pricing (adjusted for market)

Same tiers but ~40% lower price point to account for lower collection values and currency.

- Pilot: Free
- Starter: ZMW 5,000/month (~R5,000)
- Growth: ZMW 12,000/month (~R12,000)
- Scale: Custom

### Foundation for billing:

During MVP development, all tenants get full access. Billing enforcement comes after first 5 paying customers. Use Stripe for SA payments. Zambia billing TBD (potentially direct bank transfer or mobile money payment).

---

## UI/UX

### General

- Modern, minimal, data-focused
- Dark mode by default (ops teams)
- Light mode available
- Clean typography, generous whitespace
- Reference: Linear, Datadog, Stripe Dashboard
- Colour-coded risk levels throughout

### Layout

- Sidebar + main content (collapsible sidebar)
- Sidebar: Navigation (Dashboard, Collections, Analytics, Settings), tenant name, quick stats
- Main: Content area that changes based on route
- Risk detail panels open in slide-over drawer (not full page navigation)

### Dashboard Home (`/dashboard`)

- **Summary cards at top:** Total upcoming, high-risk count (red), medium (amber), low (green), total value at risk
- **Cards are clickable** — filter the table below by risk level
- **Collections table:** Sorted by risk score (highest first). Columns: Risk (dot + score + mini bar), Customer ID, Amount, Due Date, Instalment, Method (card/debit/mobile), Action button
- **Expand row** → slide-over drawer with full factor breakdown, customer context, recommended action
- **Quick actions:** Mark as reviewed, snooze alert, add note

### Analytics (`/dashboard/analytics`)

- Collection rate over time (line chart)
- Risk distribution (donut chart — % high/medium/low)
- Prediction accuracy (predicted vs actual — scatter or confusion matrix)
- Top failure factors (bar chart — which factors contribute most)
- Filterable by date range, collection method, risk level

### Settings (`/dashboard/settings`)

- Factor weights (sliders with save)
- Alert thresholds
- Webhook configuration
- API key management (create, revoke, view usage)
- Team management (invite users, assign roles)

### Risk Level Colours

```
High Risk:
  - Background: #fef2f2 (light red)
  - Border/Accent: #ef4444 (red-500)
  - Text: #991b1b (red-800)
  - Dot: #ef4444

Medium Risk:
  - Background: #fffbeb (light amber)
  - Border/Accent: #f59e0b (amber-500)
  - Text: #92400e (amber-800)
  - Dot: #f59e0b

Low Risk:
  - Background: #ecfdf5 (light green)
  - Border/Accent: #10b981 (emerald-500)
  - Text: #065f46 (emerald-800)
  - Dot: #10b981
```

### Collection Method Icons & Colours

```
Card:
  - Colour: #3b82f6 (blue-500)
  - Icon: CreditCard

Debit Order:
  - Colour: #8b5cf6 (purple-500)
  - Icon: Building (bank)

Mobile Money:
  - Colour: #f97316 (orange-500)
  - Icon: Smartphone
```

### Responsive

- Desktop-first (ops teams use desktop)
- Tablet usable (for on-the-go reviews)
- Mobile: simplified view — summary cards + risk list (no full table)

### Micro-interactions

- Smooth transitions on drawer open/close
- Hover states on table rows
- Toast notifications for actions (score complete, webhook registered, weights saved)
- Loading skeletons for async data
- Risk score animations (number counting up on load)
- Pulse animation on high-risk dot when batch exceeds threshold

---

## Project Structure

```
paypredict/
├── api/                              # FastAPI backend
│   ├── app/
│   │   ├── main.py                   # FastAPI app, middleware, CORS
│   │   ├── config.py                 # Settings, env vars
│   │   ├── dependencies.py           # Auth, tenant resolution, rate limiting
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── scores.py         # POST /v1/score, POST /v1/score/bulk
│   │   │       ├── outcomes.py       # POST /v1/outcomes
│   │   │       ├── analytics.py      # GET /v1/analytics/*
│   │   │       ├── config.py         # GET/PUT /v1/config/*
│   │   │       ├── webhooks.py       # CRUD /v1/webhooks
│   │   │       └── health.py         # GET /v1/health
│   │   ├── scoring/
│   │   │   ├── engine.py             # ScoringEngine orchestrator
│   │   │   ├── registry.py           # Factor set registry (SA, ZM, CUSTOM)
│   │   │   └── factors/
│   │   │       ├── base.py           # BaseFactor abstract class
│   │   │       ├── sa/               # SA card-based factors
│   │   │       │   ├── historical_failure.py
│   │   │       │   ├── day_of_month.py
│   │   │       │   ├── days_since_payment.py
│   │   │       │   ├── instalment_position.py
│   │   │       │   ├── order_value.py
│   │   │       │   ├── card_health.py
│   │   │       │   ├── card_type.py
│   │   │       │   └── debit_order_returns.py
│   │   │       └── zm/               # Zambia mobile money factors
│   │   │           ├── wallet_balance_trend.py
│   │   │           ├── historical_failure.py
│   │   │           ├── time_since_inflow.py
│   │   │           ├── salary_cycle.py
│   │   │           ├── concurrent_loans.py
│   │   │           ├── transaction_velocity.py
│   │   │           ├── airtime_pattern.py
│   │   │           └── loan_cycling.py
│   │   ├── models/                   # SQLAlchemy models
│   │   │   ├── tenant.py
│   │   │   ├── api_key.py
│   │   │   ├── score_request.py
│   │   │   ├── score_result.py
│   │   │   ├── outcome.py
│   │   │   ├── factor_weight.py
│   │   │   ├── user.py
│   │   │   └── alert.py
│   │   ├── schemas/                  # Pydantic request/response schemas
│   │   │   ├── score.py
│   │   │   ├── outcome.py
│   │   │   ├── analytics.py
│   │   │   ├── config.py
│   │   │   └── webhook.py
│   │   ├── services/                 # Business logic
│   │   │   ├── scoring_service.py
│   │   │   ├── outcome_service.py
│   │   │   ├── analytics_service.py
│   │   │   └── alert_service.py
│   │   └── tasks/                    # Celery tasks
│   │       ├── bulk_scoring.py
│   │       ├── webhook_delivery.py
│   │       ├── alert_evaluation.py
│   │       └── outcome_processing.py
│   ├── alembic/                      # Database migrations
│   │   └── versions/
│   ├── tests/
│   │   ├── test_scoring_engine.py
│   │   ├── test_factors/
│   │   ├── test_api/
│   │   └── fixtures/
│   ├── alembic.ini
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── docker-compose.yml            # Local dev: API + Postgres + Redis
│
├── dashboard/                        # Next.js frontend
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx              # Login / landing
│   │   │   └── dashboard/
│   │   │       ├── page.tsx          # Main dashboard (risk table)
│   │   │       ├── analytics/
│   │   │       │   └── page.tsx
│   │   │       └── settings/
│   │   │           └── page.tsx
│   │   ├── components/
│   │   │   ├── risk-table.tsx
│   │   │   ├── risk-detail-drawer.tsx
│   │   │   ├── summary-cards.tsx
│   │   │   ├── factor-breakdown.tsx
│   │   │   ├── collection-rate-chart.tsx
│   │   │   ├── risk-distribution-chart.tsx
│   │   │   └── weight-sliders.tsx
│   │   ├── lib/
│   │   │   ├── api-client.ts         # Typed API client for PayPredict API
│   │   │   └── utils.ts
│   │   └── styles/
│   │       └── globals.css
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── package.json
│
├── docs/                             # Documentation site content
│   ├── quickstart.md
│   ├── authentication.md
│   ├── api-reference.md
│   ├── factors.md
│   └── integration-examples.md
│
├── .github/
│   └── workflows/
│       ├── api-ci.yml                # Test + lint + build API
│       ├── api-deploy.yml            # Deploy API to AWS
│       └── dashboard-deploy.yml      # Deploy dashboard
│
└── README.md
```

---

## Development Priorities

### Phase 1: Scoring API (Weeks 1-4)

**Week 1-2: Foundation**
- [ ] Project setup (FastAPI, SQLAlchemy, Alembic, Docker Compose)
- [ ] Database schema + migrations for Tenant, ApiKey, ScoreRequest, ScoreResult
- [ ] Auth middleware (API key validation, tenant resolution)
- [ ] Health endpoints
- [ ] BaseFactor class + 3 SA factors (historical_failure, day_of_month, card_health)
- [ ] ScoringEngine orchestrator

**Week 3-4: Complete factors + outcomes**
- [ ] Remaining SA factors (5 more)
- [ ] All Zambia factors (8)
- [ ] Factor registry (load correct set per tenant market)
- [ ] `POST /v1/score` endpoint (single scoring)
- [ ] `POST /v1/outcomes` endpoint
- [ ] Outcome storage + linking to ScoreResult
- [ ] Seed data script for demo/testing
- [ ] Unit tests for all factors + scoring engine

### Phase 2: Dashboard + Polish (Weeks 5-8)

**Week 5-6: Dashboard core**
- [ ] Next.js project setup + auth (NextAuth v5)
- [ ] Dashboard home: summary cards + risk table
- [ ] Risk detail drawer with factor breakdown
- [ ] API client (typed, calls PayPredict API)

**Week 7-8: Settings + deploy**
- [ ] Settings page: weight sliders, API key management
- [ ] Basic analytics page (collection rate chart, risk distribution)
- [ ] Deploy API to AWS Cape Town (ECS Fargate or App Runner)
- [ ] Deploy dashboard to Vercel
- [ ] Swagger docs live at `/docs`
- [ ] Demo environment with seed data for prospect demos

### Phase 3: Async + Alerts

- [ ] Bulk scoring endpoint + Celery workers
- [ ] Webhook delivery for async results
- [ ] Alert system (high-risk batch notifications)
- [ ] Slack integration
- [ ] Prediction accuracy tracking (compare scores to outcomes)
- [ ] Hosted documentation site

### Phase 4: Optimisation + ML Prep

- [ ] Collection timing optimiser
- [ ] Analytics depth: failure factor ranking, cohort analysis
- [ ] Export functionality (CSV/JSON)
- [ ] Outcome data analysis: which factors actually predict failures?
- [ ] Weight auto-tuning suggestions based on outcome data
- [ ] ML model experimentation in Jupyter (not production yet)

---

## Non-Functional Requirements

### Performance
- Single score: < 50ms p95 response time
- Bulk score (1000 items): < 30 seconds
- Dashboard page load: < 2 seconds
- API uptime target: 99.5% (MVP), 99.9% (Scale tier)

### Security
- API keys hashed at rest (bcrypt or argon2)
- All traffic over HTTPS / TLS 1.3
- No PII stored — only external IDs
- Tenant data isolation via row-level security
- Rate limiting per API key (configurable per tier)
- Audit log for all configuration changes

### Compliance
- POPIA (SA) compliant — no personal data stored
- Zambia Data Protection Act — same principle
- Scoring logic is explainable (every score has factor breakdown)
- Immutable audit trail (scores never modified after creation)