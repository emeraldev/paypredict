# PayPredict — Factor Reference

## How factors work

Every factor is a Python class that inherits from `BaseFactor`. It receives customer and collection data, and returns a float between 0.0 (safe) and 1.0 (risky). It also provides a human-readable explanation of its score.

```python
from abc import ABC, abstractmethod

class BaseFactor(ABC):
    """Base class for all scoring factors."""

    @abstractmethod
    def calculate(self, customer_data: dict, collection_data: dict) -> float:
        """Return a risk score between 0.0 (safe) and 1.0 (risky)."""
        pass

    @abstractmethod
    def explain(self, score: float) -> str:
        """Return a human-readable explanation of the score."""
        pass

    def clamp(self, value: float) -> float:
        """Clamp value to 0.0-1.0 range."""
        return max(0.0, min(1.0, value))
```

The ScoringEngine orchestrator:
1. Looks up the tenant's market → loads the correct factor set from the registry
2. Loads the tenant's custom weights (or defaults if not customised)
3. Calls each factor's `calculate()` method
4. Multiplies raw scores by weights, sums them
5. Maps the total to a risk level (LOW/MEDIUM/HIGH)
6. Returns the full breakdown

---

## Card/Debit Factor Set (CARD_DEBIT)

For card-on-file charges and debit order collections. Not country-specific — usable in any market where card or debit order payments are collected.

### 1. HistoricalFailureRate
**Default weight: 0.25** | **Applicable methods: all** (shared factor)

Past behaviour is the strongest predictor of future behaviour.

```
Input:   customer_data.total_payments, customer_data.successful_payments
Logic:   failure_rate = 1 - (successful / total)
         If total == 0: return 0.5 (unknown = moderate default)
Score:   failure_rate directly (0% failures = 0.0, 100% failures = 1.0)
Example: 8 total, 5 successful → failure_rate = 0.375 → score = 0.375
```

### 2. DayOfMonthVsPayday
**Default weight: 0.20** | **Applicable methods: CARD, DEBIT_ORDER**

SA-specific: most salaried workers are paid on the 25th or 1st. Collecting pre-payday is riskier.

```
Input:   collection_data.collection_due_date, customer_data.known_salary_day (optional)
Logic:   If salary_day is known, calculate days between due_date and salary_day
         If not known, use SA defaults:
           Day 1-5:   0.1 (just after common payday — safest)
           Day 6-15:  0.3 (mid-month — moderate)
           Day 16-24: 0.5 (late month — elevated)
           Day 25-31: 0.8 (end of month, pre-payday — riskiest)
         If salary_day IS known:
           Collection 0-3 days after salary: 0.1
           Collection 4-10 days after: 0.3
           Collection 11-20 days after: 0.5
           Collection 21+ days after (or just before salary): 0.8
Example: Due date is 28th, no known salary day → score = 0.8
```

### 3. DaysSinceLastPayment
**Default weight: 0.15** | **Applicable methods: CARD, DEBIT_ORDER**

Recency of last successful payment. Longer gaps indicate higher risk.

```
Input:   customer_data.last_successful_payment_date
Logic:   days = (today - last_successful_payment_date).days
         If no successful payment ever: return 1.0
         score = clamp(days / 90)  # 90 days = max risk
Example: Last success 15 days ago → 15/90 = 0.167
         Last success 120 days ago → clamped to 1.0
         No history → 1.0
```

### 4. InstalmentPosition
**Default weight: 0.10** | **Applicable methods: all** (shared factor)

Later instalments carry more risk due to payment fatigue and budget strain.

```
Input:   customer_data.instalment_number, customer_data.total_instalments
Logic:   If total_instalments == 0: return 0.5
         position_ratio = instalment_number / total_instalments
         score = clamp(position_ratio * 0.8)  # Cap at 0.8 — position alone isn't max risk
Example: Instalment 5 of 6 → 5/6 * 0.8 = 0.667
         Instalment 1 of 6 → 1/6 * 0.8 = 0.133
```

### 5. OrderValueVsAverage
**Default weight: 0.10** | **Applicable methods: CARD, DEBIT_ORDER**

Collections significantly above the customer's historical average are riskier.

