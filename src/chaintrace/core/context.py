"""Trace context management for SDK capture mode."""

from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class TraceContext:
    """Context manager for trace capture in SDK mode."""

    trace_id: str | None = None
    adapter: str = "openai"
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.utcnow)
    ended_at: datetime | None = None

    def add_tag(self, tag: str) -> None:
        """Add a tag to this trace."""
        self.tags.append(tag)

    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to this trace."""
        self.metadata[key] = value

    def end(self) -> None:
        """Mark the trace as ended."""
        self.ended_at = datetime.utcnow()

    @property
    def duration_ms(self) -> int | None:
        """Get trace duration in milliseconds."""
        if self.ended_at:
            return int((self.ended_at - self.started_at).total_seconds() * 1000)
        return None

    @property
    def is_active(self) -> bool:
        """Check if trace is still active."""
        return self.ended_at is None


@contextmanager
def trace(adapter: str = "openai", **metadata: Any):
    """Context manager for tracing LLM calls."""
    ctx = TraceContext(adapter=adapter, metadata=metadata)
    try:
        yield ctx
    finally:
        ctx.end()


@asynccontextmanager
async def atrace(adapter: str = "openai", **metadata: Any):
    """Async context manager for tracing LLM calls."""
    ctx = TraceContext(adapter=adapter, metadata=metadata)
    try:
        yield ctx
    finally:
        ctx.end()