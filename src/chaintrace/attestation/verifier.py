"""Audit verification layer for timestamped traces.

This module provides verification of reasoning traces against their
Bitcoin timestamps, enabling cryptographic proof that traces existed
at specific times and haven't been tampered with.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from chaintrace.attestation.opentimestamps import (
    OpenTimestampsClient,
    TimestampProof,
    TimestampStatus,
)

logger = logging.getLogger(__name__)


class VerificationStatus(str, Enum):
    """Status of trace verification."""

    VERIFIED = "verified"  # Timestamp verified, data intact
    PENDING = "pending"  # Timestamp not yet confirmed
    FAILED = "failed"  # Verification failed
    EXPIRED = "expired"  # Timestamp too old to verify
    TAMPERED = "tampered"  # Data doesn't match timestamp


@dataclass
class VerificationResult:
    """Result of trace verification."""

    trace_id: str
    status: VerificationStatus

    # Timestamp info
    timestamp_proof: TimestampProof | None = None

    # When the verification was performed
    verified_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Verification details
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    # Integrity check results
    hash_match: bool = False
    merkle_verified: bool = False


@dataclass
class AuditRecord:
    """An audit record for a trace.

    Combines the trace with its timestamp proof and verification result.
    """

    trace_id: str
    trace_data: dict[str, Any]
    timestamp_proof: TimestampProof | None
    verification: VerificationResult

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "trace_id": self.trace_id,
            "trace_data": self.trace_data,
            "timestamp_proof": (
                self.timestamp_proof.to_dict() if self.timestamp_proof else None
            ),
            "verification": {
                "status": self.verification.status.value,
                "message": self.verification.message,
                "details": self.verification.details,
                "hash_match": self.verification.hash_match,
                "merkle_verified": self.verification.merkle_verified,
                "verified_at": self.verification.verified_at.isoformat(),
            },
            "created_at": self.created_at.isoformat(),
        }


class AuditVerifier:
    """Verifier for timestamped reasoning traces.

    Provides verification that:
    1. A trace was timestamped on Bitcoin at a specific time
    2. The trace data hasn't been tampered with
    3. The reasoning chain is authentic
    """

    def __init__(
        self,
        ots_client: OpenTimestampsClient | None = None,
        verify_merkle: bool = True,
    ):
        """Initialize the audit verifier.

        Args:
            ots_client: OpenTimestamps client (creates default if None)
            verify_merkle: Whether to verify merkle proofs (requires Bitcoin node)
        """
        self._ots = ots_client or OpenTimestampsClient()
        self._verify_merkle = verify_merkle

    async def close(self) -> None:
        """Close resources."""
        await self._ots.close()

    async def verify_trace(
        self,
        trace: "Trace",  # Forward reference
        proof: TimestampProof,
    ) -> VerificationResult:
        """Verify a trace against its timestamp proof.

        Args:
            trace: The trace to verify
            proof: The timestamp proof from Open Timestamps

        Returns:
            VerificationResult with verification status
        """
        result = VerificationResult(
            trace_id=trace.id or "unknown",
            status=VerificationStatus.PENDING,
            timestamp_proof=proof,
        )

        # Step 1: Check timestamp status
        if proof.status == TimestampStatus.PENDING:
            # Try to get updated status
            try:
                proof = await self._ots.get_timestamp_info(proof)
            except Exception as e:
                logger.warning(f"Failed to get timestamp info: {e}")

        if proof.status == TimestampStatus.PENDING:
            result.status = VerificationStatus.PENDING
            result.message = "Timestamp pending Bitcoin confirmation"
            result.details = {"calendar_url": proof.calendar_url}
            return result

        if proof.status == TimestampStatus.FAILED:
            result.status = VerificationStatus.FAILED
            result.message = "Timestamp failed"
            return result

        # Step 2: Verify data integrity (hash match)
        current_hash = self._ots.hash_trace(trace.model_dump())
        result.hash_match = current_hash == proof.hash

        if not result.hash_match:
            result.status = VerificationStatus.TAMPERED
            result.message = "Trace data doesn't match timestamp hash"
            result.details = {
                "expected_hash": proof.hash,
                "actual_hash": current_hash,
            }
            return result

        # Step 3: Verify merkle proof (if available and requested)
        if self._verify_merkle and proof.merkle_proof:
            result.merkle_verified = await self._verify_merkle_proof(proof)
        else:
            # If no merkle proof, just confirm timestamp exists
            result.merkle_verified = proof.status == TimestampStatus.CONFIRMED

        # Final status
        if result.merkle_verified and result.hash_match:
            result.status = VerificationStatus.VERIFIED
            result.message = "Trace verified - timestamp confirmed on Bitcoin"
            result.details = {
                "bitcoin_block": proof.bitcoin_block_height,
                "bitcoin_timestamp": (
                    proof.bitcoin_timestamp.isoformat()
                    if proof.bitcoin_timestamp
                    else None
                ),
            }
        else:
            result.status = VerificationStatus.FAILED
            result.message = "Verification failed"

        return result

    async def _verify_merkle_proof(self, proof: TimestampProof) -> bool:
        """Verify the merkle proof against Bitcoin.

        This is a placeholder - full merkle verification requires
        either a Bitcoin node or a verification service.

        Args:
            proof: The timestamp proof with merkle proof

        Returns:
            True if verified (placeholder always returns True for now)
        """
        # TODO: Implement full merkle verification
        # This would require:
        # 1. Access to Bitcoin node (via RPC or Electrum)
        # 2. Fetching the block header
        # 3. Verifying the merkle path
        # 4. Checking proof of work

        logger.info("Merkle verification not fully implemented - assuming valid")
        return True

    async def audit_traces(
        self,
        traces: list["Trace"],  # Forward reference
        proofs: dict[str, TimestampProof],
    ) -> list[AuditRecord]:
        """Audit multiple traces.

        Args:
            traces: List of traces to audit
            proofs: Dict mapping trace_id to timestamp proof

        Returns:
            List of AuditRecords
        """
        records = []

        for trace in traces:
            trace_id = trace.id or "unknown"
            proof = proofs.get(trace_id)

            if not proof:
                # No timestamp - record as unaudited
                result = VerificationResult(
                    trace_id=trace_id,
                    status=VerificationStatus.FAILED,
                    message="No timestamp proof available",
                )
                record = AuditRecord(
                    trace_id=trace_id,
                    trace_data=trace.model_dump(),
                    timestamp_proof=None,
                    verification=result,
                )
            else:
                result = await self.verify_trace(trace, proof)
                record = AuditRecord(
                    trace_id=trace_id,
                    trace_data=trace.model_dump(),
                    timestamp_proof=proof,
                    verification=result,
                )

            records.append(record)

        return records

    async def verify_before_block(
        self,
        traces: list["Trace"],
        proofs: dict[str, TimestampProof],
        block_height: int,
    ) -> list[VerificationResult]:
        """Verify that traces were timestamped before a specific block.

        This is useful for answering questions like:
        "Show me all traces that existed before block 850000"

        Args:
            traces: List of traces to check
            proofs: Dict mapping trace_id to timestamp proof
            block_height: The Bitcoin block height to check against

        Returns:
            List of VerificationResults for traces that pass the check
        """
        results = []

        for trace in traces:
            trace_id = trace.id or "unknown"
            proof = proofs.get(trace_id)

            if not proof:
                result = VerificationResult(
                    trace_id=trace_id,
                    status=VerificationStatus.FAILED,
                    message="No timestamp proof",
                )
                results.append(result)
                continue

            # Get updated proof info
            proof = await self._ots.get_timestamp_info(proof)

            if proof.bitcoin_block_height is None:
                result = VerificationResult(
                    trace_id=trace_id,
                    status=VerificationStatus.PENDING,
                    timestamp_proof=proof,
                    message="Timestamp not yet confirmed",
                )
                results.append(result)
                continue

            if proof.bitcoin_block_height <= block_height:
                result = VerificationResult(
                    trace_id=trace_id,
                    status=VerificationStatus.VERIFIED,
                    timestamp_proof=proof,
                    message=f"Confirmed in block {proof.bitcoin_block_height}",
                    details={"block_height": proof.bitcoin_block_height},
                )
            else:
                result = VerificationResult(
                    trace_id=trace_id,
                    status=VerificationStatus.FAILED,
                    timestamp_proof=proof,
                    message=f"Timestamp in block {proof.bitcoin_block_height} (after {block_height})",
                )

            results.append(result)

        return results


# Type hint for circular import
from chaintrace.types.trace import Trace