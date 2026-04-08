# Current Feature

Phase 1 — API Backend Foundation

## Status

In Progress

## Goals

1. Project setup: FastAPI, SQLAlchemy, Alembic, Docker Compose for local dev
2. Database schema + first migration (all 8 tables)
3. Auth middleware (API key validation -> tenant resolution)
4. Health endpoint
5. BaseFactor class + SA factor implementations (all 8)
6. Zambia factor implementations (all 8)
7. ScoringEngine orchestrator + factor registry
8. POST /v1/score endpoint
9. POST /v1/outcomes endpoint
10. Seed data script for demo
11. Unit tests for all factors + engine

## Notes

- Docker Compose uses non-standard ports due to local Postgres/Redis conflicts: Postgres on 5434, Redis on 6380
- All 8 database tables created: tenants, api_keys, factor_weights, score_requests, score_results, outcomes, users, alerts

## History

- Project setup and boilerplate cleanup
- 2026-04-08: Phase 1 scaffolding complete — FastAPI app, SQLAlchemy models (8 tables), Alembic config + initial migration, Docker Compose, health endpoints working
