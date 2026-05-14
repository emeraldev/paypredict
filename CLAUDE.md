# CLAUDE.md — PayPredict

## What is this project?

PayPredict is a pre-collection risk scoring API and ops dashboard for instalment lenders in Africa. It predicts which upcoming loan/BNPL collections will fail before the collection is attempted, and recommends actions to improve recovery rates.

The product serves two markets simultaneously:
- **South Africa:** Card-on-file charges and debit order (EFT) collections for BNPL providers and personal lenders
- **Zambia:** Mobile money wallet auto-deductions for MNO-embedded lending (MTN MoMo, Airtel Money)

## How the scoring works

The scoring engine uses a **weighted heuristic model** — 8 pluggable factor classes per factor set, each returning a score between 0.0 (safe) and 1.0 (risky). Scores are multiplied by configurable weights and summed into a final score mapped to risk levels: Low (0-30), Medium (31-60), High (61-100).

This is NOT an ML product yet. Heuristics are the product for the first 6-12 months. The architecture is designed so ML models can replace heuristic factors later without changing the API contract. Every scored collection + its outcome builds the labelled dataset needed for future ML training.

## Tech stack

- **Backend API:** Python 3.12+ / FastAPI / Pydantic v2
- **Database:** PostgreSQL 16 (Neon or AWS RDS) / SQLAlchemy 2.0 + Alembic migrations
- **Task queue:** Redis + Celery (bulk scoring, webhooks, alerts)
- **Cache:** Redis
- **Dashboard:** Next.js 16 (Turbopack default, async cookies/headers/params) / React 19 / TypeScript / Tailwind CSS v4 + shadcn/ui (zinc, base-ui not Radix) / recharts / date-fns
- **Auth:** API keys (hashed) for lender API access, NextAuth v5 for dashboard (deferred — currently stubbed)
- **Hosting:** AWS af-south-1 (Cape Town) — ECS Fargate or App Runner
- **CI/CD:** GitHub Actions → Docker → AWS
- **Monitoring:** Sentry + CloudWatch

## Key architecture decisions

