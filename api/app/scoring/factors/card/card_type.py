from app.scoring.factors.base import BaseFactor


class CardType(BaseFactor):
    """Debit cards are more prone to insufficient funds than credit cards."""

    def calculate(self, customer_data: dict, collection_data: dict) -> float:
        card_type = customer_data.get("card_type")

        if card_type is None:
            return 0.4  # Unknown

        card_type = card_type.lower()
        if card_type == "credit":
            return 0.2
        if card_type == "debit":
            return 0.5
        return 0.4  # Unknown type

    def explain(self, score: float) -> str:
        if score <= 0.2:
            return "Credit card — credit limit provides buffer against insufficient funds"
        if score >= 0.5:
            return "Debit card — directly tied to account balance, higher failure risk"
        return "Card type unknown — moderate default applied"
