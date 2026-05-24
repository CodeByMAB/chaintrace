"""Base CoT extractor interface."""

from abc import ABC, abstractmethod

from chaintrace.types.trace import ReasoningStep


class BaseExtractor(ABC):
    """Extract reasoning steps from raw text content.

    Extractors operate on the text of a response and return structured
    ReasoningStep objects.  Multiple extractors can be tried in order;
    the first that returns results wins.
    """

    name: str

    @abstractmethod
    def extract(self, text: str) -> list[ReasoningStep]:
        """Extract reasoning steps from text.

        Returns an empty list if this extractor cannot handle the input.
        """

    def can_handle(self, text: str) -> bool:
        """Quick check before running extract(); override for efficiency."""
        return True
