"""Base storage backend interface."""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator

from chaintrace.types.trace import Trace, QueryFilters, TraceStats


class BaseStorageBackend(ABC):
    """Abstract base class for all storage backends.

    All storage implementations must implement this interface.
    """

    name: str

    @abstractmethod
    async def initialize(self, config: dict[str, Any]) -> None:
        """Initialize the backend (create tables, connections, etc.)."""
        pass

    @abstractmethod
    async def store(self, trace: Trace) -> None:
        """Store a single trace."""
        pass

    @abstractmethod
    async def store_batch(self, traces: list[Trace]) -> None:
        """Store multiple traces (for efficiency)."""
        pass

    @abstractmethod
    async def get(self, trace_id: str) -> Trace | None:
        """Retrieve a trace by ID."""
        pass

    @abstractmethod
    async def query(
        self,
        filters: QueryFilters,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Trace]:
        """Query traces with filters."""
        pass

    @abstractmethod
    async def delete(self, trace_id: str) -> bool:
        """Delete a trace. Returns True if deleted, False if not found."""
        pass

    @abstractmethod
    async def stats(self) -> TraceStats:
        """Get storage statistics."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Clean up connections and resources."""
        pass

    async def stream(
        self, filters: QueryFilters
    ) -> AsyncIterator[Trace]:
        """Stream traces (for large exports). Override for efficient implementation."""
        traces = await self.query(filters, limit=1000)
        for trace in traces:
            yield trace

    async def migrate_from(self, other: "BaseStorageBackend") -> int:
        """Migrate traces from another backend. Returns count of migrated traces."""
        count = 0
        async for trace in other.stream(QueryFilters()):
            await self.store(trace)
            count += 1
        return count