"""Storage backend registry."""

from typing import Any

from chaintrace.storage.base import BaseStorageBackend
from chaintrace.storage.sqlite import SqliteBackend
from chaintrace.storage.file import FileBackend


class StorageBackendRegistry:
    """Registry for managing storage backends."""

    def __init__(self) -> None:
        self._backends: dict[str, type[BaseStorageBackend]] = {}
        self._instances: dict[str, BaseStorageBackend] = {}
        self._register_builtins()

    def _register_builtins(self) -> None:
        """Register built-in backends."""
        self.register(SqliteBackend)
        self.register(FileBackend)

    def register(self, backend_class: type[BaseStorageBackend]) -> None:
        """Register a storage backend class."""
        self._backends[backend_class.name] = backend_class

    def get(self, name: str, config: dict[str, Any]) -> BaseStorageBackend:
        """Get a storage backend instance by name."""
        if name not in self._backends:
            raise ValueError(f"Unknown storage backend: {name}. Available: {list(self._backends.keys())}")

        # Return cached instance if config matches
        cache_key = f"{name}:{hash(frozenset(config.items()))}"
        if cache_key in self._instances:
            return self._instances[cache_key]

        backend = self._backends[name]()
        self._instances[cache_key] = backend
        return backend

    def list_available(self) -> list[str]:
        """List all registered backend names."""
        return list(self._backends.keys())