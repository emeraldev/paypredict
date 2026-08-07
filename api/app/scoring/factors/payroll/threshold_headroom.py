from app.models.score_request import CollectionMethod
from app.scoring.factors.base import BaseFactor


class ThresholdHeadroom(BaseFactor):
    """The dominant payroll factor.

    Zambia (and similar jurisdictions) cap total payroll deductions at a
    fixed percentage of gross salary — 40% is the common threshold. If the
    borrower's existing deductions from other creditors already push them
    near that ceiling, the lender's deduction gets rejected regardless of
    whether the borrower has money.

    Data (all optional, all in `customer_data`):
      - gross_salary: Decimal
      - current_total_deductions: Decimal — everyone else's deductions
      - deduction_threshold_pct: float, defaults to 0.40

    Compared against `collection_data.collection_amount`.
    """

    applicable_methods = [CollectionMethod.PAYROLL]

    def calculate(self, customer_data: dict, collection_data: dict) -> float:
        gross_salary = customer_data.get("gross_salary")
        current_deductions = customer_data.get("current_total_deductions")
        # Pydantic serialises optional fields as explicit None when omitted,
        # so .get(key, default) doesn't shield us — handle None first, same
        # trap as LoanCyclingBehaviour hit.
        threshold_pct = customer_data.get("deduction_threshold_pct")
        if threshold_pct is None:
            threshold_pct = 0.40  # Zambia default
        collection_amount = collection_data.get("collection_amount", 0)

        if not gross_salary:
            return 0.5  # No salary data — insufficient info to judge

        max_deductions = float(gross_salary) * float(threshold_pct)
        amount = float(collection_amount)

        if current_deductions is not None:
            headroom = max_deductions - float(current_deductions)
            if headroom <= 0:
                return 1.0  # Already at/over the ceiling — deduction will fail
            if amount > headroom:
                return 0.9  # Our deduction alone exceeds available headroom

            # Tightness of the buffer after our deduction lands
            buffer_ratio = (headroom - amount) / max_deductions
            if buffer_ratio < 0.05:
                return 0.8
            if buffer_ratio < 0.15:
                return 0.5
            if buffer_ratio < 0.30:
                return 0.3
            return 0.1

        # Only gross_salary known — score by how much of the ceiling this
        # single deduction alone would consume.
        if max_deductions <= 0:
            return 0.5
        ratio = amount / max_deductions
        if ratio > 0.8:
            return 0.8
        if ratio > 0.5:
            return 0.5
        if ratio > 0.3:
            return 0.3
        return 0.1

    def explain(self, score: float) -> str:
        if score >= 0.95:
            return "Borrower already at or over the deduction ceiling — deduction will be rejected"
        if score >= 0.85:
            return "Deduction alone exceeds available salary threshold headroom"
        if score >= 0.7:
            return "Very tight salary threshold headroom — high rejection risk"
        if score >= 0.4:
            return "Moderate salary threshold headroom"
        if score > 0.15:
            return "Comfortable salary threshold headroom"
        return "Plenty of threshold headroom — low rejection risk"
