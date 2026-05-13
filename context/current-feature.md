# Current Feature

All core phases complete. Next: deployment, Phase 4 features, or polish.

## Status

Phase 3 complete. Notification system shipped. CI green on every PR. 224 tests passing.

## Completed Phases

### Phase 1 — Backend (Weeks 1-4) COMPLETE
1. ~~Project setup: FastAPI, SQLAlchemy, Alembic, Docker Compose~~
2. ~~Database schema + migrations (all 8 tables)~~
3. ~~Auth middleware (API key validation → tenant resolution)~~
4. ~~Health endpoint~~
5. ~~All 16 scoring factors (8 card/debit + 8 mobile wallet)~~
6. ~~ScoringEngine orchestrator + factor registry~~
7. ~~POST /v1/score + POST /v1/outcomes~~
8. ~~Seed data script~~
9. ~~117 unit tests~~

### Phase 2 — Dashboard (Weeks 5-8) COMPLETE
1. ~~Next.js 16 + shadcn + Tailwind v4 + recharts~~
2. ~~Dashboard layout: collapsible sidebar, mobile sheet, topbar~~
3. ~~Dashboard home: summary cards, collections table, risk detail drawer~~
4. ~~Analytics: 4 charts + stat cards~~
5. ~~Outcomes: filter tabs, match indicators, stats~~
6. ~~Settings: weights, API keys, alerts, team~~
7. ~~Light/dark theme with no-flash~~

