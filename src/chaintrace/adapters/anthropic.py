"""Anthropic adapter for reasoning extraction."""

from datetime import datetime
from typing import Any

from chaintrace.adapters.base import BaseAdapter
from chaintrace.types.trace import ReasoningStep


class AnthropicAdapter(BaseAdapter):
    """Adapter for Anthropic (Claude) API responses."""

    name = "anthropic"

    def extract_reasoning(self, response: dict[str, Any]) -> list[ReasoningStep]:
        """Extract reasoning from Anthropic response.

        Handles:
        - Claude 3.5 Sonnet: thinking in content blocks
        - Standard: content as reasoning
        """
        steps = []

        # Check for thinking blocks (Claude 3.5+)
        if "content" in response:
            content = response["content"]
            if isinstance(content, list):
                for block in content:
                    if block.get("type") == "thinking":
                        thinking = block.get("thinking", "")
                        for i, line in enumerate(thinking.split("\n")):
                            if line.strip():
                                steps.append(
                                    ReasoningStep(
                                        step=i + 1,
                                        content=line.strip(),
                                        timestamp=datetime.utcnow(),
                                    )
                                )
            elif isinstance(content, str):
                # Legacy format
                for i, line in enumerate(content.split("\n\n")):
                    if line.strip():
                        steps.append(
                            ReasoningStep(
                                step=i + 1,
                                content=line.strip(),
                                timestamp=datetime.utcnow(),
                            )
                        )

        return steps

    def extract_content(self, response: dict[str, Any]) -> str:
        """Extract main content from Anthropic response."""
        if "content" in response:
            content = response["content"]
            if isinstance(content, list):
                text_parts = [
                    block.get("text", "")
                    for block in content
                    if block.get("type") == "text"
                ]
                return "\n".join(text_parts)
            elif isinstance(content, str):
                return content
        return ""

    def extract_usage(self, response: dict[str, Any]) -> dict[str, int]:
        """Extract token usage from Anthropic response."""
        if "usage" in response:
            usage = response["usage"]
            return {
                "prompt_tokens": usage.get("input_tokens", 0),
                "completion_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("input_tokens", 0)
                + usage.get("output_tokens", 0),
            }
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def supports(self, response: dict[str, Any]) -> bool:
        """Check if response is from Anthropic."""
        return "content" in response and isinstance(response["content"], (list, str))