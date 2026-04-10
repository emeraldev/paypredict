from decimal import Decimal

from app.models.score_request import CollectionMethod
from app.scoring.factors.base import BaseFactor


class WalletBalanceTrend(BaseFactor):
    applicable_methods = [CollectionMethod.MOBILE_MONEY]

    """Most important mobile money factor. Declining balance = collection will fail."""

    def calculate(self, customer_data: dict, collection_data: dict) -> float:
        avg_balance = customer_data.get("wallet_balance_7d_avg")
        current_balance = customer_data.get("wallet_balance_current")
        collection_amount = collection_data.get("collection_amount")

        if avg_balance is None or current_balance is None:
            return 0.5  # Unknown

        avg_f = float(avg_balance) if isinstance(avg_balance, Decimal) else float(avg_balance)
        cur_f = (
            float(current_balance)
            if isinstance(current_balance, Decimal)
            else float(current_balance)
        )

        if avg_f == 0:
            return 0.5

        trend = cur_f / avg_f

        if trend < 0.3:
            score = 0.9
        elif trend < 0.6:
            score = 0.6
        elif trend < 0.9:
            score = 0.3
        else:
            score = 0.1

        # Adjust if current balance can't cover collection
        if collection_amount is not None:
            amt_f = (
                float(collection_amount)
                if isinstance(collection_amount, Decimal)
                else float(collection_amount)
            )
            if cur_f < amt_f:
                score += 0.3

        return self.clamp(score)

    def explain(self, score: float) -> str:
        if score >= 0.8:
            return "Wallet balance has crashed or cannot cover collection — very high risk"
        if score >= 0.5:
            return "Wallet balance declining significantly — elevated risk"
        if score >= 0.3:
            return "Wallet balance slightly declining — moderate risk"
        return "Wallet balance is stable or growing — low risk"
