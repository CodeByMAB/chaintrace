"""Base adapter interface."""

from abc import ABC, abstractmethod
from typing import Any

from chaintrace.types.trace import ReasoningStep


class BaseAdapter(ABC):
    """Abstract base class for LLM provider adapters.

    Adapters extract reasoning chains from provider responses.
    """

    name: str

    @abstractmethod
    def extract_reasoning(self, response: dict[str, Any]) -> list[ReasoningStep]:
        """Extract reasoning steps from a response.

        Args:
            response: The raw response from the LLM provider

        Returns:
            List of reasoning steps extracted from the response
        """
        pass

    @abstractmethod
    def extract_content(self, response: dict[str, Any]) -> str:
        """Extract the main content from a response.

        Args:
            response: The raw response from the LLM provider

        Returns:
            The main text content of the response
        """
        pass

    @abstractmethod
    def extract_usage(self, response: dict[str, Any]) -> dict[str, int]:
        """Extract token usage from a response.

        Args:
            response: The raw response from the LLM provider

        Returns:
            Dict with prompt_tokens, completion_tokens, total_tokens
        """
        pass

    def supports(self, response: dict[str, Any]) -> bool:
        """Check if this adapter can handle the given response.

        Override to add custom detection logic.
        """
        return True