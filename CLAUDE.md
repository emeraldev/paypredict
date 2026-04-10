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
- **Multi-tenant from day one.** Every table has tenant_id. Row-level security in PostgreSQL. Each lender is a tenant with separate API keys, weights, and factor configuration.
- **JSONB for flexibility.** Factor breakdowns and request payloads use JSONB so factor sets can evolve without schema migrations.
- **Factor sets are collection-method-based, not country-based.** The `factor_set` field (CARD_DEBIT, MOBILE_WALLET) determines which scoring factors to use based on how payments are collected. The `market` field (SA, ZM) is separate and determines currency, payday defaults, and regulatory context. This means the same factor set can be reused across any country that uses the same collection method.
- **Factor registry pattern.** Tenant's `factor_set` determines which factor classes load. Adding a new collection method = writing new factor classes + registering them. No API or engine changes needed.
- **Collection method filtering.** Each factor declares which collection methods it applies to via `applicable_methods`. The engine skips inapplicable factors (e.g. CardHealth is skipped for DEBIT_ORDER collections) and re-normalises the remaining weights to sum to 1.0. Skipped factors are reported in the API response for transparency.
- **Alembic for all migrations.** Never use auto-generate blindly. Review every migration. Run in dev first, then production. Never push schema changes directly.

## Project structure

```
paypredict/
├── api/                           # FastAPI backend (Python)
│   ├── app/
│   │   ├── main.py                # FastAPI app, middleware, CORS
│   │   ├── config.py              # Settings from env vars
│   │   ├── dependencies.py        # Auth, tenant resolution, rate limiting
│   │   ├── api/v1/               # Route handlers
│   │   │   ├── scores.py         # POST /v1/score, /v1/score/bulk
│   │   │   ├── outcomes.py       # POST /v1/outcomes
│   │   │   ├── analytics.py      # GET /v1/analytics/*
│   │   │   ├── config.py         # GET/PUT /v1/config/*
│   │   │   ├── webhooks.py       # CRUD /v1/webhooks
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
│   │       └── mock-data.ts            # ONLY file with mock data — replace in Step 8
│   └── .env.local                      # NEXT_PUBLIC_API_URL=http://localhost:8001
│
├── docs/                          # Documentation content
└── .github/workflows/             # CI/CD
```

## Database tables

Core tables: Tenant, ApiKey, FactorWeight, ScoreRequest, ScoreResult, Outcome, User, Alert

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

```
POST   /v1/score                     # Score single collection (~1ms)
POST   /v1/score/bulk                # Score batch (async)
GET    /v1/score/bulk/{job_id}       # Poll bulk results
POST   /v1/outcomes                  # Report collection outcome
POST   /v1/outcomes/bulk             # Report batch outcomes
GET    /v1/analytics/summary         # Collection rates, accuracy
GET    /v1/analytics/collection-rate # Rate over time
GET    /v1/analytics/factors         # Factor contribution ranking
GET    /v1/analytics/accuracy        # Predicted vs actual
GET    /v1/config/weights            # Current weights
PUT    /v1/config/weights            # Update weights
GET    /v1/config/factors            # Available factors
POST   /v1/webhooks                  # Register webhook
GET    /v1/health                    # Health check
```

All API endpoints require `Authorization: Bearer <api_key>`. See `docs/api-reference.md` for full request/response schemas.

## Current development phase

Phase 1 is complete. Phase 2 mocked dashboard is complete. Phase 2.5 (real API hookup) is the next step.

### Phase 1 (Weeks 1-4) — COMPLETE:
1. Project setup: FastAPI, SQLAlchemy, Alembic, Docker Compose for local dev
2. Database schema + migrations (all 8 tables)
3. Auth middleware (API key validation → tenant resolution)
4. Health endpoint
5. BaseFactor class + card/debit factor implementations (all 8)
6. Mobile wallet factor implementations (all 8)
7. ScoringEngine orchestrator + factor registry
8. POST /v1/score endpoint
9. POST /v1/outcomes endpoint
10. Seed data script for demo
11. Unit tests for all factors + engine (117 tests passing including method-filtering tests)

### Phase 2 (Weeks 5-8) — Dashboard MOCKED, COMPLETE:
1. Next.js 16 + shadcn project setup (zinc, base-ui under shadcn, Tailwind v4)
2. Shared utilities, types, API client, mock data
3. Shared components (risk badge, factor bar, stat card, pagination, etc.)
4. Dashboard layout: collapsible sidebar, mobile sheet, topbar with theme toggle
5. Dashboard home page: summary cards, collections table, filter toolbar, risk detail drawer
6. Analytics page: collection rate, risk distribution, prediction accuracy, top failure factors
7. Outcomes page: filter tabs, match indicators, stats
8. Settings page: weights tab with sliders, API keys, alerts, team — all 4 tabs
9. Light/dark theme toggle with no-flash inline script

### Phase 2.5 — TODO (deferred):
- **Backend GET endpoints needed:** GET /v1/scores (list), GET /v1/scores/{id}, GET /v1/outcomes (list), GET /v1/analytics/summary, /collection-rate, /factors, GET /v1/config/tenant, /weights, /api-keys, /team, /alerts, plus PUT/POST/DELETE for writable settings
- **Dashboard hooks** (use-collections, use-analytics, use-outcomes, use-tenant-config) — currently consume mock-data.ts directly
- **Replace mock-data.ts imports** with hook calls + add loading skeletons / error boundaries
- **NextAuth v5** for dashboard auth (currently stubbed)

### Phase 3 (Weeks 9-12): Async scoring, alerts, webhooks
### Phase 4 (Months 4-6): Timing optimiser, analytics depth, ML prep

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

# Tests
pytest                            # Run all tests
pytest tests/test_scoring_engine.py -v  # Specific test file

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

## Code style and conventions

### Backend (Python)
- Type hints on all functions. Pydantic models for all request/response schemas. Async handlers where possible.
- Factor classes: One file per factor. Class name matches factor name in PascalCase. File name is snake_case.
- Tests: One test file per module. Use pytest fixtures for common setup. Test every factor with edge cases (zero history, expired cards, empty wallets).
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