```
Input:   collection_data.collection_amount, customer_data.average_collection_amount
Logic:   If average == 0: return 0.3 (no history — moderate default)
         ratio = collection_amount / average
         If ratio <= 1.2: return 0.1  (within 20% of normal)
         If ratio <= 2.0: return 0.4  (up to double)
         Else: return 0.8             (more than double)
Example: Collection R1,500, average R750 → ratio 2.0 → score = 0.4
```

### 6. CardHealth
**Default weight: 0.10** | **Applicable methods: CARD only**

Card expiry proximity and decline history.

```
Input:   customer_data.card_expiry_date, customer_data.last_decline_code
Logic:   months_to_expiry = (card_expiry_date - today).days / 30
         base_score:
           If expired (<=0 months): 1.0
           If <=2 months: 0.7
           If <=6 months: 0.3
           Else: 0.1
         Adjust for last decline:
           If last_decline_code in hard_declines (card_cancelled, card_lost, stolen): add 0.3
           If last_decline_code in soft_declines (insufficient_funds, do_not_honour): add 0.1
           Clamp final to 1.0
Example: Expires in 1 month, last decline "insufficient_funds" → 0.7 + 0.1 = 0.8
```

Hard decline codes: `card_cancelled`, `card_lost`, `stolen`, `account_closed`, `invalid_card`
Soft decline codes: `insufficient_funds`, `do_not_honour`, `exceeded_limit`, `general_decline`

### 7. CardType
**Default weight: 0.05** | **Applicable methods: CARD only**

Debit cards are more prone to insufficient funds than credit cards.

```
Input:   customer_data.card_type
Logic:   "credit" → 0.2  (credit limit provides buffer)
         "debit"  → 0.5  (directly tied to account balance)
         unknown  → 0.4
```

### 8. DebitOrderReturnHistory
**Default weight: 0.05** | **Applicable methods: DEBIT_ORDER only**

SA-specific: EFT debit order return codes indicate specific failure types.

```
Input:   customer_data.debit_order_returns (array of recent return codes)
Logic:   If no returns: 0.0
         Count returns in last 90 days:
           0 returns: 0.0
           1 return:  0.3
           2 returns: 0.6
           3+ returns: 0.9
         Adjust for return types:
           "account_closed" in returns → set to 1.0 (fatal)
           "disputed" in returns → add 0.2 (customer actively rejecting)
Example: 2 returns in 90 days, none fatal → 0.6
```

---

## Mobile Wallet Factor Set (MOBILE_WALLET)

For mobile money wallet auto-deductions (MTN MoMo, Airtel Money, Zamtel Kwacha, etc.). Not country-specific — usable in any market where mobile money collections are used.

### 1. WalletBalanceTrend
**Default weight: 0.25** | **Applicable methods: MOBILE_MONEY**

Most important mobile money factor. Declining wallet balance = collection will fail.

```
Input:   customer_data.wallet_balance_7d_avg, customer_data.wallet_balance_current,
         collection_data.collection_amount
Logic:   If no balance data: return 0.5 (unknown)
         trend = wallet_balance_current / wallet_balance_7d_avg
           If trend < 0.3: 0.9   (balance crashed — very high risk)
           If trend < 0.6: 0.6   (declining significantly)
           If trend < 0.9: 0.3   (slight decline)
           Else: 0.1             (stable or growing)
         Adjust: if wallet_balance_current < collection_amount: add 0.3 (can't even cover it)
         Clamp to 1.0
Example: 7d avg ZMW 180, current ZMW 95, collection ZMW 250
         trend = 95/180 = 0.53 → 0.6, current < amount → +0.3 = 0.9
```

### 2. HistoricalFailureRate
**Default weight: 0.20** | **Applicable methods: all** (shared factor)

Same concept as SA. Past success/failure ratio.

```
(Same logic as SA HistoricalFailureRate — shared base implementation)
```

### 3. TimeSinceLastInflow
**Default weight: 0.15** | **Applicable methods: MOBILE_MONEY**

How long since money last entered the wallet. Longer = riskier.

```
Input:   customer_data.hours_since_last_inflow
Logic:   If no data: return 0.5
         If hours <= 6:   0.1  (just received money — ideal collection window)
         If hours <= 24:  0.2  (recent)
         If hours <= 48:  0.4  (getting stale)
         If hours <= 72:  0.6  (3 days without inflow)
         Else:            0.8  (prolonged dry period)
Example: Last inflow 48 hours ago → score = 0.4
```

