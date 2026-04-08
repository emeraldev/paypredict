# CLAUDE.md — PayPredict

## What is this project?

PayPredict is a pre-collection risk scoring API and ops dashboard for instalment lenders in Africa. It predicts which upcoming loan/BNPL collections will fail before the collection is attempted, and recommends actions to improve recovery rates.

The product serves two markets simultaneously:
- **South Africa:** Card-on-file charges and debit order (EFT) collections for BNPL providers and personal lenders
- **Zambia:** Mobile money wallet auto-deductions for MNO-embedded lending (MTN MoMo, Airtel Money)

## How the scoring works

The scoring engine uses a **weighted heuristic model** — 7-8 pluggable factor classes per market, each returning a score between 0.0 (safe) and 1.0 (risky). Scores are multiplied by configurable weights and summed into a final score mapped to risk levels: Low (0-30), Medium (31-60), High (61-100).

This is NOT an ML product yet. Heuristics are the product for the first 6-12 months. The architecture is designed so ML models can replace heuristic factors later without changing the API contract. Every scored collection + its outcome builds the labelled dataset needed for future ML training.

## Tech stack

- **Backend API:** Python 3.12+ / FastAPI / Pydantic v2
- **Database:** PostgreSQL 16 (Neon or AWS RDS) / SQLAlchemy 2.0 + Alembic migrations
- **Task queue:** Redis + Celery (bulk scoring, webhooks, alerts)
- **Cache:** Redis
- **Dashboard:** Next.js 15 / React 19 / TypeScript / Tailwind CSS v4 + shadcn/ui
- **Auth:** API keys (hashed) for lender API access, NextAuth v5 for dashboard
- **Hosting:** AWS af-south-1 (Cape Town) — ECS Fargate or App Runner
- **CI/CD:** GitHub Actions → Docker → AWS
- **Monitoring:** Sentry + CloudWatch

## Key architecture decisions

- **No PII stored.** We only store external_customer_id and external_collection_id from lenders. Never names, phone numbers, IDs, or card numbers.
- **Immutable scores.** ScoreResults are never updated after creation. Rescoring creates a new ScoreRequest + ScoreResult pair. This is for audit trail and ML training data integrity.
- **Multi-tenant from day one.** Every table has tenant_id. Row-level security in PostgreSQL. Each lender is a tenant with separate API keys, weights, and factor configuration.
- **JSONB for flexibility.** Factor breakdowns and request payloads use JSONB so factor sets can evolve without schema migrations.
- **Factor registry pattern.** Tenant's market (SA or ZM) determines which factor set loads. Adding a new market = writing new factor classes + registering them. No API or engine changes needed.
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
│   │   │   ├── registry.py        # Factor set registry (SA, ZM, CUSTOM)
│   │   │   └── factors/
│   │   │       ├── base.py        # BaseFactor abstract class
│   │   │       ├── sa/            # 8 SA card-based factors
│   │   │       └── zm/            # 8 Zambia mobile money factors
│   │   ├── models/                # SQLAlchemy models
│   │   ├── schemas/               # Pydantic request/response schemas
│   │   ├── services/              # Business logic layer
│   │   └── tasks/                 # Celery async tasks
│   ├── alembic/                   # DB migrations
│   ├── tests/
│   ├── Dockerfile
│   └── docker-compose.yml         # Local dev stack
│
├── dashboard/                     # Next.js frontend
│   ├── src/app/
│   │   ├── dashboard/page.tsx     # Main risk table
│   │   ├── dashboard/analytics/   # Charts and reports
│   │   └── dashboard/settings/    # Weights, API keys, team
│   └── src/components/            # UI components
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

### SA (Card-based + Debit Order) — 8 factors
HistoricalFailureRate (0.25), DayOfMonthVsPayday (0.20), DaysSinceLastPayment (0.15), InstalmentPosition (0.10), OrderValueVsAverage (0.10), CardHealth (0.10), CardType (0.05), DebitOrderReturnHistory (0.05)

### Zambia (Mobile Money) — 8 factors
WalletBalanceTrend (0.25), HistoricalFailureRate (0.20), TimeSinceLastInflow (0.15), SalaryCycleAlignment (0.15), ConcurrentLoanCount (0.10), TransactionVelocity (0.05), AirtimePurchasePattern (0.05), LoanCyclingBehaviour (0.05)

All factors inherit from BaseFactor with calculate() → float and explain() → str methods. See `docs/factors.md` for detailed logic.

## API endpoints summary

```
POST   /v1/score                     # Score single collection (~15ms)
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

We are at the very beginning — Phase 1 (Weeks 1-4). Nothing has been built yet. Start with the API backend.

### Phase 1 priorities (Weeks 1-4):
1. Project setup: FastAPI, SQLAlchemy, Alembic, Docker Compose for local dev
2. Database schema + first migration (Tenant, ApiKey, ScoreRequest, ScoreResult)
3. Auth middleware (API key validation → tenant resolution)
4. Health endpoint
5. BaseFactor class + SA factor implementations (all 8)
6. Zambia factor implementations (all 8)
7. ScoringEngine orchestrator + factor registry
8. POST /v1/score endpoint
9. POST /v1/outcomes endpoint
10. Seed data script for demo
11. Unit tests for all factors + engine

### Phase 2 (Weeks 5-8): Dashboard + deployment
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
npm run dev                       # Start Next.js dev server
```

## Code style and conventions

- Python: Type hints on all functions. Pydantic models for all request/response schemas. Async handlers where possible.
- Factor classes: One file per factor. Class name matches factor name in PascalCase. File name is snake_case.
- Tests: One test file per module. Use pytest fixtures for common setup. Test every factor with edge cases (zero history, expired cards, empty wallets).
- Migrations: Always generate, review, then apply. Never push directly to production DB. Never manually create tables or migrations
- API responses: Always include score_id for traceability. Factor breakdowns always included (transparency is a feature).
- Error responses: Use standard HTTP codes. 400 for bad request, 401 for auth, 404 for not found, 422 for validation, 429 for rate limit, 500 for server error. Always return JSON with error detail.


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