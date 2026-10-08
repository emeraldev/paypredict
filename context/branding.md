# Branding & Naming

**Status (2026-09-16):** the current codename `paypredict` (and its
capitalised form `PayPredict`) is a **working placeholder**. The team
is actively searching for a permanent name and checking domain
availability. Nothing in this section is settled — a rename is
expected before the first pilot goes live.

## Rules of thumb until the rename lands

- **Do not purchase domains, register trademarks, or provision
  branded infrastructure** (Fly.io app names, Neon project names,
  DNS records, SES verified sender, custom TLDs, ...) under
  `paypredict.*`. Pick neutral placeholder names for infra so a
  rename doesn't force us to re-issue TLS certs, re-verify email
  senders, or update every integrator's DNS. Current convention
  (see `docs/deployment-guide.md`): a bare `pp-<role>` prefix —
  `pp-api`, `pp-dashboard`, `pp-redis`, Neon project `pp`. No
  environment suffix today ("staging" / "demo" / "prod" would
  create their own rename trap when we eventually split
  environments); add one at that point and name the new
  environment, not this one.
- **Do not put the current name in customer-facing copy for a live
  demo.** Screenshots, email templates, one-pagers, and pitch decks
  should say "the platform" or use a neutral working label until
  the name is fixed.
- **New code is fine to write with the current name inline** —
  removing it later is a mechanical sweep. The point is that we
  don't accrue *external* obligations (domains, certs, integrator
  contracts) under a name we're about to drop.
- **The rename does NOT need to happen before Stage 0 demo hosting**
  as long as (a) infra names are neutral, (b) the URL you send a
  prospect is a plain Fly.io / Vercel / Cloudflare domain rather
  than a custom domain, and (c) the dashboard's login page copy is
  either neutral or clearly-in-progress.

## Where the current name is baked in (grep-based inventory)

Kept up to date so on rename day we don't rediscover touchpoints
under time pressure. Grouped by cost-to-change and audience.

### A. Wire-protocol identifiers — coordinate with any integrator

Anyone who wrote code against our API depends on these. A rename
without a migration window forces breaking changes on every live
integrator.

- **`X-PayPredict-Event` / `X-PayPredict-Signature` /
  `X-PayPredict-Delivery`** webhook headers, in
  `api/app/services/webhook_service.py` (defined) and
  `api/app/api/docs_config.py` + `docs/api-reference.md`
  (documented). Integrators verify signatures on these header
  names.
- **API-key prefix `pk_test_` / `pk_live_`** — generic enough that
  it might survive the rename verbatim (Stripe uses the same
  shape), or we may want new prefixes tied to the new name.
  Defined at seed / mint time (`api/app/services/api_key_service.py`,
  `api/app/seed.py`).
- **Webhook-secret prefix `whsec_`** — generic; same argument as
  above.
- **DB / user names** on Postgres (`paypredict`, `paypredict_dev`,
  `paypredict_test`) — visible to anyone with production DB access
  but not to lender integrators. Cheap to change on a fresh install,
  destructive to change on an existing DB. See section D.

### B. Customer-facing UI copy (mechanical sweep on rename day)

Only visible once a live customer opens the dashboard, so no
external contract is at stake. Every hit is a two-line PR to
replace the string.

- **HTML `<title>`** — `dashboard/src/app/layout.tsx:19`.
- **Login page** — `dashboard/src/app/login/page.tsx:41`
  (`"Sign in to PayPredict"`).
- **Sidebar + topbar brand text** —
  `dashboard/src/components/layout/mobile-sidebar.tsx:19`,
  `dashboard/src/components/layout/topbar.tsx:49`.
- **Onboarding copy** —
  `dashboard/src/components/dashboard/collections-onboarding.tsx:126`.
- **Backtest comparison** — `"With PayPredict"` label in
  `dashboard/src/components/backtest/collection-rate-comparison.tsx:23`.
- **Alerts tab** — mentions `X-PayPredict-Signature` header name and
  "verify the request came from PayPredict" copy
  (`dashboard/src/components/settings/alerts-tab.tsx:135, 167, 168`).
- **API-keys tab** —
  `dashboard/src/components/settings/api-keys-tab.tsx:43, 44`.
- **API docs description** — `api/app/api/docs_config.py`,
  `api/app/main.py` (`title="PayPredict API"`).

### C. CSV filenames + browser storage keys (self-contained, low cost)

