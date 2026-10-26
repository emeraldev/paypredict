# Deployment guide — Fly.io + Neon (two environments)

Runbook for the live-URL deployment. **Staging** is where our own
testing + demo tenants + prospect clicks all land. **Production**
is where real lenders (first: Kalene) hit the API with real data.
Promotion from staging to prod is a manual GitHub Actions step
after a human smoke-check.

Stack:
- **Fly.io** — four app containers (`pp-{staging,prod}-{api,dashboard}`)
  plus two Fly Redis instances. All in `jnb` (Johannesburg).
- **Neon** — one Postgres project with two branches (`main` →
  production, `staging` → staging). AWS Frankfurt (`eu-central-1`).
  No Africa region on Neon; Frankfurt is the closest at ~160 ms RTT
  (verified against Neon's management-API region enum). The 160 ms
  cost is invisible on dashboard clicks and visible on API calls —
  acceptable at pilot volume; revisit when traffic grows (see
  "Postgres region: upgrade paths" below).
- **GitHub Actions** — merge to `main` → auto-deploy to staging;
  manual `workflow_dispatch` → deploy to prod.

Infra names use a bare `pp-<env>-<role>` convention (see
`context/branding.md`) — no placeholder product name baked in,
and when the platform rename lands it's a single
`pp-*` → `<new-name>-*` sweep.

---

## One-time setup

Do this **once** per environment, by hand. After it's done, deploys
are `git push` → GitHub Actions (staging) or dispatch button (prod).

### 1. Prereqs (accounts + tools)

- Fly.io account with billing enabled: <https://fly.io/trial>
  (Fly removed the free tier in late 2024; a card is required to
  create any app.)
- Neon account: <https://console.neon.tech/signup>
- `flyctl` installed locally: `curl -L https://fly.io/install.sh | sh`
  (or `brew install flyctl`).
- Log in: `flyctl auth login`.

### 2. Create the Neon Postgres project + staging branch

1. In the Neon console, create a new project:
   - **Name:** `pp`
   - **Region:** **AWS Frankfurt (`eu-central-1`)**.
   - **Postgres version:** 16
   - **Database name:** `paypredict` (if the UI defaults to
     `neondb`, overwrite to `paypredict`).
2. The default branch is `main`. That's **production**.
3. In the branches tab, click **Create branch**:
   - **Name:** `staging`
   - **Parent:** `main`
   - This creates a copy-on-write clone — instant, no data copy
     cost until the branches diverge. Both have their own
     compute endpoints and connection strings.
4. Copy BOTH connection strings (prod from `main`, staging from
   `staging`). Each looks like:
   ```
   postgresql://neondb_owner:<pwd>@ep-xxxx-pooler.c-6.eu-central-1.aws.neon.tech/paypredict?sslmode=require
   ```
5. **Rewrite the scheme** on each: `postgresql://` → `postgresql+asyncpg://`.
6. **Strip `&channel_binding=require`** if Neon's string includes
   it. That's a libpq-only parameter; asyncpg ignores it. The
   `sslmode=require` prefix already enforces TLS.
7. **Keep the default `-pooler` endpoint** — the app's SQLAlchemy
   engine (`api/app/database.py`) and Alembic's env
   (`api/alembic/env.py`) both pass
   `connect_args={"statement_cache_size": 0}` to asyncpg, which is
   the Neon-prescribed workaround for using PgBouncer
   transaction-mode pooling with asyncpg's named prepared
   statements. No need to swap to the direct endpoint.

Result: two values you'll paste into `DATABASE_URL`, one per env.

### 3. Create the four Fly apps + two Redis instances

```bash
# API apps (one per env).
flyctl apps create pp-staging-api  --org personal
flyctl apps create pp-prod-api     --org personal

# Dashboard apps.
flyctl apps create pp-staging-dashboard --org personal
flyctl apps create pp-prod-dashboard    --org personal

# Fly Redis — one per env, same jnb region. --plan free covers
# the staging workload; bump prod to --plan launch when we care
# about HA.
flyctl redis create --name pp-staging-redis --org personal --region jnb --plan free
flyctl redis create --name pp-prod-redis    --org personal --region jnb --plan free

# Each `redis create` prints a REDIS_URL — save both. Shape:
# redis://default:<pw>@fly-pp-<env>-redis.upstash.io:6379
```

If a name is already globally taken (Fly's app namespace is shared
across all accounts), pick a longer variant — e.g. `pp-score-api`.
Update `api/fly.staging.toml` / `fly.prod.toml` to match before
deploying.

### 4. Set per-app secrets

The API's `Settings._validate_secrets` refuses to boot outside
`{development, test}` without a real `JWT_SECRET_KEY` (32+ chars)
and `SECRET_KEY`. Everything else is a plain env var.

Both environments get their own set — generate independent secrets
so a staging compromise can't impersonate prod sessions.

```bash
# ---- STAGING ----
flyctl secrets set -a pp-staging-api \
  JWT_SECRET_KEY="$(openssl rand -hex 32)" \
  SECRET_KEY="$(openssl rand -hex 32)" \
  DATABASE_URL="postgresql+asyncpg://<staging-neon-string>" \
  REDIS_URL="<from pp-staging-redis>" \
  CORS_ORIGINS='["https://pp-staging-dashboard.fly.dev"]' \
  PUBLIC_API_URL="https://pp-staging-api.fly.dev"

# ---- PRODUCTION ----
flyctl secrets set -a pp-prod-api \
  JWT_SECRET_KEY="$(openssl rand -hex 32)" \
  SECRET_KEY="$(openssl rand -hex 32)" \
  DATABASE_URL="postgresql+asyncpg://<prod-neon-string>" \
  REDIS_URL="<from pp-prod-redis>" \
  CORS_ORIGINS='["https://pp-prod-dashboard.fly.dev"]' \
  PUBLIC_API_URL="https://pp-prod-api.fly.dev"
```

Notes:
- `ENVIRONMENT` is set in the per-env `fly.*.toml` `[env]` block
  (`staging` vs `production`), not here.
- `CORS_ORIGINS` is parsed as JSON by pydantic-settings. The outer
  single quotes are required so bash doesn't swallow the double
  quotes.
- `flyctl secrets set` restarts the app; a brief downtime (~10 s)
  is expected.

### 5. First deploy (from your laptop)

CI will handle subsequent deploys. The first run has to be
manual so the release command (`alembic upgrade head`) creates the
schema on each empty Neon branch.

```bash
# ---- STAGING ----
cd api
flyctl deploy --config fly.staging.toml --remote-only

cd ../dashboard
flyctl deploy --config fly.staging.toml --remote-only

# ---- PRODUCTION ----
cd ../api
flyctl deploy --config fly.prod.toml --remote-only

cd ../dashboard
flyctl deploy --config fly.prod.toml --remote-only
```

### 6. Seed demo data on STAGING only

```bash
flyctl ssh console -a pp-staging-api -C "python -m app.seed --reseed"
```

This creates the four demo tenants (SA card, ZM mobile money,
Fresh, Payroll) with admin/viewer/manager users. Prod stays empty
until a real lender is onboarded.

Credentials are printed to the machine's stdout — capture them via
`flyctl logs -a pp-staging-api --no-tail | grep -A20 "Dashboard Login"`.

### 7. GitHub Actions setup

Auto-deploy on merges to `main` (see `.github/workflows/deploy.yml`)
needs one repo secret:

```bash
flyctl tokens create deploy --name github-actions --expiry 8760h
```

Paste the output into GitHub → repo → Settings → Secrets and
variables → Actions → secret name `FLY_API_TOKEN`. One token
covers both environments.

**Also configure a GitHub Environment gate on `production`.** In
Settings → Environments → New environment → `production`, add a
required reviewer (yourself at minimum). The deploy workflow
references `environment: production` so this gate fires on every
prod deploy and nothing hits Kalene without a human click.

---

## Day-to-day operations

### Deploying

- **Staging (automatic):** merge to `main`. CI runs; on green, the
  Deploy workflow fans out to `pp-staging-api` then
  `pp-staging-dashboard`.
- **Production (manual):** GitHub Actions UI → "Deploy to Fly.io"
  → "Run workflow" → pick `environment: production` and `target:
  both`. The environment gate asks for your approval, then the
  deploy runs.
- **Hot-fix from your laptop:**
  `flyctl deploy --config api/fly.staging.toml` (or `fly.prod.toml`)
  from the app directory. Uses your local `FLY_API_TOKEN`.

### Rolling back

Fly keeps prior releases per app:

```bash
flyctl releases -a pp-prod-api
flyctl releases rollback -a pp-prod-api <version-number>
```

Rollback reverts the container image, NOT the database. If the
rolled-back version predates the current schema, the lifespan
startup check `assert_db_at_head` will refuse to serve. Alembic
down-migrations are guarded (see `app/migration_guards.py`); use
them deliberately.

### Logs + shell

```bash
flyctl logs -a pp-staging-api               # tail
flyctl logs -a pp-prod-api --no-tail        # historical
flyctl ssh console -a pp-staging-api        # shell into a machine
```

### Redeploy dashboard when API URL changes

`NEXT_PUBLIC_API_URL` is baked into the client bundle at build
time (Next.js inlines `NEXT_PUBLIC_*`). If an API URL ever
changes, you must rebuild the dashboard image:

```bash
cd dashboard
flyctl deploy --config fly.staging.toml --remote-only
```

(The build-arg is read from the `fly.*.toml` `[build.args]` block
so no CLI override is needed as long as the toml is up to date.)

### Refreshing staging data from prod

One of the main reasons we picked Neon branches: an instant
copy-on-write clone of prod lets us test migrations against
real-shape data without touching the live DB.

1. In Neon console → `pp` project → Branches → delete the
   current `staging` branch.
2. Create a fresh `staging` branch with `main` as parent.
3. Grab the new staging connection string.
4. `flyctl secrets set -a pp-staging-api DATABASE_URL="postgresql+asyncpg://<new-staging-string>"`
   — restarts the app with the fresh clone.

Staging now has a copy of prod data as of the branch moment. Mess
with it freely; prod is untouched.

### Rotating secrets

```bash
flyctl secrets set -a pp-prod-api JWT_SECRET_KEY="$(openssl rand -hex 32)"
```

Restart is automatic; existing JWTs are invalidated silently (the
PR #57 `password_changed_at` check also kicks every outstanding
session on next request).

---

## Postgres region: upgrade paths

Current setup is Neon in Frankfurt (~160 ms RTT to the Fly `jnb`
app). That's invisible on dashboard page loads (handful of mostly-
parallel queries), visible on API calls (a `POST /v1/score` does
2–3 serial round-trips → ~500 ms total instead of ~10 ms with a
co-located DB).

