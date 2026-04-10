from abc import ABC, abstractmethod
from typing import ClassVar

from app.models.score_request import CollectionMethod


class BaseFactor(ABC):
    """Base class for all scoring factors."""

    # Override in subclasses to restrict which collection methods this factor applies to.
    # None means the factor applies to all methods.
    applicable_methods: ClassVar[list[CollectionMethod] | None] = None

    def applies_to(self, method: CollectionMethod) -> bool:
        """Check if this factor applies to the given collection method."""
        if self.applicable_methods is None:
            return True
        return method in self.applicable_methods

    @abstractmethod
    def calculate(self, customer_data: dict, collection_data: dict) -> float:
        """Return a risk score between 0.0 (safe) and 1.0 (risky)."""

    @abstractmethod
    def explain(self, score: float) -> str:
        """Return a human-readable explanation of the score."""

    def clamp(self, value: float) -> float:
        """Clamp value to 0.0-1.0 range."""
        return max(0.0, min(1.0, value))