- **`localStorage` keys** — `paypredict_token` (JWT storage) and
  `paypredict-theme` (light/dark preference). Migrating these
  cleanly on rename means shipping a one-time helper that reads
  the old key and writes the new one, so a signed-in user doesn't
  get bounced to `/login` on the rename deploy.
  Files: `dashboard/src/lib/api/client.ts:4`,
  `dashboard/src/lib/api/scores.ts:80`,
  `dashboard/src/lib/api/backtest.ts:17`,
  `dashboard/src/hooks/use-theme.tsx:22`.
- **CSV download filenames** —
  `paypredict-collections-<date>.csv`,
  `paypredict-outcomes-<date>.csv`,
  `paypredict_scored_<date>.csv`, and
  `paypredict_scoring_template.csv`. Files:
  `dashboard/src/app/dashboard/page.tsx`,
  `dashboard/src/app/dashboard/outcomes/page.tsx`,
  `dashboard/src/components/score/scored-rows-table.tsx`,
  `api/app/api/v1/scores.py` (template).
- **Webhook receiver placeholder** — the example URL in
  `alerts-tab.tsx:135` uses `/paypredict-webhook`. Cosmetic.

### D. Infrastructure & config (cheap on a fresh install, real churn on migration)

Change on a fresh deploy costs one PR. Change on a running system
means either a Postgres role rename + connection-string sweep or
a full DB migration to a new cluster.

- **Postgres role + database names** —
  `.github/workflows/ci.yml` (POSTGRES_USER, POSTGRES_DB),
  `api/docker-compose.yml`, `api/init-db.sql`, `api/alembic.ini`
  (default DATABASE_URL), `api/app/config.py` (default
  DATABASE_URL).
- **Python package name** — `api/pyproject.toml:6`
  (`name = "paypredict"`).
- **Docker container names** — `api/docker-compose.yml` implicitly
  (Compose uses the directory basename `api-postgres-1` etc.). No
  code change needed if the directory is renamed.

### E. Seed / demo data (safe to rename any time)

- **Demo user emails** — `admin@demo-sa.paypredict.dev` and its
  siblings across markets, in `api/app/seed.py:591–644`. Migrated
  in PR #57's password-policy update; will need another sweep when
  the name changes.
- **Test fixture emails** — `admin@paypredict.test` and siblings
  in `api/tests/conftest.py`. Purely local, no external
  coordination needed.

### F. Documentation

- `CLAUDE.md`, `README.md`, `docs/*.md`, `context/*.md`. Mechanical
  find-and-replace; some human review needed to catch cases where
  the current name is used generically vs. as a brand.

### G. Historical (leave alone)

- Alembic migration file at `5b17a75fd7b3` documents the day the
  hardcoded webhook secret `paypredict` was replaced by
  `whsec_<random>`. That reference is a historical artefact and
  should NOT be touched on rename.

## Constraints for the new name (fill in as decided)

Placeholder — populate as the search narrows.

- **Domain availability:** `<primary>.<tld>` must be available for
  purchase.
- **Trademark:** clean against SA and Zambia registries at minimum.
- **Pronunciation:** English-pronounceable; ideally also
  Nyanja / Bemba / Zulu friendly (short vowel-heavy roots tend to
  travel well).
- **Length:** short enough to look good in a topbar (~10 chars
  max) and read cleanly in an email domain.
- **Meaning:** doesn't collide with existing lending brands
  (Lulalend, Lumo, JUMO, Kongola, etc.) or Zambian financial
  household names.
- **Sub-brands:** works alongside product names ("<Name> Score",
  "<Name> Insights", etc.) if we ever split.

## Rename-day checklist (draft)

Once a name is picked, this section becomes the PR plan:

1. Section A wire-protocol identifiers, coordinated with any live
   integrator via a deprecation window (both old and new headers
   emitted for one release).
2. Section B UI-copy sweep — one PR, mechanical.
3. Section C localStorage + CSV filename sweep — one PR with the
   one-time key migration helper described above.
4. Section D infra rename — Postgres roles + DB names + Python
   package name. Requires a downtime window or a blue-green cutover.
5. Section E seed + fixture sweep — one PR.
6. Section F docs sweep — one PR.
7. Domain purchase, DNS cutover, TLS re-issuance, SES verified
   sender registration, GitHub org rename if applicable, package
   registry updates. Out of scope of any code PR.
