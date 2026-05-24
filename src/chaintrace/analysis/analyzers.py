"""Built-in analyzers for trace analysis."""

from abc import ABC, abstractmethod
from typing import Any

from chaintrace.types.trace import Trace


class BaseAnalyzer(ABC):
    """Base class for trace analyzers."""

    name: str

    @abstractmethod
    async def analyze(self, trace: Trace) -> dict[str, Any]:
        """Analyze a trace and return results."""
        pass


class TokenCountAnalyzer(BaseAnalyzer):
    """Analyze token usage in a trace."""

    name = "token_count"

    async def analyze(self, trace: Trace) -> dict[str, Any]:
        """Calculate token counts from trace."""
        usage = trace.response.get("usage", {})
        return {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "reasoning_steps": len(trace.reasoning_chain),
        }


class StepCountAnalyzer(BaseAnalyzer):
    """Analyze reasoning step count."""

    name = "step_count"

    async def analyze(self, trace: Trace) -> dict[str, Any]:
        """Count reasoning steps."""
        return {
            "total_steps": len(trace.reasoning_chain),
            "avg_step_length": (
                sum(len(s.content) for s in trace.reasoning_chain)
                / len(trace.reasoning_chain)
                if trace.reasoning_chain
                else 0
            ),
            "total_chars": sum(len(s.content) for s in trace.reasoning_chain),
        }


class LatencyAnalyzer(BaseAnalyzer):
    """Analyze request/response latency."""

    name = "latency"

    async def analyze(self, trace: Trace) -> dict[str, Any]:
        """Calculate latency metrics."""
        created_at = trace.created_at

        # Try to extract timing from response
        response_ms = trace.response.get("response_ms")

        if response_ms:
            return {
                "response_time_ms": response_ms,
                "estimated_time_per_token_ms": (
                    response_ms / trace.response.get("usage", {}).get("completion_tokens", 1)
                    if trace.response.get("usage", {}).get("completion_tokens")
                    else 0
                ),
            }

        return {"response_time_ms": None, "note": "Timing not available"}