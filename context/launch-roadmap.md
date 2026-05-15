# Launch Roadmap

This document maps everything that's *missing* from PayPredict against
the stage of customer engagement it would actually block. The goal is
to avoid two failure modes:

- **Premature work** — building AWS infra before there's a prospect to
  demo to.
- **Late discovery** — finding out we have no email transport on the
  day the first dashboard user complains they never got a notification.

Every item lists what it is, why it lives at this stage, a rough effort
estimate, and any dependencies. Stages are cumulative: Stage 2 assumes
everything in Stages 0–1 is done.

---

## Status today (2026-05-15)

- **236 tests passing**, CI green on every PR.
- Scoring + bulk + outcomes + analytics + backtest + notifications all work end-to-end.
- Timing optimiser shipped (Phase 4).
- Rate-limit enforcement shipped with per-tier limits + dual-auth.
- Public/internal Swagger docs split.
- **No live deployment**. Localhost only.
- **No prospects** yet — purely in development.

---

## Stage 0 — Demo-ready (show this to a prospect)

Goal: send a prospect a URL they can poke at; the prospect can log in,
see realistic seed data, click into a high-risk collection, see the
timing recommendation, and walk away thinking "this is a real product."

### Required

| # | Item | Effort | Why this stage |
|---|---|---|---|
| 1 | **Dockerfiles** for `api/` and `dashboard/` | 2-3 hours | Can't deploy anywhere without them. CLAUDE.md claims `api/Dockerfile` exists, but it doesn't. |
| 2 | **Hosted dev environment** (Fly.io or Railway) — Postgres + Redis managed, API + dashboard containers, HTTPS via Let's Encrypt | 3-4 hours | A localhost demo isn't a demo. Fly.io has built-in Postgres + Redis + HTTPS + a free tier. Defer AWS (Stage 2). |
| 3 | **Demo-friendly seed data on the live env** — runs `app.seed` on first deploy or via a one-off command | 30 min | Without this the live demo is empty. The seed already exists; just needs to run against the live DB. |
| 4 | **README "try the demo" section** with credentials | 15 min | Prospect needs to know what to do once they land on the URL. |

### Nice-to-have at this stage

- Custom domain (`demo.paypredict.dev` instead of `paypredict.fly.dev`) — 30 min, mostly DNS waiting
- Robots.txt / `noindex` so the demo doesn't get indexed — 5 min

### Out of scope here

Sentry, email, NextAuth, audit logs, AWS, Celery Beat — none of these block a prospect from clicking around. They block *operations*, which Stage 1+ handles.

**Total Stage 0 effort: ~half day.**

---

## Stage 1 — First pilot deal (free or paid pilot tier)

Goal: sign one lender to a pilot agreement. They send real
(small-volume) production traffic through our API. Possibly free,
possibly with a discounted tier. Failures here damage the relationship
even if they don't damage revenue yet.

### Required

| # | Item | Effort | Why this stage |
|---|---|---|---|
| 5 | **Production deploy target** — pick one: keep Fly.io and accept the limits, OR move to AWS af-south-1 ECS (matches the planned hosting region for SA latency) | Fly: 0 (keep Stage 0 infra); AWS: 2-3 days | Fly's fine for pilot volume. Switch to AWS when latency or compliance demands it (post-Stage 2). |
| 6 | **Sentry on both API and dashboard** | 2-3 hours total | First real error in prod will otherwise be invisible. CLAUDE.md tech stack already lists Sentry — make it true. |
| 7 | **Email transport for notifications** — SES or Postmark, plus a `dashboard_email_recipients` field actually getting messages | 4-6 hours | `Tenant.email_recipients` exists but mail goes nowhere. First "I missed an alert" complaint hits trust hard. |
| 8 | **Production seed / onboarding runbook** — markdown doc + a CLI script that provisions a new tenant: factor weights, first API key (returned once), webhook secret, ADMIN user, alert threshold | 3-4 hours | First customer's tenant must be created somehow. A repeatable script avoids hand-crafting SQL. |
| 9 | **Secrets via env, not committed config** — confirm no `.env` is in git, document required envs in a single place (probably `docs/deployment-guide.md`) | 1 hour | Already mostly true (`.env` is gitignored), but no checklist exists. |
| 10 | **DB backups** — Fly has snapshots, RDS has automated backups; document RPO (recovery point) target. Even "1-hour snapshots, 7-day retention" is fine for pilot. | 30 min | Loss of pilot data = loss of pilot. |
| 11 | **Webhook delivery confirmed against the pilot's endpoint** before go-live | 1 hour | We have webhook code + a per-tenant secret, but it's never delivered to a real lender URL. Smoke-test before the first paid event. |

