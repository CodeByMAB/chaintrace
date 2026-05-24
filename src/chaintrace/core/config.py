"""Configuration management using pydantic."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class ProxyConfig(BaseModel):
    """Configuration for proxy capture mode."""

    host: str = "127.0.0.1"
    port: int = 8181
    ssl: bool = False


class LogConfig(BaseModel):
    """Configuration for log parser capture mode."""

    pattern: str = "*.jsonl"
    path: str = "./logs"
    watch: bool = False
    recursive: bool = False


class CaptureConfig(BaseModel):
    """Configuration for capture settings."""

    mode: Literal["proxy", "sdk", "log"] = "sdk"
    adapter: str = "openai"
    proxy: ProxyConfig | None = None
    log: LogConfig | None = None


class SqliteConfig(BaseModel):
    """Configuration for SQLite storage backend."""

    path: str = "./chaintrace.db"
    pragma: dict[str, Any] = Field(default_factory=dict)


class FileConfig(BaseModel):
    """Configuration for file storage backend."""

    path: str = "./traces"
    format: Literal["jsonl", "json"] = "jsonl"


class PostgresConfig(BaseModel):
    """Configuration for PostgreSQL storage backend."""

    host: str = "localhost"
    port: int = 5432
    database: str = "chaintrace"
    username: str = "postgres"
    password: str | None = None
    pool_size: int = 10


class StorageConfig(BaseModel):
    """Configuration for storage settings."""

    backend: Literal["sqlite", "file", "postgresql"] = "sqlite"
    sqlite: SqliteConfig | None = None
    file: FileConfig | None = None
    postgresql: PostgresConfig | None = None


class AnalysisConfig(BaseModel):
    """Configuration for analysis settings."""

    analyzers: list[str] = Field(default_factory=lambda: ["token_count", "step_count", "latency"])


class ChainTraceConfig(BaseModel):
    """Main configuration for ChainTrace."""

    version: str = "1.0"
    capture: CaptureConfig = Field(default_factory=CaptureConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)
    adapters: dict[str, dict] = Field(default_factory=dict)

    class Config:
        env_prefix = "CHAINTRACE_"
        extra = "forbid"