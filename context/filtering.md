# Add collection method filtering to factors

## Problem

In the CARD_DEBIT factor set, some factors only apply to card collections (CardHealth, CardType) and some only apply to debit order collections (DebitOrderReturnHistory). Currently the engine runs all factors regardless of the collection_method, which means card-specific factors run on debit order collections with missing data and return noisy moderate defaults.

## Solution

Add an `applicable_methods` property to BaseFactor. The ScoringEngine checks this before running each factor and skips factors that don't apply to the current collection method. Skipped factors are excluded from the score calculation AND the weight redistribution — remaining weights are re-normalised to sum to 1.0.

### 1. Update BaseFactor

```python
from enum import Enum
from typing import ClassVar

class CollectionMethod(str, Enum):
    CARD = "CARD"
    DEBIT_ORDER = "DEBIT_ORDER"
    MOBILE_MONEY = "MOBILE_MONEY"

class BaseFactor(ABC):
    # Default: applies to all methods. Override in subclasses to restrict.
    applicable_methods: ClassVar[list[CollectionMethod] | None] = None  # None = all methods

    def applies_to(self, method: CollectionMethod) -> bool:
        if self.applicable_methods is None:
            return True
        return method in self.applicable_methods

    @abstractmethod
    def calculate(self, customer_data: dict, collection_data: dict) -> float:
        pass

    @abstractmethod
    def explain(self, score: float) -> str:
        pass

    def clamp(self, value: float) -> float:
        return max(0.0, min(1.0, value))
```

### 2. Set applicable_methods on factors that are method-specific

**Card-only factors (in factors/card/):**

```python
class CardHealth(BaseFactor):
    applicable_methods = [CollectionMethod.CARD]
    # ... rest unchanged

class CardType(BaseFactor):
    applicable_methods = [CollectionMethod.CARD]
    # ... rest unchanged
```

**Debit-order-only factors (in factors/card/):**

```python
class DebitOrderReturnHistory(BaseFactor):
    applicable_methods = [CollectionMethod.DEBIT_ORDER]
    # ... rest unchanged
```

**All other card/ factors:** Leave applicable_methods as None (applies to both CARD and DEBIT_ORDER).

**All wallet/ factors:** Set applicable_methods to [CollectionMethod.MOBILE_MONEY]. Although they're already in a separate factor set, this makes it explicit and safe.

**All shared/ factors:** Leave applicable_methods as None (applies to everything).

### 3. Update ScoringEngine

In the scoring engine, when iterating over factors:

```python
def score(self, collection_method: CollectionMethod, customer_data: dict, collection_data: dict) -> dict:
    factor_set = self.registry.get_factors(self.tenant.factor_set)
    weights = self.get_tenant_weights()

    # Filter to applicable factors only
    applicable = [(f, w) for f, w in zip(factor_set, ...) if f.applies_to(collection_method)]

    # Re-normalise weights so they sum to 1.0
    total_weight = sum(w for _, w in applicable)
    if total_weight == 0:
        total_weight = 1.0  # safety

    results = []
    final_score = 0.0

    for factor, raw_weight in applicable:
        normalised_weight = raw_weight / total_weight
        raw_score = factor.calculate(customer_data, collection_data)
        weighted = raw_score * normalised_weight
        final_score += weighted

        results.append({
            "factor": factor.__class__.__name__,
            "raw_score": round(raw_score, 3),
            "weight": round(normalised_weight, 3),
            "weighted_score": round(weighted, 3),
            "explanation": factor.explain(raw_score),
        })

    # ... map to risk level, return results
```

The key is **weight re-normalisation**. If a CARD collection skips DebitOrderReturnHistory (weight 5%), the remaining 95% of weights get scaled up proportionally so the final score still uses the full 0-1 range. Without this, card scores would max out at 0.95 and debit order scores at 0.90.

### 4. Update response to show which factors were skipped

In the API response, optionally include a `skipped_factors` field:

```json
{
  "score": 0.68,
  "risk_level": "HIGH",
  "factors": [ ... ],
  "skipped_factors": ["debit_order_return_history"],
  "skipped_reason": "Not applicable for CARD collection method"
}
```

This is useful for debugging and transparency but can be omitted from the response if it adds clutter — keep it in the internal ScoreResult.factors JSONB for audit purposes.

### 5. Update tests

- Add tests for CardHealth: verify `applies_to(CARD)` returns True, `applies_to(DEBIT_ORDER)` returns False
- Add tests for DebitOrderReturnHistory: verify `applies_to(DEBIT_ORDER)` returns True, `applies_to(CARD)` returns False
- Add engine integration test: score a CARD collection and verify CardHealth IS in factors and DebitOrderReturnHistory is NOT
- Add engine integration test: score a DEBIT_ORDER collection and verify the reverse
- Add weight normalisation test: verify weights sum to 1.0 after skipping inapplicable factors
- Add test: verify a CARD score and DEBIT_ORDER score for the same customer can produce different results because different factors run

### 6. Update seed data

Make sure the demo SA tenant has sample collections with both CARD and DEBIT_ORDER methods so the dashboard shows both types with their correct factor breakdowns.

### 7. Update docs

In docs/factors.md, add an "Applicable methods" line to each factor's documentation:
```
### CardHealth
**Default weight: 0.10**
**Applicable methods: CARD only**
```

In CLAUDE.md, add a note about method filtering in the architecture decisions section.