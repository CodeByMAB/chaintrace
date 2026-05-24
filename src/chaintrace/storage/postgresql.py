"""PostgreSQL storage backend."""

from typing import Any

from chaintrace.storage.base import BaseStorageBackend
from chaintrace.types.trace import Trace, QueryFilters, TraceStats


class PostgresBackend(BaseStorageBackend):
    """PostgreSQL storage backend (requires asyncpg)."""

    name = "postgresql"

    def __init__(self) -> None:
        self._config: dict[str, Any] = {}
        self._pool = None

    async def initialize(self, config: dict[str, Any]) -> None:
        """Initialize PostgreSQL connection pool."""
        try:
            import asyncpg
        except ImportError:
            raise ImportError(
                "PostgreSQL backend requires asyncpg. Install with: pip install chaintrace[postgresql]"
            )

        self._config = config
        self._pool = await asyncpg.create_pool(
            host=config.get("host", "localhost"),
            port=config.get("port", 5432),
            user=config.get("username", "postgres"),
            password=config.get("password"),
            database=config.get("database", "chaintrace"),
            min_size=config.get("pool_size", 10),
        )

        async with self._pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS traces (
                    id TEXT PRIMARY KEY,
                    adapter TEXT NOT NULL,
                    model TEXT NOT NULL,
                    request JSONB NOT NULL,
                    response JSONB NOT NULL,
                    reasoning_chain JSONB NOT NULL,
                    metadata JSONB NOT NULL,
                    created_at TIMESTAMP NOT NULL
                )
            """)
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_adapter ON traces(adapter)"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_model ON traces(model)"
            )

    async def store(self, trace: Trace) -> None:
        """Store a trace."""
        import uuid

        trace_id = trace.id or str(uuid.uuid4())

        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO traces
                   (id, adapter, model, request, response, reasoning_chain, metadata, created_at)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                   ON CONFLICT (id) DO UPDATE SET
                   adapter = EXCLUDED.adapter,
                   model = EXCLUDED.model,
                   request = EXCLUDED.request,
                   response = EXCLUDED.response,
                   reasoning_chain = EXCLUDED.reasoning_chain,
                   metadata = EXCLUDED.metadata,
                   created_at = EXCLUDED.created_at""",
                trace_id,
                trace.adapter,
                trace.model,
                trace.request,
                trace.response,
                [s.model_dump() for s in trace.reasoning_chain],
                trace.metadata,
                trace.created_at,
            )

    async def store_batch(self, traces: list[Trace]) -> None:
        """Store multiple traces."""
        for trace in traces:
            await self.store(trace)

    async def get(self, trace_id: str) -> Trace | None:
        """Get a trace by ID."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM traces WHERE id = $1", trace_id
            )
            if not row:
                return None
            return self._row_to_trace(row)

    async def query(
        self, filters: QueryFilters, limit: int = 100, offset: int = 0
    ) -> list[Trace]:
        """Query traces with filters."""
        query = "SELECT * FROM traces WHERE 1=1"
        params = []
        param_idx = 1

        if filters.adapter:
            query += f" AND adapter = ${param_idx}"
            params.append(filters.adapter)
            param_idx += 1

        if filters.model:
            query += f" AND model = ${param_idx}"
            params.append(filters.model)
            param_idx += 1

        query += f" ORDER BY created_at DESC LIMIT ${param_idx} OFFSET {param_idx + 1}"
        params.extend([limit, offset])

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [self._row_to_trace(row) for row in rows]

    async def delete(self, trace_id: str) -> bool:
        """Delete a trace."""
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM traces WHERE id = $1", trace_id
            )
            return result == "DELETE 1"

    async def stats(self) -> TraceStats:
        """Get storage statistics."""
        async with self._pool.acquire() as conn:
            total = await conn.fetchval("SELECT COUNT(*) FROM traces")

            adapter_counts = await conn.fetch(
                "SELECT adapter, COUNT(*) FROM traces GROUP BY adapter"
            )
            by_adapter = {r["adapter"]: r["count"] for r in adapter_counts}

            model_counts = await conn.fetch(
                "SELECT model, COUNT(*) FROM traces GROUP BY model"
            )
            by_model = {r["model"]: r["count"] for r in model_counts}

        return TraceStats(
            total_traces=total,
            by_adapter=by_adapter,
            by_model=by_model,
        )

    async def close(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None

    def _row_to_trace(self, row: dict) -> Trace:
        """Convert database row to Trace."""
        from chaintrace.types.trace import ReasoningStep

        reasoning_steps = [
            ReasoningStep(**s) for s in row["reasoning_chain"]
        ]

        return Trace(
            id=row["id"],
            adapter=row["adapter"],
            model=row["model"],
            request=row["request"],
            response=row["response"],
            reasoning_chain=reasoning_steps,
            metadata=row["metadata"],
            created_at=row["created_at"],
        )