"""Core package - configuration, engine, exceptions, events, context."""

from chaintrace.core.config import ChainTraceConfig
from chaintrace.core.engine import ChainTraceEngine
from chaintrace.core.exceptions import (
    ChainTraceError,
    ConfigurationError,
    AdapterError,
    StorageError,
    AnalysisError,
)
from chaintrace.core.events import Event, EventType, EventBus
from chaintrace.core.context import TraceContext

__all__ = [
    "ChainTraceConfig",
    "ChainTraceEngine",
    "ChainTraceError",
    "ConfigurationError",
    "AdapterError",
    "StorageError",
    "AnalysisError",
    "Event",
    "EventType",
    "EventBus",
    "TraceContext",
]