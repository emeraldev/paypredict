# Deployment guide — Fly.io + Neon

This is the runbook for the Stage 0 demo deployment: a public URL a
prospect can click, hosted in Johannesburg (jnb) to keep round-trip
latency to Zambia + SA in the single-digit-ms range.

Stack:
- **Fly.io** — app containers (API + dashboard) and Redis. JNB region.
- **Neon** — managed serverless Postgres. JNB region.
- **GitHub Actions** — auto-deploy on merge to `main`.

Infra names are neutral placeholders (`pp-demo-*`) — the platform is
being renamed and we don't want branded infrastructure to accrue. See
`context/branding.md`.

## One-time setup

Do this **once** per environment, by hand. After it's done, deploys are
`git push` → GitHub Actions.

### 1. Prereqs (accounts + tools)

- Fly.io account: <https://fly.io/app/sign-up>
- Neon account: <https://console.neon.tech/signup>
- `flyctl` installed locally: `curl -L https://fly.io/install.sh | sh`
- Log in: `flyctl auth login`

### 2. Create the Neon Postgres project

1. In the Neon console, create a new project:
   - **Name:** `pp-demo`
   - **Region:** **AWS Frankfurt (`eu-central-1`)**. Neon has no
     Africa region (verified against their management-API region
     enum, 2026-10); Frankfurt is the closest, ~160 ms RTT to
     Johannesburg via the WACS submarine cable. See the latency
     trade-off note below.
   - **Postgres version:** 16
   - **Database name:** `paypredict`
2. From the Neon dashboard, copy the connection string. It looks like:
   ```
   postgresql://user:password@ep-xxxxx.eu-central-1.aws.neon.tech/paypredict
   ```
3. **Rewrite the scheme** to `postgresql+asyncpg://` — the API uses
   asyncpg, not the default psycopg driver. Neon supports asyncpg
   natively. If the connection string carries `?sslmode=require` at
   the end, keep it: asyncpg respects it.

Result: the value you'll paste into `DATABASE_URL` below.

**Latency trade-off (why Frankfurt is fine for Stage 0 and when it stops being fine).**
The app runs in Fly `jnb`; the DB sits in AWS `eu-central-1`
(Frankfurt). That's ~160 ms RTT per DB round-trip. A dashboard
page load does a handful of mostly-parallel queries so it adds
~200–500 ms over the perceived response, which no prospect
clicking around will notice. **A lender integrating via API is
different:** a `POST /v1/score` does 2–3 serial DB round-trips
(api-key lookup, score_request insert, score_result insert) so
the Frankfurt DB turns a ~10 ms call into a ~500 ms call. That's
visible in any load test and matters once we have a real
integrator.

**Postgres region: upgrade paths for Stage 1 (first live lender).**
When latency starts to matter, two options, in order of
operational cost:

- **Fly Postgres (Unmanaged) in `jnb`** — ~2 ms RTT, co-located
  with the app. One `flyctl postgres create --region jnb`
  command. You own backups, failover, and version upgrades —
  Fly's docs list those as "under development" even for their
  Managed PG, and Unmanaged has none of them. Fine for pilot
  scale (one or two tenants, we babysit) with a scripted
  nightly `pg_dump` to S3 and a documented monthly failover
  drill.
- **AWS RDS Postgres in `af-south-1`** (Cape Town) — ~5 ms RTT,
  fully managed by AWS (automated backups, point-in-time
  restore, snapshots, parameter groups, minor-version
  auto-upgrade). ~$15–20/month at the `db.t4g.micro` tier.
  Needs a VPC + public endpoint or a Fly WireGuard peer; the
  Fly app connects via a new `DATABASE_URL`.

Migration from Neon to either option is a `pg_dump` + restore
+ `fly secrets set DATABASE_URL=...` — one afternoon of work,
documented separately when we get there.

### 3. Create the Fly.io apps + Redis

```bash
# From the repo root.
cd api

# Create the API app (no deploy yet — we need to set secrets first).
flyctl apps create pp-demo-api --org personal

# Create Fly Redis in the same region. --plan free = 100 MB, single
# node. Bump to `--plan launch` for HA once we're past demo.
flyctl redis create --name pp-demo-redis --org personal --region jnb --plan free

# The `redis create` command prints a `REDIS_URL` starting with
# `redis://default:<password>@fly-pp-demo-redis.upstash.io:6379`.
# Save it — you'll paste it into the API's secrets below.
```

Same for the dashboard app:

```bash
cd ../dashboard
flyctl apps create pp-demo-dashboard --org personal
```

### 4. Set API secrets

The API's `Settings._validate_secrets` refuses to boot outside
`{development, test}` without a real `JWT_SECRET_KEY` (32+ chars) and
`SECRET_KEY`. Everything else is a plain env var.

```bash
cd api
flyctl secrets set -a pp-demo-api \
  ENVIRONMENT="staging" \
  JWT_SECRET_KEY="$(openssl rand -hex 32)" \
  SECRET_KEY="$(openssl rand -hex 32)" \
  DATABASE_URL="postgresql+asyncpg://<neon-connection-string>" \
  REDIS_URL="<from fly redis create>" \
  CORS_ORIGINS='["https://pp-demo-dashboard.fly.dev"]' \
  PUBLIC_API_URL="https://pp-demo-api.fly.dev"