### Nice-to-have at this stage

- Custom domain + branded `api.paypredict.com` — 1 hour
- Status page (statuspage.io or similar, free tier) — 1 hour
- Dashboard "Welcome, you're connected" banner that confirms the first webhook arrived — 2 hours

### Deferred to later stages

- NextAuth v5 — current JWT-in-localStorage works for pilot. Move to NextAuth when SSO or refresh-token security matters (Stage 3).
- SCALE custom rate-limit overrides — pilot won't be a SCALE customer (Stage 2 only if they hit STARTER limits).
- Backtest async path — pilot won't upload 500+ row backtests (Stage 2).
- Celery Beat scheduled checks — needs real-data threshold tuning (Stage 2).

**Total Stage 1 effort: ~3 days (Fly path) or ~1 week (AWS path).**

---

## Stage 2 — First 1–3 lenders live in production

Goal: pilot succeeded; they're running real collections through us
and reporting outcomes. Maybe one or two more lenders signed. We're
not at scale yet but we're *responsible* for revenue-impacting
decisions.

### Required

| # | Item | Effort | Why this stage |
|---|---|---|---|
| 12 | **Audit log for factor weight changes** — who changed which weight, when, from what value to what value. Read by both dashboard + a compliance-export endpoint. | 1-2 days | Lenders running real money through this need to be able to answer "who changed our model and when?" Notifications cover the event but not the value diff. |
| 13 | **Backtest async path (>500 items)** | 1 day | First customer with 6 months of history will exceed the sync cap. The Celery infra already exists for bulk scoring; reuse it. |
| 14 | **SCALE custom rate-limit overrides** — `Tenant.custom_rate_limit` nullable column, override in `get_limit_for_plan` | 2 hours | If even one lender's volume exceeds the STARTER cap (200/min), this becomes urgent. |
| 15 | **Per-tenant alerting on key health signals** — collection rate drop, prediction drift, unused API keys; scheduled via Celery Beat | 2-3 days | Hardcoded as Phase 3 deferred items. Worth doing once there's actual customer data to tune thresholds against. |
| 16 | **Operational runbook** — what to do when an alert fires, when webhook delivery fails, when scoring latency spikes | 1 day | Becomes essential as soon as we're on the hook for SLA. |
| 17 | **Real domain on `api.` and dashboard sub-domain** if not already done | 1 hour | At paid-customer stage, vanity URL matters. |

### Nice-to-have at this stage

- Per-tenant SLA dashboard — "your scoring p99 is X ms, your webhook success rate is Y%" — 2-3 days
- Self-service tenant settings beyond what's there (e.g. configurable alert thresholds) — already partly built

### Deferred to later stages

- Per-item bulk rate-limit weighting — defer until evidence of abuse (Stage 3+)
- ML model training — needs >6 months of labelled data (Stage 4)

**Total Stage 2 effort: ~1-2 weeks of focused work.**

---

## Stage 3 — Growth (3-10 customers, scaling)

Goal: several lenders live, growing volume. Reliability and depth
matter more than new features.

### Required

