from app.scoring.factors.base import BaseFactor


class ConcurrentLoanCount(BaseFactor):
    """Over-leveraged borrowers fail more often."""

    def calculate(self, customer_data: dict, collection_data: dict) -> float:
        loan_count = customer_data.get("active_loan_count")

        if loan_count is None:
            return 0.3  # Assume some risk

        if loan_count == 0:
            return 0.0
        if loan_count == 1:
            return 0.2
        if loan_count == 2:
            return 0.5
        return 0.8  # 3+

    def explain(self, score: float) -> str:
        if score == 0.0:
            return "No other active loans — single obligation"
        if score <= 0.2:
            return "One other active loan — manageable"
        if score <= 0.5:
            return "Two active loans — moderate leverage"
        if score >= 0.8:
            return "Three or more active loans — over-leveraged"
        return "Loan count unknown — moderate default applied"
