"""Log parser capture source.

Reads JSONL log files where each line is a JSON object containing either:
  - {"request": {...}, "response": {...}, "adapter": "openai"}  (wrapped format)
  - A raw OpenAI/Anthropic response object with a "request" key embedded

Each file may contain many lines; each line becomes one trace.
"""

import json
import logging
from pathlib import Path
from typing import AsyncIterator

from chaintrace.capture.base import BaseCaptureSource

logger = logging.getLogger(__name__)

# Keys that hint at which adapter produced the response
_ADAPTER_HINTS = {
    "choices": "openai",       # OpenAI completions
    "content": "anthropic",    # Anthropic messages
}


def _detect_adapter(response: dict) -> str:
    """Guess adapter from response shape."""
    for key, adapter in _ADAPTER_HINTS.items():
        if key in response:
            return adapter
    return "openai"


def _parse_line(line: str, source_file: Path) -> tuple[dict, dict, str] | None:
    """Parse one JSONL line into (request, response, adapter).

    Accepts two formats:
      1. Wrapped: {"request": {...}, "response": {...}, "adapter": "openai"}
      2. Flat:    {"model": "...", "choices": [...], "_request": {...}}
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    try:
        obj = json.loads(line)
    except json.JSONDecodeError as exc:
        logger.warning("Skipping malformed JSON in %s: %s", source_file, exc)
        return None

    if not isinstance(obj, dict):
        return None

    # Wrapped format
    if "request" in obj and "response" in obj:
        request = obj["request"]
        response = obj["response"]
        adapter = obj.get("adapter") or _detect_adapter(response)
        return request, response, adapter

    # Flat format — response is the whole object, request may be under "_request"
    request = obj.pop("_request", {})
    adapter = obj.get("adapter") or _detect_adapter(obj)
    return request, obj, adapter


class LogParser(BaseCaptureSource):
    """Parse JSONL log files into trace records.

    Args:
        paths: One or more file paths or glob patterns to process.
        adapter: Override adapter detection with a fixed adapter name.
    """

    def __init__(self, paths: list[str | Path], adapter: str | None = None) -> None:
        self._paths = [Path(p) for p in paths]
        self._adapter_override = adapter

    @classmethod
    def from_directory(
        cls,
        directory: str | Path,
        pattern: str = "*.jsonl",
        recursive: bool = False,
    ) -> "LogParser":
        """Create a LogParser that scans a directory."""
        base = Path(directory)
        glob_fn = base.rglob if recursive else base.glob
        files = sorted(glob_fn(pattern))
        return cls(files)

    async def records(self) -> AsyncIterator[tuple[dict, dict, str]]:
        """Yield (request, response, adapter) tuples from all matching files."""
        for path in self._paths:
            if not path.exists():
                logger.warning("File not found, skipping: %s", path)
                continue

            if path.suffix in {".jsonl", ".ndjson", ".json"}:
                async for record in self._parse_file(path):
                    yield record
            else:
                logger.warning("Unsupported file type, skipping: %s", path)

    async def _parse_file(self, path: Path) -> AsyncIterator[tuple[dict, dict, str]]:
        """Yield records from a single file."""
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            logger.error("Cannot read %s: %s", path, exc)
            return

        # A plain .json file may be a single object or a list
        if path.suffix == ".json":
            try:
                data = json.loads(text)
            except json.JSONDecodeError as exc:
                logger.warning("Malformed JSON in %s: %s", path, exc)
                return

            items = data if isinstance(data, list) else [data]
            for item in items:
                line = json.dumps(item)
                result = _parse_line(line, path)
                if result:
                    req, resp, adapter = result
                    yield req, resp, self._adapter_override or adapter
            return

        # JSONL: one JSON object per line
        for line in text.splitlines():
            result = _parse_line(line, path)
            if result:
                req, resp, adapter = result
                yield req, resp, self._adapter_override or adapter