### 4. SalaryCycleAlignment
**Default weight: 0.15** | **Applicable methods: MOBILE_MONEY**

Is the collection scheduled in sync with the borrower's income pattern?

```
Input:   collection_data.collection_due_date, customer_data.regular_inflow_day
Logic:   If regular_inflow_day unknown: return 0.4 (moderate default)
         Determine day-of-week alignment:
           Collection on inflow day or day after: 0.1 (perfectly aligned)
           Collection 2-3 days after inflow: 0.25
           Collection 4-5 days after: 0.5
           Collection 6+ days after (just before next inflow): 0.75
Example: Inflow usually Friday, collection on Monday → 3 days after → 0.25
         Inflow usually Friday, collection on Thursday → 6 days after → 0.75
```

### 5. ConcurrentLoanCount
**Default weight: 0.10** | **Applicable methods: all** (shared factor)

Over-leveraged borrowers fail more often.

```
Input:   customer_data.active_loan_count
Logic:   If no data: return 0.3 (assume some risk)
         0 other loans: 0.0
         1 other loan:  0.2
         2 other loans: 0.5
         3+ loans:      0.8
Example: 2 active loans → score = 0.5
```

### 6. TransactionVelocity
**Default weight: 0.05** | **Applicable methods: MOBILE_MONEY**

Sudden drop in transaction activity signals financial stress.

```
Input:   customer_data.transactions_last_7d, customer_data.transactions_avg_7d
Logic:   If no data: return 0.3
         ratio = transactions_last_7d / transactions_avg_7d
         If ratio >= 0.8:  0.1 (normal activity)
         If ratio >= 0.5:  0.4 (noticeable slowdown)
         If ratio >= 0.2:  0.7 (significant drop)
         Else:             0.9 (near-inactive — serious concern)
Example: Usually 15 transactions/week, this week only 5 → 5/15 = 0.33 → 0.7
```

### 7. AirtimePurchasePattern
**Default weight: 0.05** | **Applicable methods: MOBILE_MONEY**

Regular airtime buyers who suddenly stop = proxy for income disruption.

```
Input:   customer_data.last_airtime_purchase_days_ago
Logic:   If no data: return 0.3
         If days <= 3:  0.1  (recently bought — financially active)
         If days <= 7:  0.2
         If days <= 14: 0.4
         If days <= 30: 0.6
         Else:          0.8  (hasn't bought airtime in a month — concern)
Example: Last airtime purchase 1 day ago → score = 0.1
```

### 8. LoanCyclingBehaviour
**Default weight: 0.05** | **Applicable methods: all** (shared factor)

Taking a new loan to repay an existing one. Classic default predictor.

```
Input:   customer_data.new_loan_within_repayment_period (boolean),
         customer_data.loans_taken_last_90d
Logic:   If new_loan_within_repayment_period: 0.8
         Elif loans_taken_last_90d >= 3: 0.6
         Elif loans_taken_last_90d >= 2: 0.3
         Else: 0.1
Example: Took a new loan 2 days before repayment was due → score = 0.8
```

---

## Payroll Deduction Factor Set (PAYROLL)

For salary-advance lenders whose collections go through payroll systems (Zambia
and similar jurisdictions with regulatory deduction ceilings). Initial customer:
Lumo Financial Services (Zambia), who service ~1,000 government workers and
~100 miners with 1–3 month salary advances.

The dominant failure mechanism is regulatory: **Zambia caps total payroll
deductions from all creditors at 40% of gross salary.** If the borrower's other
creditors have already consumed that headroom, the lender's deduction is
rejected — even if the borrower has money. Threshold headroom is the single
biggest predictor.

### 1. ThresholdHeadroom
**Default weight: 0.25** | **Applicable methods: PAYROLL**

Gap between current total deductions and the regulatory ceiling. THE key factor
for payroll — a full ceiling means the deduction will be rejected regardless of
the borrower's willingness or ability.

