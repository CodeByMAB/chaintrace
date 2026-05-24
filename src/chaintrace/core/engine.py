"""Main ChainTrace engine - orchestration of all components."""

from typing import Any

from chaintrace.core.config import ChainTraceConfig
from chaintrace.core.events import EventBus
from chaintrace.core.exceptions import StorageError, AdapterError
from chaintrace.storage.registry import StorageBackendRegistry
from chaintrace.adapters.registry import AdapterRegistry
from chaintrace.analysis.pipeline import AnalysisPipeline
from chaintrace.types.trace import Trace, QueryFilters, TraceStats


class ChainTraceEngine:
    """Main orchestration engine for ChainTrace.

    Coordinates capture, storage, and analysis of reasoning traces.
    """

    def __init__(self, config: ChainTraceConfig) -> None:
        self.config = config
        self.event_bus = EventBus()
        self.storage_registry = StorageBackendRegistry()
        self.adapter_registry = AdapterRegistry()
        self.analyzer_pipeline = AnalysisPipeline()

        self._storage = None
        self._adapters: dict[str, Any] = {}

    async def initialize(self) -> None:
        """Initialize the engine and its components."""
        # Initialize storage backend
        storage_config = self.config.storage.model_dump(
            exclude_none=True, exclude={"backend"}
        )
        backend_name = self.config.storage.backend
        self._storage = self.storage_registry.get(backend_name, storage_config)
        await self._storage.initialize(
            storage_config.get(backend_name, {}) or {}
        )

        # Initialize adapters
        self.adapter_registry.discover_builtins()
        for adapter_name, adapter_config in self.config.adapters.items():
            self._adapters[adapter_name] = self.adapter_registry.get(
                adapter_name, adapter_config
            )

    async def close(self) -> None:
        """Clean up resources."""
        if self._storage:
            await self._storage.close()

    async def capture(
        self,
        adapter_name: str,
        request: dict[str, Any],
        response: dict[str, Any],
    ) -> Trace:
        """Capture a request/response pair as a trace."""
        adapter = self._adapters.get(adapter_name)
        if not adapter:
            raise AdapterError(f"Adapter not found: {adapter_name}")

        # Extract reasoning from response
        reasoning_steps = adapter.extract_reasoning(response)

        # Create trace
        trace = Trace(
            adapter=adapter_name,
            model=request.get("model", "unknown"),
            request=request,
            response=response,
            reasoning_chain=reasoning_steps,
            metadata={
                "captured_at": "now",  # TODO: use actual timestamp
            },
        )

        # Store trace
        await self._storage.store(trace)

        return trace

    async def get_trace(self, trace_id: str) -> Trace | None:
        """Get a trace by ID."""
        return await self._storage.get(trace_id)

    async def query_traces(
        self,
        filters: QueryFilters | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Trace]:
        """Query traces with optional filters."""
        return await self._storage.query(filters or QueryFilters(), limit, offset)

    async def delete_trace(self, trace_id: str) -> bool:
        """Delete a trace by ID."""
        return await self._storage.delete(trace_id)

    async def analyze_trace(
        self, trace: Trace, analyzers: list[str] | None = None
    ) -> list[Any]:
        """Run analysis on a trace."""
        return await self.analyzer_pipeline.run(trace, analyzers)

    async def get_stats(self) -> TraceStats:
        """Get storage statistics."""
        return await self._storage.stats()

    # === Bitcoin Timestamping (Open Timestamps) ===

    def _check_attestation_enabled(self) -> None:
        """Check if attestation is enabled, raise if not."""
        if not self.config.attestation.enabled:
            from chaintrace.core.exceptions import ConfigurationError

            raise ConfigurationError(
                "Bitcoin timestamping is not enabled. "
                "Set attestation.enabled=true in config or CHAINTRACE_ATTESTATION_ENABLED=true "
                "to enable Open Timestamps."
            )

    async def timestamp_trace(
        self,
        trace: Trace,
        calendar_url: str | None = None,
    ) -> Trace:
        """Timestamp a trace on Bitcoin via Open Timestamps.

        Args:
            trace: The trace to timestamp
            calendar_url: Optional specific calendar server

        Returns:
            The trace with timestamp proof attached
        """
        from chaintrace.core.exceptions import ConfigurationError
        from chaintrace.attestation import OpenTimestampsClient

        self._check_attestation_enabled()

        # Use config calendar if not specified
        calendar = calendar_url or self.config.attestation.default_calendar

        ots = OpenTimestampsClient()
        try:
            proof = await ots.timestamp_trace(trace, calendar)

            # Update trace with timestamp proof
            trace.timestamp_proof = proof.to_dict()
            trace.timestamped = True

            # Store updated trace
            await self._storage.store(trace)

            return trace
        finally:
            await ots.close()

    async def timestamp_all(
        self,
        filters: QueryFilters | None = None,
        calendar_url: str | None = None,
    ) -> list[Trace]:
        """Timestamp all untimestamped traces.

        Args:
            filters: Optional filters to select traces
            calendar_url: Optional specific calendar server

        Returns:
            List of timestamped traces
        """
        from chaintrace.attestation import OpenTimestampsClient
        from chaintrace.types.trace import Trace

        self._check_attestation_enabled()

        # Use config calendar if not specified
        calendar = calendar_url or self.config.attestation.default_calendar

        traces = await self.query_traces(filters, limit=10000)

        # Filter to untimestamped
        untimestamped = [t for t in traces if not t.timestamped]

        if not untimestamped:
            return []

        ots = OpenTimestampsClient()
        timestamped = []

        try:
            for trace in untimestamped:
                try:
                    proof = await ots.timestamp_trace(trace, calendar)
                    trace.timestamp_proof = proof.to_dict()
                    trace.timestamped = True
                    await self._storage.store(trace)
                    timestamped.append(trace)
                except Exception as e:
                    # Log but continue
                    import logging

                    logging.warning(f"Failed to timestamp trace {trace.id}: {e}")

            return timestamped
        finally:
            await ots.close()

    async def verify_trace_timestamp(self, trace: Trace) -> dict[str, Any]:
        """Verify a trace's timestamp proof.

        Args:
            trace: The trace to verify

        Returns:
            Verification result dictionary
        """
        from chaintrace.attestation import AuditVerifier
        from chaintrace.attestation.opentimestamps import TimestampProof

        if not trace.timestamp_proof:
            return {
                "verified": False,
                "message": "No timestamp proof available",
            }

        proof = TimestampProof.from_dict(trace.timestamp_proof)
        verifier = AuditVerifier()

        try:
            result = await verifier.verify_trace(trace, proof)
            return {
                "verified": result.status.value == "verified",
                "status": result.status.value,
                "message": result.message,
                "details": result.details,
            }
        finally:
            await verifier.close()

    async def audit_traces_before_block(
        self,
        block_height: int,
        filters: QueryFilters | None = None,
    ) -> list[dict[str, Any]]:
        """Audit traces that were timestamped before a specific block.

        This answers: "Show me all traces that existed before block X"

        Args:
            block_height: The Bitcoin block height to check
            filters: Optional filters for traces

        Returns:
            List of audit results
        """
        from chaintrace.attestation import AuditVerifier
        from chaintrace.attestation.opentimestamps import TimestampProof

        traces = await self.query_traces(filters, limit=10000)

        # Build proof dict
        proofs: dict[str, TimestampProof] = {}
        for trace in traces:
            if trace.id and trace.timestamp_proof:
                proofs[trace.id] = TimestampProof.from_dict(trace.timestamp_proof)

        verifier = AuditVerifier()
        results = []

        try:
            verifications = await verifier.verify_before_block(traces, proofs, block_height)

            for v in verifications:
                results.append({
                    "trace_id": v.trace_id,
                    "status": v.status.value,
                    "message": v.message,
                    "details": v.details,
                })

            return results
        finally:
            await verifier.close()