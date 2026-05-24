"""Adapter registry for managing LLM provider adapters."""

from typing import Any

from chaintrace.adapters.base import BaseAdapter
from chaintrace.adapters.openai import OpenAIAdapter
from chaintrace.adapters.anthropic import AnthropicAdapter


class AdapterRegistry:
    """Registry for managing LLM provider adapters."""

    def __init__(self) -> None:
        self._adapters: dict[str, type[BaseAdapter]] = {}

    def register(self, adapter_class: type[BaseAdapter]) -> None:
        """Register an adapter class."""
        self._adapters[adapter_class.name] = adapter_class

    def discover_builtins(self) -> None:
        """Register all built-in adapters."""
        self.register(OpenAIAdapter)
        self.register(AnthropicAdapter)

    def get(self, name: str, config: dict[str, Any] | None = None) -> BaseAdapter:
        """Get an adapter instance by name."""
        if name not in self._adapters:
            raise ValueError(
                f"Unknown adapter: {name}. Available: {list(self._adapters.keys())}"
            )
        return self._adapters[name]()

    def list_available(self) -> list[str]:
        """List all registered adapter names."""
        return list(self._adapters.keys())