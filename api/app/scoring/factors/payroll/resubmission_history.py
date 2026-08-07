from app.models.score_request import CollectionMethod
from app.scoring.factors.base import BaseFactor


class ResubmissionHistory(BaseFactor):
    """How often we've had to resubmit this borrower's deduction with a
    lower amount in the recent past.

    Resubmissions signal ongoing threshold pressure or income volatility —
    the payroll system rejected the original amount and the lender had to
    scale down to recover something. Repeat pattern = repeat problem.

    Data (in customer_data):
      - resubmission_count: int, resubmissions in the past 6 months
    """

    applicable_methods = [CollectionMethod.PAYROLL]

    def calculate(self, customer_data: dict, collection_data: dict) -> float:
        resubmissions = customer_data.get("resubmission_count")

        if resubmissions is None:
            return 0.3  # Unknown — assume mild risk

        if resubmissions == 0:
            return 0.0
        if resubmissions == 1:
            return 0.3
        if resubmissions == 2:
            return 0.6
        return 0.85  # 3+

    def explain(self, score: float) -> str:
        if score == 0.0:
            return "No previous resubmissions — clean deduction history"
        if score <= 0.3:
            return "One prior resubmission — possibly a one-off"
        if score <= 0.6:
            return "Multiple resubmissions — recurring threshold issues"
        return "Frequent resubmissions — persistent deduction problems"
