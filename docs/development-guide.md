# PayPredict — Development Guide

## Local development setup

### Prerequisites
- Python 3.12+
- Node.js 20+ (for dashboard)
- Docker & Docker Compose (for Postgres + Redis)
- Git

### Initial setup

```bash
# Clone the repo
git clone https://github.com/emeraldev/paypredict.git
cd paypredict

# Start infrastructure
docker-compose up -d   # Postgres 16 + Redis 7

# API setup
cd api
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"

# Create database + run migrations
alembic upgrade head

# Seed demo data
python -m app.seed

# Start API server
uvicorn app.main:app --reload --port 8000
# API available at http://localhost:8000
# Swagger docs at http://localhost:8000/docs

# Dashboard setup (separate terminal)
cd dashboard
npm install
npm run dev
# Dashboard at http://localhost:3000
```

### Docker Compose (local dev)

```yaml
# docker-compose.yml (in project root)
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: paypredict_dev
      POSTGRES_USER: paypredict
      POSTGRES_PASSWORD: localdev
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  pgdata:
```

### Environment variables

```bash
# api/.env (local development)
DATABASE_URL=postgresql+asyncpg://paypredict:localdev@localhost:5432/paypredict_dev
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=local-dev-secret-change-in-production
ENVIRONMENT=development
LOG_LEVEL=DEBUG
```

```bash
# dashboard/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=local-dev-secret
```

---

## Database migrations

We use Alembic. NEVER modify the database directly.

```bash
cd api

# Generate a new migration (ALWAYS review the generated file before applying)
alembic revision --autogenerate -m "add_alert_table"

# Review the migration file in alembic/versions/
# Check: correct table names, column types, indexes, foreign keys, nullable settings

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View current migration state
alembic current

# View migration history
alembic history
```

**Rules:**
- Review every auto-generated migration. Alembic sometimes misses things or generates unnecessary operations.
- Test migrations against a copy of production data before running in prod.
- Never delete or modify an already-applied migration. Create a new one instead.
- Name migrations descriptively: `add_alert_table`, `add_index_score_result_tenant_risk`, not `update_stuff`.

---

## Running tests

```bash
cd api

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_scoring_engine.py -v

# Run specific test
pytest tests/test_factors/test_historical_failure.py::test_zero_history -v

# Run with coverage
pytest --cov=app --cov-report=html

# Run only fast tests (skip integration)
pytest -m "not integration"
```

### Test structure

```
tests/
├── conftest.py                    # Shared fixtures (test DB, test tenant, test API client)
├── test_scoring_engine.py         # Engine orchestration tests
├── test_factors/
│   ├── test_sa/
│   │   ├── test_historical_failure.py
│   │   ├── test_day_of_month.py
│   │   ├── test_card_health.py
│   │   └── ...
│   └── test_zm/
│       ├── test_wallet_balance.py
│       ├── test_time_since_inflow.py
│       └── ...
├── test_api/
│   ├── test_score_endpoint.py
│   ├── test_outcomes_endpoint.py
│   ├── test_auth.py
│   └── test_rate_limiting.py
└── fixtures/
    ├── sa_customers.json          # Sample SA customer data
    └── zm_customers.json          # Sample Zambia customer data
```

### What to test for every factor

Each factor needs tests covering:
1. **Normal case:** Typical input, expected score range
2. **Edge case — no data:** Missing fields → should return moderate default (0.3-0.5), not crash
3. **Edge case — zeros:** Zero payments, zero balance, zero days
4. **Edge case — extreme values:** Very high numbers, very old dates
5. **Boundary values:** Values exactly at threshold boundaries (e.g., 90 days for DaysSinceLastPayment)
6. **Explanation test:** Verify the explain() output is human-readable and matches the score

---

## Seed data

The seed script creates demo data for local development and prospect demos:

```bash
python -m app.seed
```

