"""Analysis pipeline for running analyzers on traces."""

from typing import Any

from chaintrace.types.trace import Trace
from chaintrace.analysis.analyzers import (
    TokenCountAnalyzer,
    StepCountAnalyzer,
    LatencyAnalyzer,
)


class AnalysisPipeline:
    """Pipeline for running multiple analyzers on traces."""

    def __init__(self) -> None:
        self._analyzers: dict[str, Any] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register default built-in analyzers."""
        self.register("token_count", TokenCountAnalyzer())
        self.register("step_count", StepCountAnalyzer())
        self.register("latency", LatencyAnalyzer())

    def register(self, name: str, analyzer: Any) -> None:
        """Register an analyzer."""
        self._analyzers[name] = analyzer

    async def run(
        self, trace: Trace, analyzer_names: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Run analyzers on a trace.

        Args:
            trace: The trace to analyze
            analyzer_names: List of analyzer names to run. If None, runs all.

        Returns:
            List of analysis results
        """
        results = []

        analyzers_to_run = (
            analyzer_names if analyzer_names else list(self._analyzers.keys())
        )

        for name in analyzers_to_run:
            if name in self._analyzers:
                analyzer = self._analyzers[name]
                result = await analyzer.analyze(trace)
                results.append({"analyzer": name, "result": result})

        return results

    def list_available(self) -> list[str]:
        """List all registered analyzers."""
        return list(self._analyzers.keys())