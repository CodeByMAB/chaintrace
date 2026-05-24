"""File-based storage backend."""

import json
import uuid
from pathlib import Path
from typing import Any

from chaintrace.storage.base import BaseStorageBackend
from chaintrace.types.trace import Trace, QueryFilters, TraceStats


class FileBackend(BaseStorageBackend):
    """File-based storage backend using JSONL."""

    name = "file"

    def __init__(self) -> None:
        self._path: Path | None = None
        self._format = "jsonl"

    async def initialize(self, config: dict[str, Any]) -> None:
        """Initialize file backend."""
        self._path = Path(config.get("path", "./traces"))
        self._format = config.get("format", "jsonl")
        self._path.mkdir(parents=True, exist_ok=True)

    async def store(self, trace: Trace) -> None:
        """Store a trace to file."""
        if not self._path:
            raise RuntimeError("Storage not initialized")

        trace_id = trace.id or str(uuid.uuid4())
        trace.id = trace_id

        file_path = self._path / f"{trace_id}.{self._format}"

        if self._format == "jsonl":
            with open(file_path, "a") as f:
                f.write(trace.model_dump_json() + "\n")
        else:
            with open(file_path, "w") as f:
                f.write(trace.model_dump_json(indent=2))

    async def store_batch(self, traces: list[Trace]) -> None:
        """Store multiple traces."""
        for trace in traces:
            await self.store(trace)

    async def get(self, trace_id: str) -> Trace | None:
        """Get a trace by ID."""
        if not self._path:
            raise RuntimeError("Storage not initialized")

        file_path = self._path / f"{trace_id}.{self._format}"
        if not file_path.exists():
            return None

        with open(file_path) as f:
            if self._format == "jsonl":
                data = json.loads(f.readline())
            else:
                data = json.load(f)

        return Trace(**data)

    async def query(
        self, filters: QueryFilters, limit: int = 100, offset: int = 0
    ) -> list[Trace]:
        """Query traces from files."""
        if not self._path:
            raise RuntimeError("Storage not initialized")

        traces = []
        for file_path in sorted(self._path.glob(f"*.{self._format}"), reverse=True):
            try:
                trace = await self.get(file_path.stem)
                if trace and self._matches_filters(trace, filters):
                    traces.append(trace)
            except Exception:
                continue

        return traces[offset : offset + limit]

    async def delete(self, trace_id: str) -> bool:
        """Delete a trace file."""
        if not self._path:
            raise RuntimeError("Storage not initialized")

        file_path = self._path / f"{trace_id}.{self._format}"
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    async def stats(self) -> TraceStats:
        """Get storage statistics."""
        if not self._path:
            raise RuntimeError("Storage not initialized")

        files = list(self._path.glob(f"*.{self._format}"))
        total_size = sum(f.stat().st_size for f in files)

        by_adapter: dict[str, int] = {}
        by_model: dict[str, int] = {}

        for f in files:
            try:
                trace = await self.get(f.stem)
                if trace:
                    by_adapter[trace.adapter] = by_adapter.get(trace.adapter, 0) + 1
                    by_model[trace.model] = by_model.get(trace.model, 0) + 1
            except Exception:
                continue

        return TraceStats(
            total_traces=len(files),
            by_adapter=by_adapter,
            by_model=by_model,
            storage_size_bytes=total_size,
        )

    async def close(self) -> None:
        """No-op for file backend."""
        pass

    def _matches_filters(self, trace: Trace, filters: QueryFilters) -> bool:
        """Check if trace matches filters."""
        if filters.adapter and trace.adapter != filters.adapter:
            return False
        if filters.model and trace.model != filters.model:
            return False
        return True