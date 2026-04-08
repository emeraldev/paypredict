from app.scoring.factors.base import BaseFactor


class AirtimePurchasePattern(BaseFactor):
    """Regular airtime buyers who stop = proxy for income disruption."""

    def calculate(self, customer_data: dict, collection_data: dict) -> float:
        days_ago = customer_data.get("last_airtime_purchase_days_ago")

        if days_ago is None:
            return 0.3

        if days_ago <= 3:
            return 0.1
        if days_ago <= 7:
            return 0.2
        if days_ago <= 14:
            return 0.4
        if days_ago <= 30:
            return 0.6
        return 0.8

    def explain(self, score: float) -> str:
        if score <= 0.1:
            return "Recent airtime purchase — financially active"
        if score <= 0.2:
            return "Airtime purchased within the week — active"
        if score <= 0.4:
            return "Airtime purchase 1-2 weeks ago — moderate"
        if score <= 0.6:
            return "No airtime purchase in 2-4 weeks — declining activity"
        if score >= 0.8:
            return "No airtime purchase in over a month — potential income disruption"
        return "Airtime data unavailable — moderate default applied"
