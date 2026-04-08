from datetime import date

from app.scoring.factors.base import BaseFactor


class DaysSinceLastPayment(BaseFactor):
    """Recency of last successful payment. Longer gaps = higher risk."""

    def calculate(self, customer_data: dict, collection_data: dict) -> float:
        last_payment = customer_data.get("last_successful_payment_date")

        if last_payment is None:
            return 1.0  # No history = max risk

        if isinstance(last_payment, str):
            last_payment = date.fromisoformat(last_payment)

        days = (date.today() - last_payment).days
        return self.clamp(days / 90)

    def explain(self, score: float) -> str:
        if score >= 1.0:
            return "No successful payment on record — maximum recency risk"
        days = round(score * 90)
        if days <= 7:
            return f"Last successful payment {days} days ago — very recent"
        if days <= 30:
            return f"Last successful payment {days} days ago — recent"
        if days <= 60:
            return f"Last successful payment {days} days ago — getting stale"
        return f"Last successful payment {days}+ days ago — significant gap"