### Phase 2.5 — Dashboard API Wiring COMPLETE
1. ~~JWT auth (login, me, logout) + AuthProvider + AuthGuard~~
2. ~~All dashboard endpoints: GET /v1/scores, /outcomes, /analytics/*, /config/*~~
3. ~~Dashboard wired to real API (replaced all mock-data imports)~~
4. ~~Login page at /login~~
5. ~~GET/PUT /v1/config/weights~~
6. ~~166 tests passing~~

### Phase 3 — Backtest, Bulk Scoring, Webhooks, Alerts COMPLETE
1. ~~Backtest tool: CSV upload, scoring, confusion matrix, results page~~
2. ~~Bulk scoring: sync (<=50) + async (Celery) paths~~
3. ~~Webhook delivery: HMAC-SHA256, 3 retries, Slack~~
4. ~~Alert evaluation: threshold check after bulk scoring~~
5. ~~Notification system: bell dropdown, 14 event templates, integrated with all config routes~~
6. ~~Expanded seed: 230 scores, 177 outcomes, 3 alerts, 5 notifications, 1 backtest~~
7. ~~Separate test DB (paypredict_test) + transaction rollback per test~~
8. ~~E2E test script (34/34 checks)~~
9. ~~201 tests passing~~

## Remaining / Deferred

### Quick fixes (< 1 hour each)
- Export button — toolbar has button, `onExport` not passed from dashboard page
- Topbar search / Cmd+K — decorative input, dashboard table has own search
- Bulk scoring async DB persistence — Celery task scores but doesn't persist to DB

### Phase 3 deferred
- Celery Beat scheduled checks (collection rate drop, prediction drift, card health, unused keys) — need real data + threshold tuning
- Backtest async path (>=500 items) — sync-only for now

### Phase 4 (Months 4-6)
- Timing optimiser — optimal collection date recommendation
- Analytics depth — cohort analysis, factor trends, A/B weight testing
- ML prep — labelled dataset export, feature engineering, model training

### Infrastructure
- ~~CI/CD (GitHub Actions)~~ — backend pytest + frontend lint/build, gate job for branch protection
- AWS deployment (ECS Fargate, af-south-1)
- NextAuth v5 (SSO, refresh tokens)
- Rate limiting middleware

## Notes

- Docker ports: Postgres 5434, Redis 6380, API 8001, Dashboard 3000
- 10 database tables: tenants, api_keys, factor_weights, score_requests, score_results, outcomes, users, alerts, backtest_runs, backtest_items, notifications
- Scoring: ~1ms per collection, collection-method-based factor sets (CARD_DEBIT, MOBILE_WALLET)
- Dashboard: Next 16 + React 19 + Tailwind v4 + shadcn (zinc, base-ui) + recharts + date-fns
- Auth: JWT in localStorage, auto-inject via client.ts, 401 clears token
- Tests: separate paypredict_test DB, transaction rollback per test, Alembic auto-migrates
- Notifications: 30s polling, 14 event templates, integrated with alert/backtest/config services

## History

- 2026-04-08: Phase 1 complete — FastAPI app, 16 factors, ScoringEngine, 117 tests
- 2026-04-09: Collection method filtering — factors declare applicable_methods
- 2026-04-10: Phase 2 mocked dashboard complete — ~60 files, all pages functional
- 2026-04-11: Design polish — topbar route titles, tinted summary cards, sortable table, sidebar tenant info
- 2026-04-12: Phase 2.5 API endpoints — JWT auth, scores/outcomes/analytics/config endpoints, 166 tests
- 2026-04-23: Dashboard wired to real API — all mock-data replaced, login page, auth guard
- 2026-04-23: Phase 3 backtest backend — models, migration, CSV parser, 5 routes, 175 tests
- 2026-04-23: Phase 3 backtest frontend — page, 6 components, sidebar nav
- 2026-04-23: Test infrastructure — separate paypredict_test DB, transaction rollback
- 2026-04-23: Phase 3 bulk scoring — Celery setup, sync/async paths, 181 tests
- 2026-04-23: Webhook delivery — HMAC-SHA256, retries, Slack, 185 tests
- 2026-04-23: Alert evaluation + endpoints + topbar bell, 192 tests
- 2026-04-23: Expanded seed — 230 scores, 177 outcomes, 3 alerts, 1 backtest
- 2026-04-24: E2E test script — 34/34 checks pass
- 2026-04-24: Bug fixes — Sheet backdrop flash, backtest recovery calc, annualization, tenant refresh, API key refetch, CSV error display
- 2026-05-08: Notification system — model, service (14 templates), 4 endpoints, bell dropdown, integrated with all config routes, 5 seed notifications, 201 tests
- 2026-05-09: Quick fixes — Cmd+K command palette (global search across collections/outcomes/backtests), CSV export wired (Dashboard + Outcomes, paginated through all pages), settings tabs read ?tab= URL param, Team Manage dialog (role change + remove), bulk scoring DB persistence in Celery path
- 2026-05-09: Per-tenant webhook secret — replaces hardcoded shared "paypredict" secret. Tenant.webhook_secret column, auto-generated whsec_<random>, exposed in GET /v1/config/alerts, POST /v1/config/alerts/regenerate-secret to rotate, dashboard UI shows + copies + rotates the secret. Closes a cross-tenant forgery risk before paying customers exist. 203 tests.
- 2026-05-12: CI/CD — GitHub Actions workflow with backend (pytest + Postgres/Redis services) and frontend (lint + build) jobs, plus a ci-passed gate for branch protection. Concurrency cancels stale runs. README CI badge. Dropped deprecated mock-data.ts; downgraded react-hooks/set-state-in-effect to warn (the default flags legitimate external-data sync patterns).
- 2026-05-12: Cosmetic/UX — Customer/Amount/Method columns sortable on dashboard (backend whitelist extended to external_customer_id + collection_method, 3 new sort tests). Analytics period picker (7d/14d/30d/60d/90d) replaces hardcoded 30d. Empty states redesigned with circular icon backdrop and context-aware copy/actions across collections, outcomes, backtest results, and notifications dropdown. 206 tests.
- 2026-05-12: Fix blank Top Failure Contributors chart — bulk scoring path was persisting factor entries with key "factor" instead of "factor_name" (single-score path was correct). Analytics SQL reads "factor_name" → returned NULL → Pydantic 500. Fixed bulk_scoring_service + Celery task to persist canonical shape, hardened analytics SQL with COALESCE on both keys, and shipped a one-time migration to normalize 3 legacy rows. API response shape unchanged. 208 tests.
- 2026-05-12: Split Swagger docs by tag — `/docs` now shows only lender-facing endpoints (Scoring, Outcomes, Analytics, Configuration, Health); the full surface (incl. Auth, Notifications, Backtest, Dashboard Scores/Outcomes, API Keys, Team, Alert Settings) lives at `/docs/internal`. `/docs/internal` is disabled when ENVIRONMENT=production. **Endpoint paths unchanged** — the split is OpenAPI-schema-only, so no dashboard/test code moved. Dual-auth dependency added so the public shared endpoints (analytics + config/weights) accept either an API key (pk_*) or a dashboard JWT. Public docs get a quick-start description + per-tag descriptions.
- 2026-05-13: Docs polish (deferred items from the split PR) — (1) every protected route declares 401/422 in OpenAPI; lender routes additionally declare 429 with documented Retry-After + X-RateLimit-* headers; admin routes add 403; detail routes add 404. (2) New description-only `Webhooks` tag in the public Swagger UI carries signature-verification examples in Python and Node + retry guidance. (3) OpenAPI version is read from `pyproject.toml` at startup (single source of truth). 217 tests (+4 new docs assertions). Rate-limit enforcement deferred to its own PR.
- 2026-05-13: Rate-limit enforcement — fixed-window per-tenant counter in Redis (`ratelimit:{tenant_id}:{minute}`) gates POST /v1/score, POST /v1/score/bulk, GET /v1/score/bulk/{job_id}, POST /v1/outcomes. Limits drawn from PLAN_RATE_LIMITS (PILOT 60, STARTER 200, GROWTH 500, SCALE 2000 req/min — matches docs/api-reference.md). New `enforce_rate_limit` dependency in `app/dependencies.py` wraps `get_current_tenant`, increments the counter, and either attaches `X-RateLimit-Limit/Remaining/Reset` headers on success or raises 429 with the same headers plus `Retry-After`. Bulk endpoints count as one ticket regardless of batch size. Dashboard JWT endpoints are unaffected. 224 tests (+7 new).
