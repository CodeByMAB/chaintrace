"""Attestation module for Bitcoin timestamping via Open Timestamps."""

from chaintrace.attestation.opentimestamps import (
    OpenTimestampsClient,
    TimestampProof,
    TimestampStatus,
)
from chaintrace.attestation.verifier import AuditVerifier, VerificationResult

__all__ = [
    "OpenTimestampsClient",
    "TimestampProof",
    "TimestampStatus",
    "AuditVerifier",
    "VerificationResult",
]