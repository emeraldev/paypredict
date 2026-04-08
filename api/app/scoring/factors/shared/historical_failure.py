from app.scoring.factors.base import BaseFactor


class HistoricalFailureRate(BaseFactor):
    """Past payment success/failure ratio. Strongest predictor of future behaviour."""

    def calculate(self, customer_data: dict, collection_data: dict) -> float:
        total = customer_data.get("total_payments", 0)
        successful = customer_data.get("successful_payments", 0)

        if total == 0:
            return 0.5  # Unknown = moderate default

        failure_rate = 1 - (successful / total)
        return self.clamp(failure_rate)

    def explain(self, score: float) -> str:
        pct = round(score * 100, 1)
        if score == 0.5:
            return "No payment history available — moderate default applied"
        if score <= 0.1:
            return f"{pct}% of past collections have failed — excellent track record"
        if score <= 0.3:
            return f"{pct}% of past collections have failed — good history"
        if score <= 0.6:
            return f"{pct}% of past collections have failed — elevated failure rate"
        return f"{pct}% of past collections have failed — high failure rate"
