from app.scoring.factors.base import BaseFactor


class DayOfMonthVsPayday(BaseFactor):
    """SA-specific: collection timing relative to payday (25th or 1st)."""

    def calculate(self, customer_data: dict, collection_data: dict) -> float:
        due_date = collection_data.get("collection_due_date")
        if due_date is None:
            return 0.4

        salary_day = customer_data.get("known_salary_day")
        day = due_date.day

        if salary_day is not None:
            # Calculate days after salary (circular, within a month)
            days_after = (day - salary_day) % 31
            if days_after <= 3:
                return 0.1
            if days_after <= 10:
                return 0.3
            if days_after <= 20:
                return 0.5
            return 0.8

        # No known salary day — use SA defaults
        if day <= 5:
            return 0.1
        if day <= 15:
            return 0.3
        if day <= 24:
            return 0.5
        return 0.8

    def explain(self, score: float) -> str:
        if score <= 0.1:
            return "Collection scheduled just after payday — lowest risk window"
        if score <= 0.3:
            return "Collection in early-to-mid period after payday — moderate timing"
        if score <= 0.5:
            return "Collection in mid-to-late period — elevated timing risk"
        return "Collection near end of month or pre-payday — highest timing risk"
