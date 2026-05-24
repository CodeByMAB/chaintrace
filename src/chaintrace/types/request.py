"""Request payload types."""

from typing import Any

from pydantic import BaseModel


class RequestPayload(BaseModel):
    """Model-agnostic request representation."""

    model: str
    messages: list[dict[str, Any]]
    parameters: dict[str, Any] = {}
    temperature: float | None = None
    max_tokens: int | None = None
    stream: bool = False

    class Config:
        extra = "allow"