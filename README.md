# PayPredict

Pre-collection risk scoring for African lenders. Predicts which instalment collections will fail before they're attempted.

## Overview

PayPredict is an API + ops dashboard that scores upcoming loan/BNPL collections by risk of failure. It serves two markets:

- **South Africa** — card-on-file and debit order collections
- **Zambia** — mobile money wallet auto-deductions

The scoring engine uses configurable heuristic factors (7-8 per market) that produce an explainable risk score. Every scored collection and its outcome creates training data for future ML models.

## Repository structure

```
paypredict/
├── CLAUDE.md              # AI assistant context for this project
├── README.md              # This file
├── docker-compose.yml     # Local dev: Postgres + Redis
├── api/                   # FastAPI backend (Python)
│   ├── app/               # Application code
│   ├── alembic/           # Database migrations
│   ├── tests/             # Test suite
│   ├── Dockerfile
│   └── pyproject.toml
├── dashboard/             # Next.js frontend (TypeScript)
│   ├── src/
│   └── package.json
└── docs/                  # Project documentation
    ├── business-context.md
    ├── data-model.md
    ├── factors.md
    ├── api-reference.md
    └── development-guide.md
```

## Quick start

```bash
# Start local infrastructure
docker-compose up -d

# Setup API
cd api
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload

# Test it
curl -X POST http://localhost:8000/v1/score \
  -H "Authorization: Bearer <key_from_seed_output>" \
  -H "Content-Type: application/json" \
  -d '{
    "external_customer_id": "test_cust_1",
    "external_collection_id": "test_inst_1",
    "collection_amount": 500.00,
    "collection_currency": "ZAR",
    "collection_due_date": "2026-04-15",
    "collection_method": "CARD",
    "customer_data": {
      "total_payments": 10,
      "successful_payments": 7,
      "last_successful_payment_date": "2026-03-28",
      "card_type": "debit",
      "card_expiry_date": "2026-08-01"
    }
  }'
```

## Documentation

| Document | What it covers |
|----------|---------------|
| [CLAUDE.md](./CLAUDE.md) | Full project context for AI-assisted development |
| [docs/business-context.md](./docs/business-context.md) | Why this product exists, target customers, competitive landscape |
| [docs/data-model.md](./docs/data-model.md) | Database schema, table definitions, relationships |
| [docs/factors.md](./docs/factors.md) | All scoring factors with detailed logic for SA and Zambia |
| [docs/api-reference.md](./docs/api-reference.md) | Complete API endpoint reference with request/response examples |
| [docs/development-guide.md](./docs/development-guide.md) | Local setup, migrations, testing, code conventions, Phase 1 build order |

## Tech stack

- **API:** Python 3.12+ / FastAPI / Pydantic v2
- **Database:** PostgreSQL 16 / SQLAlchemy 2.0 / Alembic
- **Queue:** Redis + Celery
- **Dashboard:** Next.js 15 / React 19 / TypeScript / Tailwind v4 / shadcn/ui
- **Hosting:** AWS af-south-1 (Cape Town)

## License

Proprietary. All rights reserved.