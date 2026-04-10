# Current Feature

Phase 1 — API Backend Foundation

## Status

Completed

## Goals

1. ~~Project setup: FastAPI, SQLAlchemy, Alembic, Docker Compose for local dev~~
2. ~~Database schema + first migration (all 8 tables)~~
3. ~~Auth middleware (API key validation -> tenant resolution)~~
4. ~~Health endpoint~~
5. ~~BaseFactor class + card/debit factor implementations (all 8)~~
6. ~~Mobile wallet factor implementations (all 8)~~
7. ~~ScoringEngine orchestrator + factor registry~~
8. ~~POST /v1/score endpoint~~
9. ~~POST /v1/outcomes endpoint~~
10. ~~Seed data script for demo~~
11. ~~Unit tests for all factors + engine~~

## Notes

- Docker Compose uses non-standard ports due to local Postgres/Redis conflicts: Postgres on 5434, Redis on 6380
- All 8 database tables created: tenants, api_keys, factor_weights, score_requests, score_results, outcomes, users, alerts
- 117 tests passing (shared + card + wallet factor tests, method filtering tests, engine integration tests, API endpoint tests)
- Scoring completes in ~1ms per collection
- Factor sets are collection-method-based (CARD_DEBIT, MOBILE_WALLET), not country-based. Market (SA, ZM) is separate.
- Shared factors (HistoricalFailureRate, InstalmentPosition, ConcurrentLoanCount, LoanCyclingBehaviour) live in factors/shared/

## History

- Project setup and boilerplate cleanup
- 2026-04-08: Phase 1 scaffolding complete — FastAPI app, SQLAlchemy models (8 tables), Alembic config + initial migration, Docker Compose, health endpoints working
- 2026-04-08: Phase 1 fully complete — auth middleware, all 16 scoring factors (8 card + 8 wallet), ScoringEngine + FactorRegistry, POST /v1/score, POST /v1/outcomes, seed script, 97 tests all green
- 2026-04-08: Refactor — renamed factor sets from country-based (CARD_SA, MOBILE_ZM) to collection-method-based (CARD_DEBIT, MOBILE_WALLET). Moved shared factors to factors/shared/. Renamed sa/ → card/, zm/ → wallet/. Alembic migration for enum rename. All docs updated.
- 2026-04-09: Collection method filtering — factors declare applicable_methods (CARD, DEBIT_ORDER, MOBILE_MONEY). Engine skips inapplicable factors and re-normalises weights. CardHealth/CardType are CARD-only, DebitOrderReturnHistory is DEBIT_ORDER-only. API response includes skipped_factors. 117 tests passing.
