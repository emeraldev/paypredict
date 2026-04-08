from app.scoring.factors.base import BaseFactor


class InstalmentPosition(BaseFactor):
    """Later instalments carry more risk due to payment fatigue."""

    def calculate(self, customer_data: dict, collection_data: dict) -> float:
        instalment_number = customer_data.get("instalment_number")
        total_instalments = customer_data.get("total_instalments")

        if not total_instalments or total_instalments == 0:
            return 0.5  # Unknown position

        if instalment_number is None:
            return 0.5

        position_ratio = instalment_number / total_instalments
        return self.clamp(position_ratio * 0.8)

    def explain(self, score: float) -> str:
        if score >= 0.5:
            return "Late-stage instalment — payment fatigue risk is elevated"
        if score >= 0.3:
            return "Mid-stage instalment — moderate position risk"
        return "Early-stage instalment — low payment fatigue risk"