```

Notes:
- `CORS_ORIGINS` is parsed as JSON by pydantic-settings. The single
  quotes around the outer value are required — bash otherwise
  swallows the double quotes.
- Generate new secrets on any leak. `flyctl secrets set` restarts the
  app; brief downtime (~10s) is expected.

### 5. First deploy (from your laptop)

CI will deploy from GitHub Actions on subsequent pushes, but the very
first deploy needs to run from your machine so the release command
(`alembic upgrade head`) creates the schema on an empty Neon DB.

```bash
# API — this runs `alembic upgrade head` as the release command
# before the first machine starts serving.
cd api
flyctl deploy --config fly.toml --remote-only

# Dashboard.
cd ../dashboard
flyctl deploy --config fly.toml --remote-only \
  --build-arg NEXT_PUBLIC_API_URL="https://pp-demo-api.fly.dev"
```

### 6. Seed the demo data

Once the API is up and the schema is at head, run the seed script
inside the running machine:

```bash
flyctl ssh console -a pp-demo-api -C "python -m app.seed --reseed"
```

This creates the four demo tenants (SA card, ZM mobile money, fresh
lender, payroll) with their admin/viewer/manager users. Credentials
are printed to the machine's stdout — capture them from
`flyctl logs -a pp-demo-api` or re-run and pipe.

### 7. GitHub Actions setup

Auto-deploy on merges to `main` (see
`.github/workflows/deploy.yml`) needs one repo secret:

```bash
# Generate a deploy-scoped token (avoid your personal token).
flyctl tokens create deploy --name github-actions --expiry 8760h
```

Paste the output into GitHub → repo → Settings → Secrets and
variables → Actions → `FLY_API_TOKEN`. Both `deploy-api` and
`deploy-dashboard` jobs use it.

## Day-to-day operations

### Deploying

- **Automatic:** merge to `main`. CI runs; on green, the Deploy
  workflow fans out to API then dashboard.
- **Manual:** GitHub Actions UI → "Deploy to Fly.io" → Run workflow.
  Pick target (both / api / dashboard).
- **Hot-fix from laptop:** `flyctl deploy --config <app>/fly.toml`
  from the app directory. Uses your local `FLY_API_TOKEN`.

### Rolling back

Fly.io keeps prior releases:

```bash
flyctl releases -a pp-demo-api
flyctl releases rollback -a pp-demo-api <version-number>
```

Note: this rolls back the container image, NOT the database. If the
rolled-back version predates the current schema, the app's
`assert_db_at_head` startup check will fail and the machine won't
serve. Alembic down-migrations are guarded — see
`app/migration_guards.py`.

### Logs + shell

```bash
flyctl logs -a pp-demo-api                 # tail
flyctl logs -a pp-demo-api --no-tail | ... # historical
flyctl ssh console -a pp-demo-api          # shell into a running machine
```

### Redeploy dashboard when API URL changes

`NEXT_PUBLIC_API_URL` is baked into the client bundle at build time
(Next.js inlines `NEXT_PUBLIC_*` vars). If the API URL ever changes,
you must **rebuild** the dashboard image, not just restart it:

```bash
cd dashboard
flyctl deploy --build-arg NEXT_PUBLIC_API_URL="https://new-api-url"
```

### Rotating secrets

```bash
flyctl secrets set -a pp-demo-api JWT_SECRET_KEY="$(openssl rand -hex 32)"
```

Restart is automatic; existing JWTs are invalidated silently
(clients will see 401 on their next call and be sent to `/login`).

## Known limits of this deployment

- **No Celery worker.** The bulk-scoring path uses Celery only for
  batches > 50 items. Sync bulk (≤50) works fine. If a demo user
  uploads a >50-row bulk request they'll get a `job_id` that never
  processes. Fix by launching a worker app when we care.
- **No email transport.** Notifications land in the DB (dashboard bell
  works) but no email goes out — Stage 1 item #7 in the roadmap.
- **Free-tier resource envelope.** Fly's shared-cpu-1x + Neon's free
  plan cover a demo but will not survive a real integration test.
  Move to `launch` plan on both before piloting.
- **No custom domain.** URLs are `pp-demo-*.fly.dev`. Custom domains
  are deferred until the platform rename lands
  (`context/branding.md`).

## Rename-day changes

When the platform is renamed, these need updates:

- `pp-demo-api` → `<new-name>-api` Fly app rename (issues new TLS
  cert; ~5 min downtime).
- `pp-demo-dashboard` → `<new-name>-dashboard` (same).
- `pp-demo-redis` → `<new-name>-redis`.
- Neon project name (cosmetic; connection string unaffected).
- `CORS_ORIGINS` + `NEXT_PUBLIC_API_URL` — rebuild dashboard image.
- This guide's `pp-demo-*` references throughout.

See `context/branding.md` for the full rename-day checklist covering
everything else in the codebase.
