# Pilot onboarding runbook

One command to provision a new lender tenant on prod. Captures what
`app.seed` does for the demo tenants, but for a real customer:
no demo data, no fake scores, policy-compliant admin credentials,
`pk_live_` API key.

## Prereqs

- SSH access to the prod API Fly app: `flyctl auth whoami` returns
  the account that owns `pp-prod-api`.
- The lender's details:
  - Display name (e.g. `Kalene Lending`)
  - Market (`SA` or `ZM`)
  - Factor set (`CARD_DEBIT`, `MOBILE_WALLET`, `PAYROLL`)
  - Which `collection_method`s to seed weights for
  - Head-of-ops email + name
  - Plan tier (default `PILOT` — 60 req/min; `STARTER` is 200)

## Run the provision

From your laptop:

```bash
flyctl ssh console -a pp-prod-api -C "python -m scripts.provision_tenant \
  --name 'Kalene Lending' \
  --market ZM \
  --factor-set PAYROLL \
  --plan STARTER \
  --admin-email ignatius@kalene.co.zm \
  --admin-name 'Mr. Ignatius' \
  --methods PAYROLL \
  --api-key-label 'Production key'"
```

**Dry-run first** to confirm the inputs are what you intend, before
touching prod:

```bash
flyctl ssh console -a pp-prod-api -C "python -m scripts.provision_tenant \
  ... same flags ... \
  --dry-run"
```

A `--dry-run` opens a transaction, runs every write, then rolls back
cleanly — nothing persists. Any validation failure (duplicate admin
email, invalid method name) surfaces here before the real run.

## What gets created

- One `Tenant` row with your display name + market + factor_set.
- One `User` row — the admin, with a 20-character random password
  that meets the platform policy (upper, lower, digit, symbol).
  `password_changed_at` is stamped so JWT revocation works.
- One `FactorWeight` row per factor per supplied `collection_method`,
  seeded from `app.scoring.registry.get_default_weights_for_method`.
- One `ApiKey` row with the lookup_id + bcrypt hash. The raw key is
  shown ONCE in the output and never recoverable.

All in one DB transaction — any failure aborts without partial state.

## The output

The script prints a non-secret summary first (safe to log, screenshot,
share with your team), then a credentials block at the bottom. The
credentials block is the ONE time the admin password and raw API key
appear anywhere. Capture them before closing the terminal.

Shape:

```
Tenant ID:    <uuid>
Tenant name:  Kalene Lending
Methods:      PAYROLL
API key:      pk_live_<lookup>  (label: Production key)

========================================================================
CREDENTIALS — capture these NOW; they are not recoverable.
========================================================================

Dashboard login: ignatius@kalene.co.zm
Dashboard pw:    <20 chars>

API key (full):  pk_live_<lookup>_<secret>
```

## Hand over to the lender

Send on a secure channel (not plain email):

1. **Dashboard URL:** `https://pp-prod-dashboard.fly.dev`
2. **Admin login + password** (from the credentials block)
3. **API key** (from the credentials block)
4. **API docs:** `https://pp-prod-api.fly.dev/docs`
5. **A one-liner on what to do first:**
   > "Visit the dashboard, change your password immediately on
   > Settings → Profile, then start uploading scoring requests via
   > the API or via the Score Collections page. Each API request
   > needs an `Authorization: Bearer <API key>` header."

## After-provision checklist

- [ ] Confirm the lender can sign in (ask them to try, don't guess)
- [ ] Confirm they rotated the admin password
- [ ] Watch Fly logs on the first few API calls:
      `flyctl logs -a pp-prod-api | grep <tenant-id>`
- [ ] If they want a webhook: hand them the signing secret via a
      separate channel (the dashboard also shows it on Settings →
      Alerts)

## Rolling back a mis-provisioned tenant

The script has no un-do command. If you provisioned incorrectly:

1. Mark the tenant inactive via SQL:
   `UPDATE tenants SET is_active = false WHERE id = '<uuid>';`
2. Deactivate the API key:
   `UPDATE api_keys SET is_active = false WHERE tenant_id = '<uuid>';`
3. Re-run the provision with the correct inputs under a NEW email.

Don't `DELETE` — the audit trail (`activity_log`, `weight_change_log`)
references the tenant_id and FK cascades would wipe real history. The
`is_active = false` posture is the correct offboarding path and is
what we'll use when a tenant leaves.