| # | Item | Effort | Why this stage |
|---|---|---|---|
| 18 | **AWS af-south-1 deployment** if still on Fly — ECS Fargate, RDS Postgres, ElastiCache Redis, ALB, ACM cert, secrets via Parameter Store, ECR registry, deploy pipeline via GitHub Actions | 1-2 weeks | Fly is fine until you need af-south-1 latency for SA customers and compliance posture for serious lenders. |
| 19 | **Cohort analytics** — slice analytics by `factor_set`, `plan`, `market`, customer cohort (instalment number, payment-history bucket). Surfaces in the dashboard analytics page. | 1-2 days | "Where is the model breaking?" question becomes critical with multiple customers and segments. |
| 20 | **NextAuth v5 on dashboard** — SSO via OIDC, refresh-token rotation, MFA option | 1-2 days | Multi-customer access patterns + compliance pressure push this from "deferred" to "expected". |
| 21 | **A/B weight testing** — let a tenant route 5% of traffic through an alternate weight config and see the lift | 2-3 days | Lenders tuning their own model is a power-user feature that justifies higher tiers. |
| 22 | **Status page + uptime monitoring** — public SLA visibility | 1 day | Expected at this customer count. |

### Nice-to-have at this stage

- Per-item bulk rate-limit weighting if we see abuse — 2 hours
- Per-endpoint rate limits (different ceiling for analytics vs scoring) — 2 hours

**Total Stage 3 effort: ~3-4 weeks of focused work, mostly the AWS migration.**

---

## Stage 4 — ML transition (10+ customers, 6+ months of labelled data)

Goal: replace heuristic factors with ML models where ML provably beats
the heuristic. The architecture was designed for this from day one
(immutable scores, labelled outcomes, factor registry).

### Required

| # | Item | Effort | Why this stage |
|---|---|---|---|
| 23 | **Labelled dataset export** — `GET /v1/datasets/labelled?from=YYYY-MM-DD` streams `(features, outcome)` pairs as Parquet or CSV. Goes through the same auth + tenant filtering as scoring. | 1 day | Foundation for everything ML. |
| 24 | **Feature engineering pipeline** — extract reproducible features from the stored request_payload + outcome history | 1 week | Heuristic factors already encode some of these; ML wants richer inputs. |
| 25 | **Model training + evaluation** — choose framework (probably scikit-learn for v1), train per `factor_set`, evaluate against held-out outcomes, compare to heuristic baseline | 2-4 weeks | The actual ML work. Pre-requisite: enough labelled data per `factor_set` (rule of thumb: 10k+ resolved outcomes). |
| 26 | **Model serving** — register trained models alongside heuristic factors; engine picks model when available; falls back to heuristic if model load fails | 1 week | The "ML replaces heuristics without API contract change" promise from day one. |
| 27 | **Model versioning + rollback** — store model artefacts, track which version scored which collection, support per-tenant rollback | 1 week | Required for compliance and trust. |

**Total Stage 4 effort: 2-3 months. Not before Q4 2026 at the earliest.**

---

## Summary at a glance

| Stage | Trigger | Cumulative effort | Status |
|---|---|---|---|
| 0 — Demo ready | Sending a URL to a prospect | ~half day | **Not started** |
| 1 — First pilot | Pilot agreement signed | +3 days (Fly) or +1 week (AWS) | **Not started** |
| 2 — Live with 1-3 lenders | First paid invoice | +1-2 weeks | **Not started** |
| 3 — Growth | 3-10 customers | +3-4 weeks (mostly AWS migration) | **Not started** |
| 4 — ML transition | 10+ customers, 6mo data | +2-3 months | **Not started** |

---

## What we are *not* prioritising (and why)

- **NextAuth v5 right now** — current JWT-in-localStorage is fine until Stage 3. Premature complexity.
- **Sentry/CloudWatch at Stage 0** — nothing in prod to monitor. Stage 1 is the right moment.
- **Per-item bulk rate-limit weighting** — no abuse data. Wait for evidence.
- **AWS deploy at Stage 0** — Fly.io gets us a live URL in hours, not days. Stage 3 is when latency/compliance forces the migration.
- **ML before 6 months of data** — not enough signal to beat the heuristic baseline.

---

## How to use this doc

When you're considering a new piece of work, find which Stage it
belongs to. If it's in a Stage further out than where the company
currently is, it's by definition premature — push back or defer.

Update the **Status today** section at the top whenever a Stage
becomes "in progress" or "complete." Treat this as a living document,
not a contract.
