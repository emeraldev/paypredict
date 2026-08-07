from app.models.score_request import CollectionMethod
from app.scoring.factors.base import BaseFactor


# Segment risk scores. Government workers have the most predictable
# payslips (fixed pay date, employer doesn't disappear), miners are the
# most volatile (workers leave sites, industry cyclicality). Values are
# starting-point defaults — tenants can retune via factor-weight
# adjustments if their segment mix differs from the Lumo baseline.
DEFAULT_SEGMENT_SCORES: dict[str, float] = {
    "government": 0.2,
    "private_sector": 0.4,
    "contract": 0.5,
    "mining": 0.6,
    "informal": 0.7,
}


class BorrowerSegment(BaseFactor):
    """Risk from the borrower's employment segment.

    For Lumo Financial Services specifically: government workers vs
    miners. Government workers have stable, on-time salaries. Miners
    move between sites, get retrenched in commodity downturns, or
    simply disappear — "when they go, they go."

    Data (in customer_data):
      - borrower_segment: str — one of the keys in DEFAULT_SEGMENT_SCORES.
        Case-insensitive; unknown values fall through to a moderate default.
    """

    applicable_methods = [CollectionMethod.PAYROLL]

    def calculate(self, customer_data: dict, collection_data: dict) -> float:
        raw = customer_data.get("borrower_segment")
        if not raw:
            return 0.4  # Unknown segment — moderate default
        segment = str(raw).strip().lower()
        return DEFAULT_SEGMENT_SCORES.get(segment, 0.4)

    def explain(self, score: float) -> str:
        if score <= 0.25:
            return "Government/stable sector — lower risk segment"
        if score <= 0.45:
            return "Moderate risk segment"
        if score <= 0.65:
            return "Higher risk sector — more income volatility"
        return "High risk segment — least predictable income patterns"