```
Input:   customer_data.gross_salary, customer_data.current_total_deductions,
         customer_data.deduction_threshold_pct (defaults to 0.40),
         collection_data.collection_amount
Logic:   If gross_salary unknown: return 0.5
         cap = gross_salary × threshold_pct
         If current_deductions provided:
           headroom = cap - current_deductions
           If headroom <= 0:          1.0  (already at/over cap)
           If amount > headroom:      0.9  (our deduction exceeds available room)
           buffer = (headroom - amount) / cap
             If buffer < 5%:          0.8
             If buffer < 15%:         0.5
             If buffer < 30%:         0.3
             Else:                    0.1
         Else (only gross known):
           ratio = amount / cap
             If ratio > 0.8:          0.8
             ... (same tiering, single-deduction proxy)
Example: gross ZMW 10000, existing deductions 3600, our deduction 500
         cap = 4000, headroom = 400 < 500 → 0.9
```

### 2. HistoricalFailureRate
**Default weight: 0.20** | **Applicable methods: all** (shared factor)

Same logic as the shared factor used by CARD_DEBIT and MOBILE_WALLET. Past
deduction success/failure ratio.

### 3. DeductionToIncomeRatio
**Default weight: 0.15** | **Applicable methods: PAYROLL**

Deduction amount as a share of the borrower's income. A large ratio is riskier
even when the threshold factor is comfortable, because take-home pay pressure
increases the chance of the borrower disputing or reversing the deduction.

```
Input:   customer_data.net_pay (or gross_salary as fallback),
         collection_data.collection_amount
Logic:   If no income: return 0.5
         ratio = amount / income
           If ratio > 0.50: 0.9
           If ratio > 0.35: 0.7
           If ratio > 0.20: 0.4
           If ratio > 0.10: 0.2
           Else:            0.1
Example: net_pay ZMW 5100, deduction ZMW 2600 → ratio 0.51 → 0.9
```

### 4. ConcurrentLoanCount
**Default weight: 0.15** | **Applicable methods: all** (shared factor)

Number of active loans from other creditors. Directly maps to the threshold-
consumption story — every other creditor deducting from the same payroll
consumes headroom.

### 5. ResubmissionHistory
**Default weight: 0.10** | **Applicable methods: PAYROLL**

How often we've had to resubmit this borrower's deduction with a lower amount
in the recent past. Resubmissions signal ongoing threshold pressure or income
volatility.

```
Input:   customer_data.resubmission_count (past 6 months)
Logic:   If no data: 0.3 (unknown, mild default)
         0 resubmissions:  0.0 (clean history)
         1 resubmission:   0.3 (possibly one-off)
         2 resubmissions:  0.6 (pattern forming)
         3+ resubmissions: 0.85
Example: 3 resubmissions in the past 6 months → 0.85
```

### 6. BorrowerSegment
**Default weight: 0.05** | **Applicable methods: PAYROLL**

Employment sector as a coarse risk prior. For Lumo specifically: government
workers have stable, on-time salaries; miners move between sites, get
retrenched in commodity downturns, or disappear entirely.

```
Input:   customer_data.borrower_segment (case-insensitive)
Logic:   Segment → base score:
           government:      0.2
           private_sector:  0.4
           contract:        0.5
           mining:          0.6
           informal:        0.7
         Unknown / missing: 0.4 (moderate default)
Example: borrower_segment "government" → 0.2
```

### 7. LoanCyclingBehaviour
**Default weight: 0.05** | **Applicable methods: all** (shared factor)

Borrowers who take new loans while still repaying — same logic as the shared
factor used by MOBILE_WALLET.

### 8. InstalmentPosition
**Default weight: 0.05** | **Applicable methods: all** (shared factor)

Which month of the (usually 1–3 month) advance we're on. Same shared factor.

---

## Adding a new factor

1. Create a new file in `api/app/scoring/factors/card/`, `wallet/`, or `shared/`
2. Inherit from `BaseFactor`, implement `calculate()` and `explain()`
3. Register the factor in the appropriate factor set in `registry.py`
4. Add a default weight for the factor in the tenant seeding logic
5. Write unit tests covering normal cases, edge cases (missing data, zeros), and boundary values
6. Update this documentation

## Adding a new collection method

1. Create a new folder `api/app/scoring/factors/{method_name}/`
2. Implement factor classes specific to that collection method (reuse shared factors where applicable)
3. Add a new enum value to the `FactorSet` enum
4. Register the factor set in `registry.py`
5. Add default weights to tenant seeding logic
6. Update CLAUDE.md and this documentation

Note: Adding a new **market** (country) does not require new factors — just a new `Market` enum value. Markets affect currency, payday defaults, and regulation, but factor sets are determined by collection method.