Creates:
- 2 tenants: "Demo BNPL SA" (SA market) and "Demo MoMo ZM" (Zambia market)
- API keys for both (printed to console on first run)
- Default factor weights for each market
- Sample score requests + results for dashboard testing
- Sample outcomes linked to scores

Seed data should tell a clear story for demos:
- Mix of high, medium, and low risk scores
- Some with outcomes reported, some pending
- Variety of failure reasons
- Realistic collection amounts and dates

---

## Code conventions

### Python (API)

- **Type hints everywhere.** Every function parameter and return type annotated.
- **Pydantic for all I/O.** Request bodies, response bodies, config — all Pydantic models.
- **Async where possible.** Database queries, Redis operations, HTTP calls — all async.
- **One class per file for factors.** File name = snake_case factor name. Class name = PascalCase.
- **Services layer.** Business logic in `services/`, not in route handlers. Route handlers validate input, call service, return response.
- **No business logic in models.** SQLAlchemy models are data containers. Logic goes in services.

### TypeScript (Dashboard)

- **Strict TypeScript.** No `any` types. Define interfaces for all API responses.
- **Server components by default.** Client components only when interactivity is needed.
- **shadcn/ui for all UI components.** Don't build custom components that shadcn already provides.
- **API client module.** All API calls go through `lib/api-client.ts`, never inline fetch calls.

### Git

- **Branch naming:** `feature/scoring-engine`, `fix/auth-middleware`, `docs/factor-reference`
- **Commit messages:** Present tense, imperative. "Add historical failure factor" not "Added historical failure factor"
- **PR required for main.** No direct pushes to main branch.

---

## Phase 1 implementation order

This is the recommended order for building Phase 1 (Weeks 1-4). Each step builds on the previous.

### Foundation

```
1. Project scaffolding
   - FastAPI app skeleton (main.py, config.py)
   - pyproject.toml with dependencies
   - Docker Compose for local Postgres + Redis
   - Alembic configuration

2. Database models + first migration
   - Tenant model
   - ApiKey model
   - ScoreRequest model
   - ScoreResult model
   - Run migration, verify tables exist

3. Auth middleware
   - API key extraction from Authorization header
   - Key hash lookup in ApiKey table
   - Tenant resolution (attach tenant to request context)
   - Return 401 for missing/invalid keys

4. Health endpoint
   - GET /v1/health → 200 OK
   - GET /v1/health/detailed → DB and Redis connectivity check
```

### Scoring engine + API

```
5. BaseFactor class
   - Abstract base with calculate(), explain(), clamp()
   - Type definitions for customer_data and collection_data

6. SA factors (all 8)
   - Implement one at a time, with unit tests for each
   - Start with HistoricalFailureRate (simplest, proves the pattern)
   - Then DayOfMonthVsPayday, DaysSinceLastPayment, etc.

7. Zambia factors (all 8)
   - Same approach, one at a time with tests
   - WalletBalanceTrend first (most important Zambia factor)

8. ScoringEngine + FactorRegistry
   - Registry maps market → factor set
   - Engine loads weights, runs factors, sums scores, maps to risk level
   - Integration test: full scoring with sample data

9. POST /v1/score endpoint
   - Validate request body (Pydantic schema)
   - Load tenant from auth middleware
   - Call ScoringEngine
   - Store ScoreRequest + ScoreResult
   - Return response

10. POST /v1/outcomes endpoint
    - Validate request body
    - Link to ScoreResult if score_id provided
    - Store Outcome record

11. Seed data script
    - Create demo tenants, API keys, factor weights
    - Create sample scores and outcomes for dashboard work

12. Tests
    - All factors tested (normal + edge cases)
    - Engine integration test
    - API endpoint tests (happy path + errors + auth)
```

After Phase 1, you should be able to:
- Start the API locally
- Create a tenant and API key via seed script
- Score a collection via curl/Postman
- Report an outcome
- See scores in the database
- Run all tests green