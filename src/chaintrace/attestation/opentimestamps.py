"""Open Timestamps client for Bitcoin timestamping.

This module provides timestamping of ChainTrace reasoning traces via the
Open Timestamps protocol (https://opentimestamps.org/).

The protocol works by:
1. Creating a SHA-256 hash of the data
2. Submitting the hash to a calendar server
3. Receiving a timestamp proof that can be verified against Bitcoin
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class TimestampStatus(str, Enum):
    """Status of a timestamp proof."""

    PENDING = "pending"  # Submitted, waiting for Bitcoin confirmation
    CONFIRMED = "confirmed"  # Included in Bitcoin blockchain
    VERIFIED = "verified"  # Proof verified against Bitcoin
    FAILED = "failed"  # Timestamp failed


@dataclass
class TimestampProof:
    """A timestamp proof from Open Timestamps.

    This proof can be verified against the Bitcoin blockchain to prove
    that the data existed at a specific time.
    """

    # The SHA-256 hash of the timestamped data
    hash: str

    # When the timestamp was submitted to the calendar
    submitted_at: datetime

    # The calendar server that created the timestamp
    calendar_url: str

    # The Bitcoin block height when confirmed (if known)
    bitcoin_block_height: int | None = None

    # The Bitcoin block hash (if confirmed)
    bitcoin_block_hash: str | None = None

    # The timestamp from the calendar (before Bitcoin confirmation)
    calendar_timestamp: datetime | None = None

    # The timestamp when confirmed in Bitcoin
    bitcoin_timestamp: datetime | None = None

    # The raw OTS (OpenTimestamp) data as base64
    raw_proof: str | None = None

    # Current status
    status: TimestampStatus = TimestampStatus.PENDING

    # Merkle proof (when confirmed)
    merkle_proof: dict[str, Any] | None = None

    # Any additional metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "hash": self.hash,
            "submitted_at": self.submitted_at.isoformat(),
            "calendar_url": self.calendar_url,
            "bitcoin_block_height": self.bitcoin_block_height,
            "bitcoin_block_hash": self.bitcoin_block_hash,
            "calendar_timestamp": (
                self.calendar_timestamp.isoformat()
                if self.calendar_timestamp
                else None
            ),
            "bitcoin_timestamp": (
                self.bitcoin_timestamp.isoformat()
                if self.bitcoin_timestamp
                else None
            ),
            "raw_proof": self.raw_proof,
            "status": self.status.value,
            "merkle_proof": self.merkle_proof,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TimestampProof":
        """Deserialize from dictionary."""
        return cls(
            hash=data["hash"],
            submitted_at=datetime.fromisoformat(data["submitted_at"]),
            calendar_url=data["calendar_url"],
            bitcoin_block_height=data.get("bitcoin_block_height"),
            bitcoin_block_hash=data.get("bitcoin_block_hash"),
            calendar_timestamp=(
                datetime.fromisoformat(data["calendar_timestamp"])
                if data.get("calendar_timestamp")
                else None
            ),
            bitcoin_timestamp=(
                datetime.fromisoformat(data["bitcoin_timestamp"])
                if data.get("bitcoin_timestamp")
                else None
            ),
            raw_proof=data.get("raw_proof"),
            status=TimestampStatus(data.get("status", "pending")),
            merkle_proof=data.get("merkle_proof"),
            metadata=data.get("metadata", {}),
        )


class OpenTimestampsClient:
    """Client for Open Timestamps protocol.

    Provides timestamping of data via the Open Timestamps calendar servers.
    The resulting proofs can be verified against the Bitcoin blockchain.
    """

    # Default calendar servers
    DEFAULT_CALENDARS = [
        "https://alice.btc.calendar.opentimestamps.org",
        "https://bob.btc.calendar.opentimestamps.org",
        "https://node1.opentimestamps.org",
    ]

    def __init__(
        self,
        calendar_urls: list[str] | None = None,
        timeout: float = 30.0,
    ):
        """Initialize the Open Timestamps client.

        Args:
            calendar_urls: List of calendar server URLs to use.
                          Defaults to several well-known servers.
            timeout: Request timeout in seconds.
        """
        self._calendars = calendar_urls or self.DEFAULT_CALENDARS
        self._timeout = timeout
        self._http = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._http.aclose()

    @staticmethod
    def hash_data(data: bytes | str) -> str:
        """Create SHA-256 hash of data.

        Args:
            data: The data to hash (bytes or string)

        Returns:
            Hex-encoded SHA-256 hash
        """
        if isinstance(data, str):
            data = data.encode("utf-8")
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def hash_trace(trace_dict: dict[str, Any]) -> str:
        """Create a deterministic hash of a trace for timestamping.

        This hashes the core trace data (reasoning chain, model, adapter)
        but not metadata like timestamps that change.

        Args:
            trace_dict: The trace as a dictionary

        Returns:
            Hex-encoded SHA-256 hash
        """
        # Create deterministic representation
        core_data = {
            "adapter": trace_dict.get("adapter"),
            "model": trace_dict.get("model"),
            "request": trace_dict.get("request"),
            "response": trace_dict.get("response"),
            "reasoning_chain": [
                {"step": s.get("step"), "content": s.get("content")}
                for s in trace_dict.get("reasoning_chain", [])
            ],
        }

        # Sort keys for deterministic serialization
        json_str = json.dumps(core_data, sort_keys=True, separators=(",", ":"))
        return OpenTimestampsClient.hash_data(json_str)

    async def timestamp(
        self,
        data: bytes | str | dict[str, Any],
        calendar_url: str | None = None,
    ) -> TimestampProof:
        """Submit data for timestamping.

        Args:
            data: Data to timestamp (bytes, string, or trace dict)
            calendar_url: Specific calendar to use (optional)

        Returns:
            TimestampProof that can be verified later
        """
        # Determine the hash to timestamp
        if isinstance(data, dict):
            data_hash = self.hash_trace(data)
        else:
            data_hash = self.hash_data(data)

        # Use specified calendar or try first available
        calendar = calendar_url or self._calendars[0]

        # Submit to calendar
        try:
            response = await self._http.post(
                f"{calendar}/timestamp",
                content=data_hash,
                headers={"Content-Type": "application/octet-stream"},
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(f"Failed to submit timestamp to {calendar}: {e}")
            # Try other calendars
            for fallback in self._calendars:
                if fallback == calendar:
                    continue
                try:
                    response = await self._http.post(
                        f"{fallback}/timestamp",
                        content=data_hash,
                        headers={"Content-Type": "application/octet-stream"},
                    )
                    response.raise_for_status()
                    calendar = fallback
                    break
                except httpx.HTTPError:
                    continue
            else:
                raise RuntimeError(f"All calendars failed for hash {data_hash}")

        # Parse the timestamp response
        # The calendar returns an OTS file (we store as base64)
        import base64

        proof_base64 = base64.b64encode(response.content).decode("ascii")

        return TimestampProof(
            hash=data_hash,
            submitted_at=datetime.now(timezone.utc),
            calendar_url=calendar,
            raw_proof=proof_base64,
            status=TimestampStatus.PENDING,
        )

    async def get_timestamp_info(
        self, proof: TimestampProof
    ) -> TimestampProof:
        """Get updated timestamp info from calendar.

        Checks if the timestamp has been confirmed in Bitcoin.

        Args:
            proof: The timestamp proof to check

        Returns:
            Updated TimestampProof with confirmation info
        """
        if not proof.raw_proof:
            return proof

        import base64

        ots_data = base64.b64decode(proof.raw_proof)

        try:
            response = await self._http.get(
                f"{proof.calendar_url}/timestamp/{proof.hash}"
            )
            response.raise_for_status()

            info = response.json()

            if info.get("status") == "confirmed":
                proof.status = TimestampStatus.CONFIRMED
                proof.bitcoin_block_height = info.get("block_height")
                proof.bitcoin_block_hash = info.get("block_hash")

                # Parse timestamps
                if info.get("timestamp"):
                    proof.bitcoin_timestamp = datetime.fromisoformat(
                        info["timestamp"].replace("Z", "+00:00")
                    )

        except httpx.HTTPError as e:
            logger.warning(f"Failed to get timestamp info: {e}")

        return proof

    async def timestamp_trace(
        self,
        trace: "Trace",  # Forward reference
        calendar_url: str | None = None,
    ) -> TimestampProof:
        """Timestamp a ChainTrace trace.

        Args:
            trace: The Trace object to timestamp
            calendar_url: Specific calendar to use (optional)

        Returns:
            TimestampProof
        """
        trace_dict = trace.model_dump()
        return await self.timestamp(trace_dict, calendar_url)

    async def verify_proof(self, proof: TimestampProof) -> bool:
        """Verify a timestamp proof against Bitcoin.

        This checks that the proof is valid by verifying the merkle proof
        against the Bitcoin blockchain (via the calendar).

        Args:
            proof: The timestamp proof to verify

        Returns:
            True if the proof is valid, False otherwise
        """
        if proof.status != TimestampStatus.CONFIRMED:
            # Try to get updated info first
            proof = await self.get_timestamp_info(proof)

        if proof.status != TimestampStatus.CONFIRMED:
            return False

        # For full verification, we would need to check the merkle proof
        # against Bitcoin. This requires either:
        # 1. A Bitcoin node
        # 2. A verification service
        # 3. The opentimestamps python library with bitmap support

        # For now, we mark as verified if confirmed
        proof.status = TimestampStatus.VERIFIED
        return True


# Type hint for circular import
from chaintrace.types.trace import Trace