"""Event system for ChainTrace."""

from datetime import datetime
from enum import Enum
from typing import Any, Callable

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Event types emitted by ChainTrace."""

    CAPTURE_START = "capture_start"
    CAPTURE_COMPLETE = "capture_complete"
    TRACE_STORED = "trace_stored"
    TRACE_DELETED = "trace_deleted"
    ANALYSIS_START = "analysis_start"
    ANALYSIS_COMPLETE = "analysis_complete"
    ERROR = "error"
    ADAPTER_REGISTERED = "adapter_registered"
    BACKEND_INITIALIZED = "backend_initialized"


class Event(BaseModel):
    """Event emitted by ChainTrace."""

    type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: dict[str, Any] = {}
    trace_id: str | None = None


class EventBus:
    """Simple pub/sub event bus for internal events."""

    def __init__(self) -> None:
        self._subscribers: dict[EventType, list[Callable[[Event], None]]] = {}

    def subscribe(
        self, event_type: EventType, handler: Callable[[Event], None]
    ) -> None:
        """Subscribe to an event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def unsubscribe(
        self, event_type: EventType, handler: Callable[[Event], None]
    ) -> None:
        """Unsubscribe from an event type."""
        if event_type in self._subscribers:
            self._subscribers[event_type].remove(handler)

    def publish(self, event: Event) -> None:
        """Publish an event to all subscribers."""
        if event.type in self._subscribers:
            for handler in self._subscribers[event.type]:
                handler(event)

    def clear(self) -> None:
        """Clear all subscribers."""
        self._subscribers.clear()