- **No PII stored.** We only store external_customer_id and external_collection_id from lenders. Never names, phone numbers, IDs, or card numbers.
- **Immutable scores.** ScoreResults are never updated after creation. Rescoring creates a new ScoreRequest + ScoreResult pair. This is for audit trail and ML training data integrity.
- **Multi-tenant from day one.** Every table has tenant_id. Row-level security in PostgreSQL. Each lender is a tenant with separate API keys, weights, factor configuration, and webhook signing secret.
- **Per-tenant webhook signing secret.** Each tenant has a unique `webhook_secret` (auto-generated on tenant creation, `whsec_<random>` format). All outgoing webhook deliveries are signed with HMAC-SHA256 using the tenant's secret. Customers can rotate via `POST /v1/config/alerts/regenerate-secret` if compromised. NEVER share secrets across tenants — that would allow cross-tenant forgery.
- **JSONB for flexibility.** Factor breakdowns and request payloads use JSONB so factor sets can evolve without schema migrations.
- **Factor sets are collection-method-based, not country-based.** The `factor_set` field (CARD_DEBIT, MOBILE_WALLET) determines which scoring factors to use based on how payments are collected. The `market` field (SA, ZM) is separate and determines currency, payday defaults, and regulatory context. This means the same factor set can be reused across any country that uses the same collection method.
- **Factor registry pattern.** Tenant's `factor_set` determines which factor classes load. Adding a new collection method = writing new factor classes + registering them. No API or engine changes needed.
- **Collection method filtering.** Each factor declares which collection methods it applies to via `applicable_methods`. The engine skips inapplicable factors (e.g. CardHealth is skipped for DEBIT_ORDER collections) and re-normalises the remaining weights to sum to 1.0. Skipped factors are reported in the API response for transparency.
- **Alembic for all migrations.** Never use auto-generate blindly. Review every migration. Run in dev first, then production. Never push schema changes directly.
- **Rate limiting on lender API endpoints.** Fixed one-minute window per tenant, backed by Redis (`ratelimit:{tenant_id}:{minute_epoch}` key, ~70s TTL). Tier limits live in `app/config.py:PLAN_RATE_LIMITS` and must stay in sync with the table in `docs/api-reference.md`. Two enforcement deps live in `app/dependencies.py`: `enforce_rate_limit` (drop-in for `get_current_tenant` on API-key-only routes) and `enforce_rate_limit_or_jwt` (drop-in for `get_tenant_from_either` on dual-auth routes — applies the limit only on the API-key path, JWT requests bypass entirely so the dashboard team can't throttle itself). Both share `_apply_rate_limit`. Dashboard-only JWT routes are not rate-limited.

## Project structure

```
paypredict/
├── api/                           # FastAPI backend (Python)
│   ├── app/
│   │   ├── main.py                # FastAPI app, middleware, CORS
│   │   ├── config.py              # Settings from env vars
│   │   ├── dependencies.py        # Auth, tenant resolution, rate limiting
│   │   ├── api/v1/               # Route handlers
│   │   │   ├── scores.py         # POST /v1/score
│   │   │   ├── scores_list.py    # GET /v1/scores, /v1/scores/{id}
│   │   │   ├── bulk_score.py     # POST /v1/score/bulk + GET /v1/score/bulk/{job_id}
│   │   │   ├── outcomes.py       # POST /v1/outcomes
│   │   │   ├── outcomes_list.py  # GET /v1/outcomes
│   │   │   ├── analytics.py      # GET /v1/analytics/*
│   │   │   ├── auth.py           # POST /v1/auth/login, /me, /logout
│   │   │   ├── api_keys.py       # CRUD /v1/config/api-keys
│   │   │   ├── team.py           # CRUD /v1/config/team (admin-only)
│   │   │   ├── weights.py        # GET/PUT /v1/config/weights
│   │   │   ├── alerts_config.py  # GET/PUT /v1/config/alerts + regenerate-secret
│   │   │   ├── backtest.py       # POST /v1/backtest, upload, list, get
│   │   │   ├── alerts.py         # GET /v1/alerts (legacy)
│   │   │   ├── notifications.py  # GET /v1/notifications, mark-read
│   │   │   └── health.py         # GET /v1/health
│   │   ├── scoring/
│   │   │   ├── engine.py          # ScoringEngine orchestrator
│   │   │   ├── registry.py        # Factor set registry (CARD_DEBIT, MOBILE_WALLET, CUSTOM)
│   │   │   └── factors/
│   │   │       ├── base.py        # BaseFactor abstract class
│   │   │       ├── shared/        # Factors used by multiple factor sets
│   │   │       ├── card/          # Card-on-file + debit order factors
│   │   │       └── wallet/        # Mobile money wallet factors
│   │   ├── models/                # SQLAlchemy models
│   │   ├── schemas/               # Pydantic request/response schemas
│   │   ├── services/              # Business logic layer
│   │   └── tasks/                 # Celery async tasks
│   ├── alembic/                   # DB migrations
│   ├── tests/
│   ├── Dockerfile
│   └── docker-compose.yml         # Local dev stack
│
├── dashboard/                     # Next.js 16 frontend
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx              # Root layout: theme provider + no-flash script + sonner
│   │   │   ├── page.tsx                # Redirects to /dashboard
│   │   │   └── dashboard/
│   │   │       ├── layout.tsx          # Dashboard shell: sidebar + topbar + main
│   │   │       ├── page.tsx            # Risk-ranked collections table + drawer
│   │   │       ├── analytics/page.tsx  # 4 charts + stat cards
│   │   │       ├── outcomes/page.tsx   # Outcomes table with match/mismatch
│   │   │       └── settings/page.tsx   # 4 tabs: weights, API keys, alerts, team
│   │   ├── components/
│   │   │   ├── ui/                     # shadcn primitives (button, card, table, etc.)
│   │   │   ├── shared/                 # Reused across pages (risk-badge, factor-bar, stat-card, ...)
│   │   │   ├── layout/                 # Sidebar, topbar, mobile sidebar, theme toggle
│   │   │   ├── dashboard/              # Collections table, summary cards, drawer
│   │   │   ├── analytics/              # 4 chart components + stat cards
│   │   │   ├── outcomes/               # Outcomes table, filter tabs, stats
│   │   │   └── settings/               # Weights/API keys/alerts/team tabs
│   │   ├── hooks/
│   │   │   ├── use-sidebar.tsx         # Sidebar collapse state context
│   │   │   └── use-theme.tsx           # Light/dark theme + no-flash script
│   │   └── lib/
│   │       ├── api/                    # client.ts (single fetch wrapper) + types + endpoint wrappers
│   │       ├── utils/                  # format-currency, format-date, format-risk, format-method
│   │       ├── constants.ts            # RISK_CONFIG, METHOD_CONFIG, FACTOR_LABELS — single source of truth
│   │       └── mock-data.ts            # DEPRECATED — retained for reference, zero imports
│   └── .env.local                      # NEXT_PUBLIC_API_URL=http://localhost:8001
│
├── docs/                          # Documentation content
└── .github/workflows/             # CI/CD
```

## Database tables

Core tables: Tenant, ApiKey, FactorWeight, ScoreRequest, ScoreResult, Outcome, User, Alert, BacktestRun, BacktestItem, Notification

Key relationships:
- Tenant (1) → (many) ApiKey, FactorWeight, ScoreRequest, User
- ScoreRequest (1) → (1) ScoreResult
- ScoreResult (1) → (0..1) Outcome

See `docs/data-model.md` for full schema definitions.

## Factor sets

Factor sets are organised by **collection method**, not by country. Shared factors (e.g. HistoricalFailureRate, InstalmentPosition) live in `factors/shared/` and are reused across both sets.

### CARD_DEBIT (Card-on-file + Debit Order) — 8 factors
HistoricalFailureRate (0.25), DayOfMonthVsPayday (0.20), DaysSinceLastPayment (0.15), InstalmentPosition (0.10), OrderValueVsAverage (0.10), CardHealth (0.10), CardType (0.05), DebitOrderReturnHistory (0.05)

### MOBILE_WALLET (Mobile Money Wallet) — 8 factors
WalletBalanceTrend (0.25), HistoricalFailureRate (0.20), TimeSinceLastInflow (0.15), SalaryCycleAlignment (0.15), ConcurrentLoanCount (0.10), TransactionVelocity (0.05), AirtimePurchasePattern (0.05), LoanCyclingBehaviour (0.05)

All factors inherit from BaseFactor with calculate() → float and explain() → str methods. See `docs/factors.md` for detailed logic.

## API endpoints summary

### Lender-facing (API key auth)
```
POST   /v1/score                     # Score single collection (~1ms)
POST   /v1/score/bulk                # Score batch (<=50 sync, >50 async via Celery)
GET    /v1/score/bulk/{job_id}       # Poll async bulk job status/results
POST   /v1/outcomes                  # Report collection outcome
GET    /v1/health                    # Health check
```

### Dashboard-facing (JWT session auth)
```
POST   /v1/auth/login                # Email + password → JWT
GET    /v1/auth/me                   # Current user from JWT
POST   /v1/auth/logout               # Stateless logout

GET    /v1/scores                    # List scores (filter, sort, paginate + summary)
GET    /v1/scores/{id}               # Score detail (factors, customer context, outcome)
GET    /v1/outcomes                   # List outcomes (filter, stats)

GET    /v1/analytics/summary         # Period summary with rate change
GET    /v1/analytics/collection-rate # Time-series (daily/weekly)
GET    /v1/analytics/factors         # Factor contributions + correlation
GET    /v1/analytics/accuracy        # Confusion matrix

GET    /v1/config/weights            # Current weights
PUT    /v1/config/weights            # Update weights
GET    /v1/config/api-keys           # List API keys
POST   /v1/config/api-keys           # Create key (returns raw key once)
PATCH  /v1/config/api-keys/{id}      # Toggle active/inactive
DELETE /v1/config/api-keys/{id}      # Revoke key
GET    /v1/config/team               # List team (admin-only)
POST   /v1/config/team               # Invite member
PATCH  /v1/config/team/{id}          # Update role
DELETE /v1/config/team/{id}          # Remove member
GET    /v1/config/alerts             # Alert settings (incl. webhook_secret)
PUT    /v1/config/alerts             # Update alert settings
POST   /v1/config/alerts/regenerate-secret  # Rotate per-tenant webhook signing secret

POST   /v1/backtest                  # Run backtest (JSON, max 500)
POST   /v1/backtest/upload           # Run backtest from CSV
GET    /v1/backtest/{id}             # Get backtest results
GET    /v1/backtests                 # List past backtests
GET    /v1/backtest/template         # Download CSV template

GET    /v1/notifications             # List notifications (paginated, filterable)
GET    /v1/notifications/unread-count # Lightweight count for bell polling
PATCH  /v1/notifications/{id}/read   # Mark single notification read
POST   /v1/notifications/read-all    # Mark all notifications read

GET    /v1/alerts                    # List alerts (legacy)
PATCH  /v1/alerts/{id}/read          # Mark alert read (legacy)
PATCH  /v1/alerts/read-all           # Mark all alerts read (legacy)
```

Two OpenAPI surfaces are served from the same FastAPI app:

- `/docs` — **public Swagger UI** that lenders see. Filtered by tag to only include Scoring, Outcomes, Analytics, Configuration, Webhooks (description-only with HMAC verification examples), and Health. Component schemas are pruned to only those reachable from public paths, so internal Pydantic models (Backtest / Team / ApiKey / Notification / etc.) do not leak.
- `/docs/internal` — **full Swagger UI** with every endpoint, used by the dashboard team during development. Gated by two independent flags: `environment != "production"` AND `internal_docs_enabled` (settings.internal_docs_visible). Returns 404 in production.
- `/redoc` — ReDoc rendering of the public schema.
- `/openapi.json` / `/openapi-internal.json` — the raw schemas.

When adding a new endpoint, set `tags=[...]` to one of the canonical values in `app/api/docs_config.py`. That single setting decides whether it appears in the public or internal Swagger. Untagged endpoints are internal-only by default.

## Current development phase

Phases 1–3 complete. 217 tests passing. Next: deployment, Phase 4 features, or polish.

### Phase 1 (Weeks 1-4) — COMPLETE
Scoring engine, 16 factors, POST /v1/score, POST /v1/outcomes, seed data, 117 tests.

### Phase 2 (Weeks 5-8) — COMPLETE
Next.js 16 dashboard with all pages (dashboard, analytics, outcomes, settings), light/dark theme.

### Phase 2.5 — COMPLETE
JWT auth, all dashboard-facing API endpoints, dashboard wired to real API (zero mock-data imports), login page, auth guard. 166 tests.

### Phase 3 — COMPLETE
- Backtest tool: CSV upload, scoring (reuses ScoringEngine), confusion matrix, results page
- Bulk scoring: sync (<=50) + async (Celery) paths
- Webhook delivery: HMAC-SHA256, 3 retries, Slack
- Alert evaluation: threshold check after bulk scoring, creates Alert + Notification
- Notification system: bell dropdown, 14 event templates, integrated with all config routes
- Separate test DB (paypredict_test) + transaction rollback per test
- E2E test script (34/34 checks)
- Expanded seed: 230 scores, 177 outcomes, 3 alerts, 5 notifications, 1 backtest
- 217 tests passing

### Phase 4 (Months 4-6) — TODO
- Timing optimiser — optimal collection date recommendation
- Analytics depth — cohort analysis, factor trends, A/B weight testing
- ML prep — labelled dataset export, feature engineering, model training

## Commands

```bash
# Local development
cd api
docker-compose up -d              # Start Postgres + Redis
pip install -e ".[dev]"           # Install dependencies
alembic upgrade head              # Run migrations
uvicorn app.main:app --reload     # Start API server

# Migrations
alembic revision --autogenerate -m "description"  # Generate (ALWAYS review before applying)
alembic upgrade head                               # Apply
alembic downgrade -1                               # Rollback one

# Tests (uses separate paypredict_test database — never touches dev data)
pytest                            # Run all tests
pytest tests/test_scoring_engine.py -v  # Specific test file
pytest tests/test_api/ -v         # All API endpoint tests
pytest -x                         # Stop on first failure

# E2E test (requires running API server)
python scripts/test_flow.py       # 34 checks against http://localhost:8001

# Celery worker (for async bulk scoring >50 items)
celery -A app.tasks.celery_app worker --loglevel=info

# Dashboard
cd dashboard
npm install
npm run dev                       # Start Next.js dev server (http://localhost:3000)
npm run build                     # Production build (Turbopack default in Next 16)
```

### Local port quirks
- Postgres runs on port **5434** in Docker (5432 is taken by host Postgres)
- Redis runs on port **6380** in Docker (6379 is taken by host Redis)
- API runs on port **8001** locally (8000 is taken by another local process)
- Dashboard expects `NEXT_PUBLIC_API_URL=http://localhost:8001` in `dashboard/.env.local`

## Test infrastructure

Tests use a **separate `paypredict_test` database** with **transaction rollback per test** — production-grade isolation that ensures tests never interfere with each other or with dev/seed data.

### How it works

1. **Separate database:** `paypredict_test` is created alongside `paypredict_dev` by `api/init-db.sql` (mounted into Docker's entrypoint). Tests never touch the dev database.
2. **Auto-migration:** A session-scoped pytest fixture runs `alembic upgrade head` against the test DB once per test session. You never need to manually migrate the test DB.
3. **Transaction rollback:** Each test gets a database session wrapped in a transaction that is **always rolled back** after the test completes — even if the test fails. The app code calls `session.commit()` but it's patched to `flush()` (writes to DB within the transaction without actually committing). On teardown, the outer transaction rolls back and all data vanishes.
4. **No cleanup code:** Fixtures don't need DELETE statements. The rollback handles everything unconditionally.

### Setup (first time only)

```bash
# If the test database doesn't exist yet (container was created before init-db.sql was added):
docker exec api-postgres-1 psql -U paypredict -d paypredict_dev -c "CREATE DATABASE paypredict_test OWNER paypredict;"
```

After this, just run `pytest` — migrations are applied automatically.

### Key files

- `api/tests/conftest.py` — all fixtures: `db_session` (transaction-wrapped), `sa_tenant`, `zm_tenant`, `sa_admin_user`, `async_client`
- `api/init-db.sql` — creates `paypredict_test` on first Docker start
- `api/alembic/env.py` — respects `ALEMBIC_DATABASE_URL` env var (set by test fixture)
- `api/app/config.py` — `database_url_test` setting

### Writing new tests

```python
@pytest.mark.asyncio
async def test_something(async_client, sa_admin_user):
    # Login to get JWT
    r = await async_client.post("/v1/auth/login", json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD})
    token = r.json()["token"]

    # Make API calls with the token
    r = await async_client.get("/v1/scores", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200

    # All data created during this test is automatically rolled back
```

- Use `sa_tenant` fixture for tests that need a tenant (creates API key + factor weights)
- Use `sa_admin_user` fixture for tests that need JWT auth (creates an ADMIN user)
- Use `async_client` for HTTP endpoint tests (injects the test DB session into the app)
- Use `db_session` directly for service-layer tests
- Never manually delete test data — the transaction rollback handles it

## Code style and conventions

### Backend (Python)
- Type hints on all functions. Pydantic models for all request/response schemas. Async handlers where possible.
- Factor classes: One file per factor. Class name matches factor name in PascalCase. File name is snake_case.
- Tests: One test file per module. Use pytest fixtures from `conftest.py`. Tests run against `paypredict_test` DB with transaction rollback — never manually clean up test data. Test every factor with edge cases.
- Migrations: Always generate, review, then apply. Never push directly to production DB. Never manually create tables or migrations
- API responses: Always include score_id for traceability. Factor breakdowns always included (transparency is a feature).
- Error responses: Use standard HTTP codes. 400 for bad request, 401 for auth, 404 for not found, 422 for validation, 429 for rate limit, 500 for server error. Always return JSON with error detail.

### Dashboard (TypeScript)
- **Server components by default.** Add `"use client"` only when interactivity is needed (state, effects, event handlers)
- **No `any` types anywhere.** Use proper types or `unknown`
- **All API calls go through `lib/api/client.ts`** — no inline `fetch()` calls anywhere else (verified by grep in CI)
- **Risk colors come from `RISK_CONFIG` constant**, never hardcoded hex values in components
- **Format helpers are utilities, not inline.** `formatCurrency`, `formatDate`, `getRiskConfig`, `getMethodConfig` live in `lib/utils/` — used everywhere via import
- **Reusable shared components.** `risk-score-display`, `method-badge`, `factor-bar`, `data-table-pagination`, `stat-card` are used across multiple pages — never duplicated
- **Mock data lives ONLY in `lib/mock-data.ts`** — never scatter across components. Will be removed in Phase 2.5
- **One component per file.** File name is kebab-case, component name is PascalCase. Props interface named `{ComponentName}Props`
- **Shadcn note:** This shadcn version uses `@base-ui/react` instead of Radix. `DialogTrigger` does NOT support `asChild` — control dialogs via state with a separate Button


## Important context

- Target customers are BNPL providers and micro-lenders in SA, and mobile money lenders in Zambia
- JUMO (lending platform behind MTN QwikLoan in SA and MTN Kongola in Zambia) is the strategic whale customer
- The product competes with "nothing" — most lenders use spreadsheets or gut feel for collections
- Heuristics are the product, not a placeholder for ML. They provide immediate value.
- Every scored collection + outcome pair is training data for future ML models
- AWS Cape Town (af-south-1) for hosting — latency to SA customers matters
- The name "PayPredict" is a working name — domain availability not yet confirmed

## Read the following for more context

- @context/coding-standards.md
- @context/ai-interaction.md


Update @context/current-feature.md when after changes are made and approved
