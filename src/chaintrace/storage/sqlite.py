"""SQLite storage backend."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import aiosqlite

from chaintrace.storage.base import BaseStorageBackend
from chaintrace.types.trace import QueryFilters, ReasoningStep, Trace, TraceStats


class SqliteBackend(BaseStorageBackend):
    """SQLite storage backend using aiosqlite."""

    name = "sqlite"

    def __init__(self) -> None:
        self._db: aiosqlite.Connection | None = None
        self._path = "./chaintrace.db"

    async def initialize(self, config: dict[str, Any]) -> None:
        """Initialize SQLite database."""
        self._path = config.get("path", "./chaintrace.db")
        self._db = await aiosqlite.connect(self._path)

        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS traces (
                id TEXT PRIMARY KEY,
                adapter TEXT NOT NULL,
                model TEXT NOT NULL,
                request TEXT NOT NULL,
                response TEXT NOT NULL,
                reasoning_chain TEXT NOT NULL,
                metadata TEXT NOT NULL,
                created_at TEXT NOT NULL,
                timestamp_proof TEXT,
                timestamped INTEGER NOT NULL DEFAULT 0
            )
        """)

        # Migrate existing databases that predate these columns
        for col, definition in [
            ("timestamp_proof", "TEXT"),
            ("timestamped", "INTEGER NOT NULL DEFAULT 0"),
        ]:
            try:
                await self._db.execute(f"ALTER TABLE traces ADD COLUMN {col} {definition}")
            except Exception:
                pass  # Column already exists

        await self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_adapter ON traces(adapter)"
        )
        await self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_model ON traces(model)"
        )
        await self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_created_at ON traces(created_at)"
        )

        await self._db.commit()

    async def store(self, trace: Trace) -> None:
        """Store a trace in SQLite."""
        if not self._db:
            raise RuntimeError("Database not initialized")

        trace_id = trace.id or str(uuid.uuid4())
        trace.id = trace_id

        await self._db.execute(
            """INSERT OR REPLACE INTO traces
               (id, adapter, model, request, response, reasoning_chain, metadata,
                created_at, timestamp_proof, timestamped)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                trace_id,
                trace.adapter,
                trace.model,
                json.dumps(trace.request),
                json.dumps(trace.response),
                json.dumps([s.model_dump(mode="json") for s in trace.reasoning_chain]),
                json.dumps(trace.metadata),
                trace.created_at.isoformat(),
                json.dumps(trace.timestamp_proof) if trace.timestamp_proof else None,
                1 if trace.timestamped else 0,
            ),
        )
        await self._db.commit()

    async def store_batch(self, traces: list[Trace]) -> None:
        """Store multiple traces."""
        for trace in traces:
            await self.store(trace)

    async def get(self, trace_id: str) -> Trace | None:
        """Get a trace by ID."""
        if not self._db:
            raise RuntimeError("Database not initialized")

        async with self._db.execute(
            "SELECT * FROM traces WHERE id = ?", (trace_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            return self._row_to_trace(row)

    async def query(
        self, filters: QueryFilters, limit: int = 100, offset: int = 0
    ) -> list[Trace]:
        """Query traces with filters."""
        if not self._db:
            raise RuntimeError("Database not initialized")

        q = "SELECT * FROM traces WHERE 1=1"
        params: list[Any] = []

        if filters.adapter:
            q += " AND adapter = ?"
            params.append(filters.adapter)

        if filters.model:
            q += " AND model = ?"
            params.append(filters.model)

        if filters.start_date:
            q += " AND created_at >= ?"
            params.append(filters.start_date.isoformat())

        if filters.end_date:
            q += " AND created_at <= ?"
            params.append(filters.end_date.isoformat())

        q += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        async with self._db.execute(q, params) as cursor:
            rows = await cursor.fetchall()
            return [self._row_to_trace(row) for row in rows]

    async def delete(self, trace_id: str) -> bool:
        """Delete a trace."""
        if not self._db:
            raise RuntimeError("Database not initialized")

        cursor = await self._db.execute(
            "DELETE FROM traces WHERE id = ?", (trace_id,)
        )
        await self._db.commit()
        return cursor.rowcount > 0

    async def stats(self) -> TraceStats:
        """Get storage statistics."""
        if not self._db:
            raise RuntimeError("Database not initialized")

        async with self._db.execute("SELECT COUNT(*) FROM traces") as cursor:
            total_traces = (await cursor.fetchone())[0]

        async with self._db.execute(
            "SELECT adapter, COUNT(*) FROM traces GROUP BY adapter"
        ) as cursor:
            by_adapter = {row[0]: row[1] for row in await cursor.fetchall()}

        async with self._db.execute(
            "SELECT model, COUNT(*) FROM traces GROUP BY model"
        ) as cursor:
            by_model = {row[0]: row[1] for row in await cursor.fetchall()}

        path = Path(self._path)
        size = path.stat().st_size if path.exists() else 0

        return TraceStats(
            total_traces=total_traces,
            by_adapter=by_adapter,
            by_model=by_model,
            storage_size_bytes=size,
        )

    async def close(self) -> None:
        """Close database connection."""
        if self._db:
            await self._db.close()
            self._db = None

    def _row_to_trace(self, row: tuple) -> Trace:
        """Convert a database row to a Trace."""
        reasoning_chain = json.loads(row[5])
        reasoning_steps = [
            ReasoningStep(
                step=s["step"],
                content=s["content"],
                timestamp=datetime.fromisoformat(s["timestamp"]),
            )
            for s in reasoning_chain
        ]

        timestamp_proof = json.loads(row[8]) if len(row) > 8 and row[8] else None
        timestamped = bool(row[9]) if len(row) > 9 else False

        return Trace(
            id=row[0],
            adapter=row[1],
            model=row[2],
            request=json.loads(row[3]),
            response=json.loads(row[4]),
            reasoning_chain=reasoning_steps,
            metadata=json.loads(row[6]),
            created_at=datetime.fromisoformat(row[7]),
            timestamp_proof=timestamp_proof,
            timestamped=timestamped,
        )
