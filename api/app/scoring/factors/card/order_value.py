from decimal import Decimal

from app.scoring.factors.base import BaseFactor


class OrderValueVsAverage(BaseFactor):
    """Collections above the customer's historical average are riskier."""

    def calculate(self, customer_data: dict, collection_data: dict) -> float:
        average = customer_data.get("average_collection_amount")
        amount = collection_data.get("collection_amount")

        if average is None or average == 0:
            return 0.3  # No history — moderate default

        if amount is None:
            return 0.3

        # Ensure we work with floats for comparison
        avg_f = float(average) if isinstance(average, Decimal) else average
        amt_f = float(amount) if isinstance(amount, Decimal) else amount

        ratio = amt_f / avg_f
        if ratio <= 1.2:
            return 0.1
        if ratio <= 2.0:
            return 0.4
        return 0.8

    def explain(self, score: float) -> str:
        if score <= 0.1:
            return "Collection amount is within normal range for this customer"
        if score <= 0.4:
            return "Collection amount is notably higher than customer's average"
        if score >= 0.8:
            return "Collection amount is more than double the customer's average"
        return "No average available — moderate default applied"
