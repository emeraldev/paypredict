from app.models.score_request import CollectionMethod
from app.scoring.factors.base import BaseFactor


class DeductionToIncomeRatio(BaseFactor):
    """The deduction amount as a share of the borrower's income.

    A ZMW 2,600 deduction on a ZMW 5,100 net pay (51%) is riskier than a
    ZMW 1,000 deduction on the same salary (20%) — even if the threshold
    factor is comfortable.

    Prefers `net_pay` (what the borrower actually receives). Falls back to
    `gross_salary` if net isn't available. Returns 0.5 when neither is
    known.
    """

    applicable_methods = [CollectionMethod.PAYROLL]

    def calculate(self, customer_data: dict, collection_data: dict) -> float:
        income = customer_data.get("net_pay") or customer_data.get("gross_salary")
        collection_amount = collection_data.get("collection_amount", 0)

        if income is None or float(income) <= 0:
            return 0.5

        ratio = float(collection_amount) / float(income)

        if ratio > 0.50:
            return 0.9
        if ratio > 0.35:
            return 0.7
        if ratio > 0.20:
            return 0.4
        if ratio > 0.10:
            return 0.2
        return 0.1

    def explain(self, score: float) -> str:
        if score >= 0.8:
            return "Deduction is a very large portion of borrower's income"
        if score >= 0.6:
            return "Deduction is a significant portion of income"
        if score >= 0.3:
            return "Deduction is moderate relative to income"
        return "Deduction is small relative to income"
