from app.scoring.factors.base import BaseFactor


class DebitOrderReturnHistory(BaseFactor):
    """SA-specific: EFT debit order return codes indicate failure types."""

    def calculate(self, customer_data: dict, collection_data: dict) -> float:
        returns = customer_data.get("debit_order_returns", [])

        if not returns:
            return 0.0

        # Check for fatal return types
        lower_returns = [r.lower() for r in returns]
        if "account_closed" in lower_returns:
            return 1.0

        # Score by count
        count = len(returns)
        if count == 1:
            base_score = 0.3
        elif count == 2:
            base_score = 0.6
        else:
            base_score = 0.9

        # Adjust for disputed returns
        if "disputed" in lower_returns:
            base_score += 0.2

        return self.clamp(base_score)

    def explain(self, score: float) -> str:
        if score >= 1.0:
            return "Account closed — debit order collection is impossible"
        if score >= 0.8:
            return "Multiple debit order returns — very high failure risk"
        if score >= 0.5:
            return "Recent debit order returns detected — elevated risk"
        if score >= 0.3:
            return "One recent debit order return — moderate concern"
        return "No debit order returns — clean history"
