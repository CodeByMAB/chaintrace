"""Base capture interface."""

from abc import ABC, abstractmethod
from typing import AsyncIterator

from chaintrace.types.trace import Trace


class BaseCaptureSource(ABC):
    """Abstract base for all capture sources.

    A capture source yields (request, response, adapter_hint) tuples that
    the engine can turn into Trace objects.
    """

    @abstractmethod
    async def records(self) -> AsyncIterator[tuple[dict, dict, str]]:
        """Yield (request, response, adapter_name) tuples."""
        # mypy requires a yield in abstract async generators
        return
        yield  # type: ignore[misc]

    async def close(self) -> None:
        """Release any held resources."""
