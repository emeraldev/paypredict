from app.scoring.factors.base import BaseFactor


class TransactionVelocity(BaseFactor):
    """Sudden drop in transaction activity signals financial stress."""

    def calculate(self, customer_data: dict, collection_data: dict) -> float:
        recent = customer_data.get("transactions_last_7d")
        avg = customer_data.get("transactions_avg_7d")

        if recent is None or avg is None:
            return 0.3

        if avg == 0:
            return 0.3

        ratio = recent / avg
        if ratio >= 0.8:
            return 0.1
        if ratio >= 0.5:
            return 0.4
        if ratio >= 0.2:
            return 0.7
        return 0.9

    def explain(self, score: float) -> str:
        if score <= 0.1:
            return "Transaction activity is normal — no concern"
        if score <= 0.4:
            return "Noticeable slowdown in transactions — moderate concern"
        if score <= 0.7:
            return "Significant drop in transaction activity — financial stress signal"
        if score >= 0.9:
            return "Near-inactive account — serious concern"
        return "Transaction data unavailable — moderate default applied"
