"""Response payload types."""

from typing import Any

from pydantic import BaseModel


class ResponsePayload(BaseModel):
    """Model-agnostic response representation."""

    content: str
    reasoning: str | None = None
    usage: dict[str, int] = {}
    model: str
    raw: dict[str, Any] = {}

    class Config:
        extra = "allow"