Fine for Kalene's pilot volume. Options when latency starts to
matter:

- **Fly Postgres (Unmanaged) in `jnb`** — ~2 ms RTT, co-located.
  One `flyctl postgres create --region jnb` command. We own
  backups, failover, version upgrades — Fly's docs list those as
  "under development" even on their Managed PG, and Unmanaged
  has none of them. OK for pilot with a scripted nightly
  `pg_dump` to S3 + documented monthly failover drill.
- **AWS RDS Postgres in `af-south-1`** (Cape Town) — ~5 ms RTT,
  fully managed by AWS. ~$15–20/month at `db.t4g.micro`. Needs
  a VPC + public endpoint or a Fly WireGuard peer; the Fly app
  connects via a new `DATABASE_URL`.

Migration from Neon to either option is a `pg_dump` + restore
+ `fly secrets set DATABASE_URL=...` — one afternoon when the
time comes.

---

## Known limits of this deployment

- **No Celery worker.** Bulk scoring at >50 items queues to Celery
  which is not deployed. Sync bulk (≤50) works fine. Fix by
  launching a worker app when we care.
- **No email transport.** Notifications land in the DB (dashboard
  bell works) but no email goes out. Stage 1 roadmap item #7.
- **Free-tier Fly resource envelope.** `shared-cpu-1x` + 512 MB
  covers staging comfortably and prod up to Kalene's pilot volume
  (~2 k borrowers across 4 branches). Bump to `shared-cpu-2x` /
  1 GB when we see sustained CPU > 70%.
- **No custom domain.** URLs are `pp-*.fly.dev`. Custom domains
  are deferred until the platform rename lands
  (`context/branding.md`).

---

## Rename-day changes

When the platform name is picked, these need updates in a single
sweep (see `context/branding.md` for the full inventory):

- **Fly apps**: `pp-{staging,prod}-{api,dashboard}` →
  `<new-name>-{staging,prod}-{api,dashboard}`. Each rename issues
  a new TLS cert; ~5 min downtime per app (do them one at a time).
- **Fly Redis**: `pp-{staging,prod}-redis` → same pattern.
- **Neon project name**: cosmetic; connection strings unaffected.
- **CORS_ORIGINS + NEXT_PUBLIC_API_URL + PUBLIC_API_URL**: new
  URLs via `flyctl secrets set` and a dashboard rebuild.
- **This guide's `pp-*` references** throughout.
- **`.github/workflows/deploy.yml`** prereq comments.
