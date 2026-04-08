from app.scoring.factors.base import BaseFactor

DAY_INDEX = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


class SalaryCycleAlignment(BaseFactor):
    """Is the collection scheduled in sync with the borrower's income pattern?"""

    def calculate(self, customer_data: dict, collection_data: dict) -> float:
        inflow_day = customer_data.get("regular_inflow_day")
        due_date = collection_data.get("collection_due_date")

        if inflow_day is None or due_date is None:
            return 0.4  # Moderate default

        inflow_idx = DAY_INDEX.get(inflow_day.lower())
        if inflow_idx is None:
            return 0.4

        collection_idx = due_date.weekday()  # 0=Monday
        days_after = (collection_idx - inflow_idx) % 7

        if days_after <= 1:
            return 0.1
        if days_after <= 3:
            return 0.25
        if days_after <= 5:
            return 0.5
        return 0.75

    def explain(self, score: float) -> str:
        if score <= 0.1:
            return "Collection perfectly aligned with inflow day — lowest risk"
        if score <= 0.25:
            return "Collection 2-3 days after inflow — good alignment"
        if score <= 0.5:
            return "Collection 4-5 days after inflow — moderate misalignment"
        return "Collection far from inflow day — poor alignment"
