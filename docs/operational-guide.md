# Operational Guide

How to turn PayPredict's risk score and `recommended_action` into real
collection workflow decisions. This is the missing manual between
"we got a score back" and "what does my ops team do with it."

---

## The decision surface

Every `POST /v1/score` response carries three signals that should drive
your downstream decision:

| Field | Meaning |
|---|---|
| `score` | Continuous 0.0–1.0 risk of failure. Use this when you need a number (e.g. for prioritising a queue). |
| `risk_level` | Discrete `LOW` / `MEDIUM` / `HIGH`. Use this when you need a category (e.g. routing to a workflow). |
| `recommended_action` | Opinionated suggestion — what we'd do with this collection if we ran your operations. |

Score thresholds map directly to risk levels:

| Score range | Risk level |
|---|---|
| `0.00 – 0.30` | `LOW` |
| `0.31 – 0.60` | `MEDIUM` |
| `0.61 – 1.00` | `HIGH` |

If you want a single number to gate everything, use `score`. If you want
to bucket collections into pipelines, use `risk_level`. If you want us
to do the thinking, follow `recommended_action`.

---

## The `recommended_action` values

There are four. Each maps to a different operational response:

### `collect_normally`

> "This collection looks healthy. Run your standard process."

- **Typical risk profile**: `LOW` (score ≤ 0.30)
- **What to do**: Attempt the collection on the scheduled date through
  your normal pipeline. No special handling.
- **What NOT to do**: Don't manually intervene — the model is telling
  you the customer history, timing, and balance signals all look fine.

### `pre_collection_sms`

> "The collection is borderline. A nudge will probably help."

- **Typical risk profile**: `MEDIUM` (score 0.31–0.60)
- **What to do**: Send a reminder to the customer 24–48 hours before
  the collection date. SMS, email, or push — whatever your customer
  base responds to. Then attempt the collection on schedule.
- **Why this works**: Most medium-risk failures are timing/awareness
  issues (low balance customer who didn't realise the debit was due).
  A nudge gives them time to top up.

### `flag_for_review`

> "Don't attempt this collection blindly. Have a human look first."

- **Typical risk profile**: `HIGH` (score ≥ 0.61)
- **What to do**: Route the collection to a manual queue. Check the
  `factors` array for *why* it's high risk — a card-expiry case
  needs different handling than a customer with 6 recent debit-order
  returns.
- **Action menu** for a human reviewer:
  - **Card expired / declined recently**: request a new card before
    attempting.
  - **Insufficient-funds pattern**: shift the date (see below) or
    contact customer.
  - **Customer has multiple active loans**: escalate — they may be in
    financial distress.

### `shift_date`

> "The original date is bad timing. Move it to one we found that's
> meaningfully lower risk."

- **Trigger condition**: The timing optimiser found a date in
  `[due_date − 14, due_date + 14]` that scores ≥ 0.10 lower than the
  original.
- **Three extra fields populate** when this action fires:
  - `recommended_collection_date` — the new date we recommend
  - `recommended_score` — what the score would be on that date
  - `score_improvement` — how much risk drops
- **What to do**: Reschedule the collection. If your downstream system
  doesn't support rescheduling, fall back to `pre_collection_sms` for
  the original date.
- **What NOT to do**: Don't shift by tiny amounts on your own — the
  optimiser already filtered out shifts smaller than 0.10. If we don't
  return `shift_date`, no meaningful shift exists.

---

## Mapping to a typical queue

A common pattern lenders adopt:

```
score response
   │
   ├─ shift_date         ──► Rescheduled queue
   │                          (auto-shift to recommended_collection_date)
   │
   ├─ flag_for_review    ──► Manual review queue
   │                          (look at factors, decide action)
   │
   ├─ pre_collection_sms ──► Nudge queue
   │                          (send 24-48h reminder, then collect)
   │
   └─ collect_normally   ──► Standard collection pipeline
                              (no human, run on schedule)
```

You don't have to implement all four pipelines on day one. The minimum
useful integration is:

1. Always send `POST /v1/score` before attempting a collection.
2. Route `flag_for_review` to a human (or just don't attempt that day).
3. Treat the other three the same for now — just collect on schedule.

Even at that minimum level of integration, the expected effect is to
stop wasting attempts on the clearly-doomed collections — how much
that lifts your collection rate depends on your existing failure
distribution. Use the Backtest tool against your own historical data
to see the projected lift before changing your live pipeline.

---

## What to feed back via `POST /v1/outcomes`

After every collection attempt — successful, failed, or partial —
report the result via `POST /v1/outcomes`. Include the `score_id` you
got back from the original score; that's what builds the labelled
training data behind the model's accuracy over time.

```bash
curl -X POST https://api.paypredict.com/v1/outcomes \
  -H "Authorization: Bearer pk_live_..." \
  -H "Content-Type: application/json" \
  -d '{
    "score_id": "sr_abc123...",
    "external_collection_id": "your_collection_id",
    "outcome": "FAILED",
    "failure_reason": "insufficient_funds",
    "attempted_at": "2026-04-15T08:00:00Z"
  }'
```

Outcomes you don't report are outcomes the model can't learn from.
Report every attempt, ideally within a few days — the labelled data
is what improves accuracy over time.

---

## What you'll see on your dashboard

- **Dashboard home** — risk-ranked table of upcoming collections.
  Sortable by score / due date / amount / customer / method.
- **Analytics** — collection rate over time, prediction accuracy,
  factor contributions. Compare this period vs. last period to see if
  your operational changes are working.
- **Outcomes** — every reported outcome with the predicted risk
  alongside, plus a "Matched / Mismatched" filter so you can audit
  where the model called it right vs. wrong.
- **Backtest** — re-score past collections against a new weight
  configuration to validate the change before saving.
- **Settings → Weights** — control how much each factor contributes.
  Use the Backtest tool first to validate any change.

---

## Signals worth investigating

Patterns in your own dashboard that are worth a closer look:

- **Collection rate drops sharply** with no operational change on your
  side — could indicate model drift. Run a backtest against the
  affected period to compare against the live model.
- **A specific factor consistently scores 0.0** in the response —
  likely missing input data on your side; check that the optional
  `customer_data` fields for that factor are being sent.
- **`recommended_action` keeps returning `flag_for_review` for a
  large share of collections** — your weights may be skewed toward
  HIGH risk. Try tuning the weight on `historical_failure_rate` (the
  highest-impact factor) and validate the change with the Backtest
  tool before saving.
