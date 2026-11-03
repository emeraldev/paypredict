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
    def explain(self, score: float, trigger: str | None = None) -> str:
        """Return a human-readable explanation of the score.

        `trigger` is the short code returned by `self.trigger(...)` when a
        specific policy rule inside the factor fired (not just a tight
        buffer). Factors that emit triggers should short-circuit here to
        return a message that names the rule by name, rather than the
        generic bucketed message. Factors that don't emit triggers can
        ignore the kwarg.
        """

    def trigger(
        self, customer_data: dict, collection_data: dict
    ) -> str | None:
        """Return a short code naming the specific policy rule that fired, or None.

        Default implementation returns None — the factor's score alone
        tells the story. Factors that gate on specific business rules
        (e.g. a regulatory cap breach vs a tight buffer) override this
        to tell the engine which rule fired, which the dashboard then
        surfaces as a precise reason rather than a bucketed tightness
        message.

        Called by the engine after `calculate`; the return is stored on
        `FactorBreakdown.trigger` and passed into `explain(score, trigger=...)`.
        """
        return None

    def clamp(self, value: float) -> float:
        """Clamp value to 0.0-1.0 range."""
        return max(0.0, min(1.0, value))
