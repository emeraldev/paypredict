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


# Specific real-world employer names routed to the bucket that best
# describes them. Kalene's pilot workflow uses these names directly in
# the `borrower_segment` field; without the alias layer every one of
# them would fall to the 0.4 "unknown" default, which is WORSE than the
# right-bucket score (ZESCO workers are government-adjacent and should
# score at 0.2, not 0.4 — the specific real-world information was
# lowering the signal). The aliases here express universal category
# claims about these employers (ZESCO is a state utility), not
# specific per-employer scores. Per-tenant overrides (if a lender
# disagrees with the alias target) are a planned follow-up PR; this
# dict is the global default.
#
# Keys are always lowercase to match the `strip().lower()` normalisation
# in `calculate`. Add to this table ONLY when:
#   (a) the employer is a real, identifiable entity (not a job title);
#   (b) the category assignment is defensible without lender-specific
#       context (a utility is government-adjacent everywhere; a
#       specific mine being "moderate" is NOT universal).
EMPLOYER_ALIASES: dict[str, str] = {
    # Zambian state / utility — government-adjacent payroll reliability.
    "zesco": "government",   # Zambia Electricity Supply Corporation
    "zsic": "government",    # Zambia State Insurance Corporation
    "zra": "government",     # Zambia Revenue Authority
    "grz": "government",     # Government of the Republic of Zambia
    # Zambian mining majors — industry cyclicality + site mobility.
    "kcm": "mining",         # Konkola Copper Mines
    "mopani": "mining",      # Mopani Copper Mines
    "fqm": "mining",         # First Quantum Minerals
}


class BorrowerSegment(BaseFactor):
    """Risk from the borrower's employment segment.

    Two levels of input are accepted:
      1. Canonical bucket strings (`government`, `private_sector`,
         `contract`, `mining`, `informal`) score directly from
         `DEFAULT_SEGMENT_SCORES`.
      2. Specific employer names (e.g. `ZESCO`, `KCM`, `Mopani`) are
         resolved through `EMPLOYER_ALIASES` to the right bucket, then
         score from the same table. Unknown employer names fall to a
         moderate 0.4 default.

    For Lumo Financial Services specifically: government workers vs
    miners. Government workers have stable, on-time salaries. Miners
    move between sites, get retrenched in commodity downturns, or
    simply disappear — "when they go, they go."

    Data (in customer_data):
      - borrower_segment: str — one of the keys in DEFAULT_SEGMENT_SCORES
        OR EMPLOYER_ALIASES. Case-insensitive; unknown values fall
        through to a moderate default.
    """

    applicable_methods = [CollectionMethod.PAYROLL]

    def calculate(self, customer_data: dict, collection_data: dict) -> float:
        raw = customer_data.get("borrower_segment")
        if not raw:
            return 0.4  # Unknown segment — moderate default
        segment = str(raw).strip().lower()
        # Alias layer: route specific employer names to the right bucket
        # before the score lookup. Falls through for canonical bucket
        # strings (government, mining, etc.) because they are not in
        # EMPLOYER_ALIASES.
        segment = EMPLOYER_ALIASES.get(segment, segment)
        return DEFAULT_SEGMENT_SCORES.get(segment, 0.4)

    def explain(self, score: float, trigger: str | None = None) -> str:
        if score <= 0.25:
            return "Government/stable sector — lower risk segment"
        if score <= 0.45:
            return "Moderate risk segment"
        if score <= 0.65:
            return "Higher risk sector — more income volatility"
        return "High risk segment — least predictable income patterns"
