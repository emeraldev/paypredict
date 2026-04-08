# PayPredict — Business Context

This document provides business context for engineering decisions. It explains WHY the product exists, WHO it serves, and WHAT constraints shape the technical choices.

---

## The problem

Lenders in Africa process thousands of instalment collections daily. Most treat every collection identically — same priority, same timing, same retry logic. When collections fail, they react after the fact instead of predicting and preventing failures.

Default rates across African lending are extreme:
- BNPL in South Africa: 20-35% of collections fail
- Mobile money micro-loans in Kenya/Zambia: 30-65% default rates
- SA digital personal lenders: rising defaults with 38% of credit customers in arrears

The cost: lost revenue, wasted PSP/MNO transaction fees on failed attempts, ops teams spending time on manual review instead of proactive intervention.

## What PayPredict does

A pre-collection risk scoring API that predicts which upcoming collections will fail BEFORE the attempt, scored from 0 (safe) to 100 (will fail). Returns a risk level, factor breakdown, and recommended action.

The scoring starts with configurable heuristic rules (no ML yet). Every scored collection + its real outcome creates labelled training data for future ML models. The product gets smarter automatically over time.

## Target customers

### South Africa (launch market)
- **BNPL providers:** Float, PayJustNow (2.6M customers), Payflex, HappyPay
- **Digital personal lenders:** Finchoice (1.1M users), Wonga, Boodle
- **MNO lending:** MTN QwikLoan (via JUMO), Vodacom VodaLend

### Zambia (second market)
- **Mobile money lenders:** MTN Kongola, Airtel Nasova (both via JUMO)
- **Micro-lenders:** ExpressCredit, Kazang
- **MNOs directly:** MTN Zambia, Airtel Zambia

### Strategic customer: JUMO
JUMO is the lending platform behind MTN and Airtel mobile money loans across multiple African countries. Winning JUMO potentially gives access to MNO lending products in SA, Zambia, Ghana, Uganda, Kenya, Tanzania, and Cameroon through one relationship.

## Competitive landscape

Nobody is doing the exact same thing. The gap is specifically: standalone, API-first, pre-collection scoring for African lending markets.

**Adjacent players (NOT direct competitors):**
- **RiskSeal, Credolab, TransUnion:** Pre-APPROVAL scoring (should we lend?). We do post-approval (will we collect?). Different problem, different buyer.
- **Credgenics:** Full end-to-end debt collection platform. Enterprise-heavy, India-focused. Overkill for a 20-person BNPL startup.
- **GiniMachine:** Generic ML debt scoring. Upload CSV, get scores. No real-time API, no African expertise.
- **LexisNexis RiskView:** US-only, requires deep credit bureau data that doesn't exist in Africa.

Our real competitor is "nothing" — spreadsheets, gut feel, or treating all collections equally.

## Why heuristics (not ML) for MVP

1. **No training data exists.** ML needs thousands of labelled examples (this collection failed / succeeded). Lenders don't have this structured data yet. Our heuristics generate it.
2. **Transparency sells.** Ops teams trust scores they can understand: "score is 72 because 40% failure rate + card expiring + end-of-month timing." Black-box ML gets ignored.
3. **Ships immediately.** No data collection period, no model training, no validation phase. Deploy and score on day one.
4. **Foundation for ML.** The 7-8 heuristic factors become the feature vector for the future ML model. Same inputs, same outputs, better accuracy.

The upgrade path: heuristics → collect outcomes for 3-6 months → train logistic regression / XGBoost → shadow mode alongside heuristics → swap when ML outperforms. The API contract never changes.

## Pricing model

Per-score pricing + dashboard subscription:
- **Pilot:** Free for 30 days (up to 1,000 scores). Prove ROI before paying.
- **Starter:** R5,000/month (10K scores, 2 dashboard users)
- **Growth:** R15,000/month (50K scores, 5 users, Slack, timing recs)
- **Scale:** R40,000+/month (unlimited, custom factors, SLA, ML training)

Zambia pricing ~40% lower to account for lower collection values.

Unit economics: A mid-size BNPL doing 50K collections/month at R1/score = R50K/month. If our scoring prevents even 2% more collection failures on their R50M annual book, that's R1M recovered/year against R600K product cost. Clear ROI.

## Regulatory context

- **SA:** BNPL currently in regulatory grey zone. FINASA is convening a working group on BNPL regulation in 2026. When regulation hits, lenders will need demonstrable risk management — our product provides that.
- **Zambia:** Lighter regulation. Bank of Zambia oversees mobile money. Data protection act applies.
- **Our compliance story:** We store no PII. Scores are fully explainable (every factor exposed). Immutable audit trail. This makes lenders' compliance conversations easier, not harder.

## Realistic timeline expectations

- **Months 1-3:** MVP built + deployed. 1 pilot running. 5+ prospects in conversation.
- **Months 4-6:** Pilot results in. 1-2 paying customers. Case study created. Zambia factor set ready.
- **Months 7-9:** 3-5 paying SA customers. First Zambia pilot. ML data collection underway.
- **Month 12:** 5-8 paying SA customers. 1-2 Zambia customers. R150-250K monthly revenue.

Sales cycles for B2B fintech in Africa: 3-6 months per customer. The first customer is hardest. The case study from the first customer sells the next 5.

## Key metrics to track

- **Prediction accuracy:** What % of HIGH-risk scores actually failed? What % of LOW-risk actually succeeded?
- **Collection rate lift:** Tenant's collection rate before vs after using PayPredict
- **Factor contribution:** Which factors are most predictive of actual failures?
- **Scoring latency:** p50 and p95 response times
- **Outcome reporting rate:** What % of scored collections have outcomes reported back? (Higher = better training data)
- **Customer retention:** Monthly churn rate of paying tenants