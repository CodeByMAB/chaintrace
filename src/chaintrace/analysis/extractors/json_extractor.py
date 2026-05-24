"""JSON CoT extractor.

Handles responses where the reasoning is embedded as JSON, e.g.:

    {"reasoning": ["step 1...", "step 2..."], "answer": "..."}
    {"steps": [{"content": "..."}, ...]}
    {"chain_of_thought": "..."}

Works on both the full response body (if it is JSON) and on code-fenced
JSON blocks embedded in a larger text response.
"""

import json
import re
from datetime import datetime

from chaintrace.analysis.extractors.base import BaseExtractor
from chaintrace.types.trace import ReasoningStep

# Keys that might contain a reasoning chain
_CHAIN_KEYS = [
    "reasoning", "chain_of_thought", "thoughts", "thinking",
    "steps", "reasoning_steps", "thought_process", "scratchpad",
]

# Code-fence pattern for JSON blocks
_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.+?\}|\[.+?\])\s*```", re.DOTALL)


def _steps_from_value(value: object) -> list[str]:
    """Turn a JSON value into a flat list of text strings."""
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                # {"content": "..."} or {"text": "..."} or {"step": 1, "content": "..."}
                text = item.get("content") or item.get("text") or item.get("reasoning") or ""
                if text:
                    parts.append(str(text))
        return parts
    return []


def _extract_from_dict(obj: dict) -> list[str]:
    """Pull reasoning text from a parsed JSON object."""
    for key in _CHAIN_KEYS:
        if key in obj:
            parts = _steps_from_value(obj[key])
            if parts:
                return parts

    # Fallback: look for any list-valued key whose items look like text
    for v in obj.values():
        if isinstance(v, list) and v and isinstance(v[0], (str, dict)):
            parts = _steps_from_value(v)
            if parts:
                return parts

    return []


class JsonExtractor(BaseExtractor):
    """Extract reasoning from JSON-structured responses."""

    name = "json"

    def can_handle(self, text: str) -> bool:
        stripped = text.strip()
        return stripped.startswith("{") or bool(_JSON_FENCE_RE.search(text))

    def extract(self, text: str) -> list[ReasoningStep]:
        candidates: list[str] = []

        # Try top-level JSON parse
        try:
            obj = json.loads(text.strip())
            if isinstance(obj, dict):
                candidates = _extract_from_dict(obj)
        except (json.JSONDecodeError, ValueError):
            pass

        # Try JSON fences if top-level parse failed
        if not candidates:
            for match in _JSON_FENCE_RE.finditer(text):
                try:
                    obj = json.loads(match.group(1))
                    if isinstance(obj, dict):
                        candidates = _extract_from_dict(obj)
                    if candidates:
                        break
                except (json.JSONDecodeError, ValueError):
                    continue

        return [
            ReasoningStep(step=i, content=s.strip(), timestamp=datetime.utcnow())
            for i, s in enumerate(candidates, start=1)
            if s.strip()
        ]
