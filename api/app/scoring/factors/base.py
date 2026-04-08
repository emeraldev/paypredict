from abc import ABC, abstractmethod


class BaseFactor(ABC):
    """Base class for all scoring factors."""

    @abstractmethod
    def calculate(self, customer_data: dict, collection_data: dict) -> float:
        """Return a risk score between 0.0 (safe) and 1.0 (risky)."""

    @abstractmethod
    def explain(self, score: float) -> str:
        """Return a human-readable explanation of the score."""

    def clamp(self, value: float) -> float:
        """Clamp value to 0.0-1.0 range."""
        return max(0.0, min(1.0, value))
