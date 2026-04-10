# Current Feature

Phase 2 — Dashboard (mocked, awaiting API hookup)

## Status

In Progress

## Goals

### Phase 1 — Backend (Completed)
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

### Phase 2 — Dashboard (mocked)
1. ~~Next.js 16 + shadcn project setup, dependencies (recharts, date-fns)~~
2. ~~Shared utilities, constants, types, API client, mock data~~
3. ~~Shared components (risk badge, factor bar, stat card, pagination, etc.)~~
4. ~~Dashboard layout: collapsible sidebar, mobile sheet, topbar with theme toggle~~
5. ~~Dashboard home: summary cards, collections table, filter toolbar, risk detail drawer~~
6. ~~Analytics: collection rate, risk distribution, prediction accuracy, top failure factors~~
7. ~~Outcomes: filter tabs (matched/mismatched/pending), match indicators, stats~~
8. ~~Settings: weights tab with sliders, API keys, alerts, team — all 4 tabs~~
9. ~~Light/dark theme toggle with no-flash inline script~~

### Phase 2 — TODO (deferred)
- Connect to real API (requires new backend GET endpoints for /v1/scores, /v1/analytics/*, /v1/config/*)
- Auth (NextAuth integration)
- Command palette (Cmd+K)
- Real-time updates / websockets
- Export functionality
- Notification bell with real alerts (currently static dot)

## Notes

- Docker Compose uses non-standard ports due to local Postgres/Redis conflicts: Postgres on 5434, Redis on 6380
- All 8 database tables created: tenants, api_keys, factor_weights, score_requests, score_results, outcomes, users, alerts
- 117 backend tests passing (shared + card + wallet factor tests, method filtering tests, engine integration tests, API endpoint tests)
- Scoring completes in ~1ms per collection
- Factor sets are collection-method-based (CARD_DEBIT, MOBILE_WALLET), not country-based. Market (SA, ZM) is separate.
- Shared factors (HistoricalFailureRate, InstalmentPosition, ConcurrentLoanCount, LoanCyclingBehaviour) live in factors/shared/
- Dashboard uses Next.js 16 (Turbopack default, async cookies/headers/params, base-ui under shadcn instead of Radix)
- Dashboard tech: Next 16 + React 19 + Tailwind v4 + shadcn (zinc + base-ui) + recharts + date-fns
- Dashboard runs on http://localhost:3000, expects API at NEXT_PUBLIC_API_URL=http://localhost:8001
- All API calls go through lib/api/client.ts (single fetch wrapper). Mock data lives only in lib/mock-data.ts.
- Theme persisted in localStorage under key 'paypredict-theme'. No-flash inline script in root layout.

## History

- Project setup and boilerplate cleanup
- 2026-04-08: Phase 1 scaffolding complete — FastAPI app, SQLAlchemy models (8 tables), Alembic config + initial migration, Docker Compose, health endpoints working
- 2026-04-08: Phase 1 fully complete — auth middleware, all 16 scoring factors (8 card + 8 wallet), ScoringEngine + FactorRegistry, POST /v1/score, POST /v1/outcomes, seed script, 97 tests all green
- 2026-04-08: Refactor — renamed factor sets from country-based (CARD_SA, MOBILE_ZM) to collection-method-based (CARD_DEBIT, MOBILE_WALLET). Moved shared factors to factors/shared/. Renamed sa/ → card/, zm/ → wallet/. Alembic migration for enum rename. All docs updated.
- 2026-04-09: Collection method filtering — factors declare applicable_methods (CARD, DEBIT_ORDER, MOBILE_MONEY). Engine skips inapplicable factors and re-normalises weights. CardHealth/CardType are CARD-only, DebitOrderReturnHistory is DEBIT_ORDER-only. API response includes skipped_factors. 117 tests passing.
- 2026-04-10: Phase 2 mocked dashboard complete — Next.js 16 + shadcn + Tailwind v4. ~60 dashboard files. Dashboard, analytics, outcomes, and settings pages all functional with mock data. Theme toggle (no-flash). All routes return 200, build clean, no `any` types, no inline fetch outside client.ts. Step 8 (real API hookup) deferred — requires new backend GET endpoints.
