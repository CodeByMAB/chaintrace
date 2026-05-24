"""Custom exceptions for ChainTrace."""


class ChainTraceError(Exception):
    """Base exception for all ChainTrace errors."""

    pass


class ConfigurationError(ChainTraceError):
    """Raised when configuration is invalid or missing."""

    pass


class AdapterError(ChainTraceError):
    """Raised when an adapter encounters an error."""

    pass


class StorageError(ChainTraceError):
    """Raised when a storage backend encounters an error."""

    pass


class AnalysisError(ChainTraceError):
    """Raised when an analyzer encounters an error."""

    pass


class CaptureError(ChainTraceError):
    """Raised when capture encounters an error."""

    pass


class ValidationError(ChainTraceError):
    """Raised when data validation fails."""

    pass


class NotFoundError(ChainTraceError):
    """Raised when a requested resource is not found."""

    pass