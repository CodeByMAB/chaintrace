"""OpenAI adapter for reasoning extraction."""

from datetime import datetime
from typing import Any

from chaintrace.adapters.base import BaseAdapter
from chaintrace.types.trace import ReasoningStep


class OpenAIAdapter(BaseAdapter):
    """Adapter for OpenAI API responses."""

    name = "openai"

    def extract_reasoning(self, response: dict[str, Any]) -> list[ReasoningStep]:
        """Extract reasoning from OpenAI response.

        Handles:
        - o1 models: reasoning_content in usage
        - Standard completions: content as reasoning
        - Streaming: not handled (use accumulate)
        """
        steps = []

        # Check for o1 reasoning (stored in usage.reasoning_content)
        if "usage" in response:
            reasoning_content = response["usage"].get("reasoning_content")
            if reasoning_content:
                # o1 models store reasoning as a single block
                for i, line in enumerate(reasoning_content.split("\n")):
                    if line.strip():
                        steps.append(
                            ReasoningStep(
                                step=i + 1,
                                content=line.strip(),
                                timestamp=datetime.utcnow(),
                            )
                        )

        # Check for standard content
        if "choices" in response and response["choices"]:
            choice = response["choices"][0]
            message = choice.get("message", {})
            content = message.get("content", "")

            # If no o1 reasoning, use content as reasoning
            if not steps and content:
                # Split content into logical chunks (paragraphs or numbered items)
                chunks = content.split("\n\n")
                for i, chunk in enumerate(chunks):
                    if chunk.strip():
                        steps.append(
                            ReasoningStep(
                                step=i + 1,
                                content=chunk.strip(),
                                timestamp=datetime.utcnow(),
                            )
                        )

        return steps

    def extract_content(self, response: dict[str, Any]) -> str:
        """Extract main content from OpenAI response."""
        if "choices" in response and response["choices"]:
            return response["choices"][0].get("message", {}).get("content", "")
        return ""

    def extract_usage(self, response: dict[str, Any]) -> dict[str, int]:
        """Extract token usage from OpenAI response."""
        if "usage" in response:
            usage = response["usage"]
            return {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            }
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def supports(self, response: dict[str, Any]) -> bool:
        """Check if response is from OpenAI."""
        return "choices" in response or "usage" in response