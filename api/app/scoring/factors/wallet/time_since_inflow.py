from app.scoring.factors.base import BaseFactor


class TimeSinceLastInflow(BaseFactor):
    """How long since money last entered the wallet. Longer = riskier."""

    def calculate(self, customer_data: dict, collection_data: dict) -> float:
        hours = customer_data.get("hours_since_last_inflow")

        if hours is None:
            return 0.5

        if hours <= 6:
            return 0.1
        if hours <= 24:
            return 0.2
        if hours <= 48:
            return 0.4
        if hours <= 72:
            return 0.6
        return 0.8

    def explain(self, score: float) -> str:
        if score <= 0.1:
            return "Money received very recently — ideal collection window"
        if score <= 0.2:
            return "Recent inflow within 24 hours — good timing"
        if score <= 0.4:
            return "Last inflow 1-2 days ago — moderate timing"
        if score <= 0.6:
            return "No inflow for 2-3 days — elevated risk"
        if score >= 0.8:
            return "Prolonged period without inflow — high risk"
        return "No inflow data available — moderate default applied"
