from datetime import date

from app.models.score_request import CollectionMethod
from app.scoring.factors.base import BaseFactor

HARD_DECLINES = {"card_cancelled", "card_lost", "stolen", "account_closed", "invalid_card"}
SOFT_DECLINES = {"insufficient_funds", "do_not_honour", "exceeded_limit", "general_decline"}


class CardHealth(BaseFactor):
    """Card expiry proximity and decline history."""

    applicable_methods = [CollectionMethod.CARD]

    def calculate(self, customer_data: dict, collection_data: dict) -> float:
        expiry = customer_data.get("card_expiry_date")
        decline_code = customer_data.get("last_decline_code")

        # Base score from expiry
        if expiry is None:
            base_score = 0.3  # Unknown card status
        else:
            if isinstance(expiry, str):
                expiry = date.fromisoformat(expiry)
            months_to_expiry = (expiry - date.today()).days / 30
            if months_to_expiry <= 0:
                base_score = 1.0
            elif months_to_expiry <= 2:
                base_score = 0.7
            elif months_to_expiry <= 6:
                base_score = 0.3
            else:
                base_score = 0.1

        # Adjust for decline code
        if decline_code:
            code = decline_code.lower()
            if code in HARD_DECLINES:
                base_score += 0.3
            elif code in SOFT_DECLINES:
                base_score += 0.1

        return self.clamp(base_score)

    def explain(self, score: float) -> str:
        if score >= 0.9:
            return "Card is expired or has hard decline — very high risk"
        if score >= 0.7:
            return "Card expiring soon or recent decline — elevated risk"
        if score >= 0.3:
            return "Card health is moderate — some concerns"
        return "Card is healthy with no recent issues"
