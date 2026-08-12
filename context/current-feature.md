# Current Feature

All core phases complete. Next: deployment, Phase 4 features, or polish.

See [launch-roadmap.md](./launch-roadmap.md) for the stage-by-stage
prioritisation of remaining work (demo → pilot → live → growth → ML).

## Status

Phase 3 complete. Phase 4 timing optimiser shipped. Role enforcement landed. Weights are per collection method (silent cross-method bug fixed). CI green on every PR. 306 tests passing.

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
- 2026-05-14: Rate-limit follow-up: dual-auth coverage — extended enforcement to the shared endpoints (`GET /v1/analytics/*`, `GET/PUT /v1/config/weights`) **when called via API key**. JWT callers (the dashboard team) still bypass entirely — they can never throttle themselves. Refactored shared logic into `_apply_rate_limit` helper; new `enforce_rate_limit_or_jwt` dep replaces `get_tenant_from_either` on those routes. 3 new tests cover (a) API-key path is rate-limited, (b) JWT path emits no headers and never 429s, (c) JWT calls don't consume the tenant's API-key bucket. 227 tests total.
- 2026-05-14: Phase 4 — Timing optimiser shipped. New `app/scoring/timing_optimiser.py` re-runs the existing `ScoringEngine` across ±14 days around the original `collection_due_date` (skipping past dates) and picks the lowest-score candidate. When the improvement is ≥ 0.10, the response sets `recommended_action: "shift_date"` and populates new fields `recommended_collection_date`, `recommended_score`, `score_improvement`. Two new persisted columns (Alembic migration `9ce5ceb0356c`). Wired through single-score, bulk sync, and Celery async paths. Drawer surfaces the recommendation with a "Risk drops by N pts" callout. 9 new tests (7 unit + 2 integration); 236 total.
- 2026-05-15: Role enforcement — `ADMIN` / `MANAGER` / `VIEWER` were label-only before this. Now properly enforced: new `require_admin_or_manager` dep in `app/dependencies.py`, `require_admin` extended to gate every mutating tenant-config endpoint. **Locked down**: API key CUD, factor-weight PUT (JWT path only — API-key path still trusted), alert-config PUT + regenerate-secret are Admin-only; backtest POST + POST `/upload` are Admin-or-Manager (replaces an inline helper). `useAuth()` exposes `isAdmin` + `canManage`; dashboard hides or disables every mutating control accordingly and hides the Team tab entirely from non-admins. 10 new tests pin the role × endpoint matrix (403 for every forbidden combination). 246 total.
- 2026-08-08: Weights per collection method — `factor_weights` now unique on `(tenant_id, collection_method, factor_name)`; the scoring engine picks the factor bundle from each request's `collection_method` rather than the tenant's `factor_set` (which is retained for backward compat but no longer read by scoring). Fixes the silent bug where bulk + CSV rows with mixed methods were forced through one bundle. `GET /v1/config/weights` returns a grouped view (one entry per method the tenant uses); `PUT` targets one method at a time with cross-method isolation. Dashboard weights tab is now sub-tabs per method with per-tab save + unsaved-changes dot. Backend + frontend both add per-method labels + plain-English copy. Migration `52f6a4d1b0c9` backfills existing tenants (CARD_DEBIT → CARD + DEBIT_ORDER rows preserving tuning). New `weights_service.py` centralises reads/writes. 306 tests (+57 new + rewritten).

- 2026-05-25: API field rename — drop `external_` prefix on the public API. Lender perspective: those are *their* IDs, not "external" ones. Pydantic request/response schemas now use `customer_id` and `collection_id`; service layer maps to the unchanged DB columns (`external_customer_id` / `external_collection_id`) at the boundary. Touched: 6 schemas, 7 services, 1 task, 9 backend tests, the E2E script, the backtest CSV template + column headers, sort_by query value (`?sort_by=customer_id`), all dashboard types + components reading these fields, and docs/api-reference.md / operational-guide.md / README. `docs/data-model.md` left as-is because it describes the DB schema. Pre-deploy was the cheapest moment to do this — no integrators broken. 249 tests still passing, dashboard builds clean.
- 2026-05-18: Contextual help — new reusable `HelpPopover` (`?` icon → small popover with title + body) used inline at the highest-jargon spots: (a) risk-detail-drawer next to "Recommended Action" lists what to do for each of the 4 action values, (b) Backtest stat cards explain `Predicted Accuracy` and `Est. Annual Recovery` (the latter calls out it's an upper bound), (c) Settings → Weights explains why Total must equal 100% and the skip-and-re-normalise behaviour. `StatCard` gained an optional `titleHelp` slot. Help is *available* not *demanded* — muted icon until hover, doesn't compete with the surrounding content.
- 2026-05-16: Lender onboarding UX — six focused fixes to make the tool intuitive cold. (1) Empty-state on `/dashboard` replaced with an onboarding panel: "Create API key → Make your first call" with a real curl example and a copy button. (2) Hero copy added to Backtest, Outcomes, and Settings → Weights so first-time users understand what each page is for. (3) New `shift_recommended` count on `ScoresSummary` (`scores_service` query + `scores_list` schema); dashboard shows a callout banner when the timing optimiser has flagged shifts. (4) `docs/operational-guide.md` — opinionated mapping from each `recommended_action` value to a real collection-pipeline workflow, plus the score-vs-risk-level decision guide and an integration minimum-viable checklist. README + public Swagger description link to it. (5) Native `title` tooltips on jargon terms: Match/Matched/Mismatched filter tabs, the Match column header, and the Backtest/Outcomes sidebar items. (6) Public OpenAPI description now lists the highest-impact `customer_data` fields per factor set so integrators know which fields actually move the score.
- 2026-08-12: Weight-change audit log + per-score weights snapshot (roadmap Stage 2 #12, shipped ahead of schedule). Answers the two compliance questions a live lender asks: (a) "who changed which factor and when, from what to what?" — new append-only `weight_change_log` table (migration `d4e8c1f95a72`), every mutation writes entries in the same DB transaction as the actual `factor_weights` change so state and audit can never diverge; admin-only `GET /v1/config/weights/history` paginated + method/factor-filterable; dashboard renders a Change History card on Settings → Weights with `old → new` deltas colour-coded by direction. (b) "reproduce this score under its exact-at-time config" — new `score_results.weights_snapshot` JSONB column captures the full pre-normalisation weight vector (all factors including skipped) on every new score. Verified score immutability was already correct (zero UPDATE code paths on `score_results`); this PR only added the missing audit + reproducibility layer, no scoring behavior changed. 384 tests (+7 new). Follow-up: compliance-export CSV endpoint — data layer is ready.
