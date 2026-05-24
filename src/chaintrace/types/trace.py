"""Trace data models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ReasoningStep(BaseModel):
    """A single step in a reasoning chain."""

    step: int
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Trace(BaseModel):
    """Complete trace of an LLM interaction."""

    id: str | None = Field(default=None, description="Unique trace ID")
    adapter: str = Field(description="Adapter used (e.g., openai, claude)")
    model: str = Field(description="Model identifier")
    request: dict[str, Any] = Field(description="Original request payload")
    response: dict[str, Any] = Field(description="Original response payload")
    reasoning_chain: list[ReasoningStep] = Field(
        default_factory=list, description="Extracted reasoning steps"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )


class QueryFilters(BaseModel):
    """Filters for querying traces."""

    adapter: str | None = None
    model: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    search: str | None = None
    tags: list[str] = Field(default_factory=list)


class TraceStats(BaseModel):
    """Statistics about stored traces."""

    total_traces: int = 0
    total_tokens: int = 0
    total_reasoning_steps: int = 0
    by_adapter: dict[str, int] = Field(default_factory=dict)
    by_model: dict[str, int] = Field(default_factory=dict)
    storage_size_bytes: int = 0