from app.scoring.factors.base import BaseFactor


class LoanCyclingBehaviour(BaseFactor):
    """Taking a new loan to repay an existing one. Classic default predictor."""

    def calculate(self, customer_data: dict, collection_data: dict) -> float:
        cycling = customer_data.get("new_loan_within_repayment_period")
        loans_90d = customer_data.get("loans_taken_last_90d", 0)

        if cycling:
            return 0.8

        if loans_90d >= 3:
            return 0.6
        if loans_90d >= 2:
            return 0.3
        return 0.1

    def explain(self, score: float) -> str:
        if score >= 0.8:
            return "New loan taken within repayment period — loan cycling detected"
        if score >= 0.6:
            return "Three or more loans in 90 days — high churn pattern"
        if score >= 0.3:
            return "Two loans in 90 days — moderate borrowing frequency"
        return "Normal borrowing pattern — low risk"
