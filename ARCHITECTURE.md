# ChainTrace Architecture Design Document

**Version:** 1.0  
**Date:** 2025-05-24  
**Status:** Design Proposal  

---

## 1. Design Philosophy

### 1.1 Core Principles

| Principle | Description |
|-----------|-------------|
| **Modularity First** | Every component is pluggable — adapters, backends, analyzers |
| **Local-First** | Data stays local by default; cloud is optional |
| **Minimal Dependencies** | Core has ~15 direct dependencies; features isolated in extras |
| **Type-Safe** | Full type hints, pydantic for validation, mypy for checking |
| **Testable** | Dependency injection, interfaces over implementations |

### 1.2 Design Goals

1. **CLI should feel like a polished product** — rich output, helpful errors, intuitive commands
2. **Adapter framework should make adding new models trivial** — ~50 lines of code per adapter
3. **Storage backends should be swappable without code changes** — same interface, different implementations
4. **Analysis pipeline should be composable** — chain analyzers or run in parallel

---

## 2. Project Structure

```
chaintrace/
├── src/
│   └── chaintrace/
│       ├── __init__.py              # Package entry, version
│       ├── __main__.py              # python -m chaintrace
│       │
│       ├── core/                    # Core engine
│       │   ├── __init__.py
│       │   ├── config.py            # Configuration management
│       │   ├── engine.py            # Main orchestration
│       │   ├── exceptions.py        # Custom exceptions
│       │   ├── events.py            # Event system
│       │   └── context.py           # Trace context management
│       │
│       ├── capture/                 # Capture methods
│       │   ├── __init__.py
│       │   ├── base.py              # Base capture interface
│       │   ├── proxy.py             # API proxy mode
│       │   ├── sdk.py               # SDK injection mode
│       │   └── log_parser.py        # Log parsing mode
│       │
│       ├── storage/                 # Storage backends
│       │   ├── __init__.py
│       │   ├── base.py              # Backend interface
│       │   ├── registry.py          # Backend registry
│       │   ├── sqlite.py            # SQLite backend
│       │   ├── file.py              # File (JSONL) backend
│       │   └── postgresql.py        # PostgreSQL backend
│       │
│       ├── adapters/                # Model adapters
│       │   ├── __init__.py
│       │   ├── base.py              # Base adapter interface
│       │   ├── registry.py          # Adapter registry
│       │   └── builtin/             # Built-in adapters
│       │       ├── __init__.py
│       │       ├── openai.py
│       │       ├── anthropic.py
│       │       ├── codex.py
│       │       ├── ollama.py
│       │       └── gemini.py
│       │
│       ├── analysis/                # Analysis pipeline
│       │   ├── __init__.py
│       │   ├── base.py              # Analyzer interface
│       │   ├── pipeline.py          # Analysis pipeline
│       │   ├── extractors/          # CoT extractors
│       │   │   ├── __init__.py
│       │   │   ├── base.py
│       │   │   ├── xml.py
│       │   │   ├── json.py
│       │   │   └── markdown.py
│       │   └── analyzers/           # Built-in analyzers
│       │       ├── __init__.py
│       │       ├── token_count.py
│       │       ├── step_count.py
│       │       └── latency.py
│       │
│       ├── cli/                     # CLI interface
│       │   ├── __init__.py
│       │   ├── app.py               # Click app root
│       │   ├── commands/            # Command modules
│       │   │   ├── __init__.py
│       │   │   ├── init.py
│       │   │   ├── capture.py
│       │   │   ├── list.py
│       │   │   ├── view.py
│       │   │   ├── analyze.py
│       │   │   ├── export.py
│       │   │   ├── adapter.py
│       │   │   └── backend.py
│       │   ├── output/              # Output formatters
│       │   │   ├── __init__.py
│       │   │   ├── console.py
│       │   │   ├── json.py
│       │   │   └── table.py
│       │   └── helpers.py           # CLI utilities
│       │
│       └── types/                   # Shared types
│           ├── __init__.py
│           ├── trace.py             # Trace data model
│           ├── request.py           # Request types
│           ├── response.py          # Response types
│           └── config.py            # Config types
│
├── tests/
│   ├── unit/
│   │   ├── core/
│   │   ├── storage/
│   │   ├── adapters/
│   │   └── analysis/
│   ├── integration/
│   │   ├── test_capture.py
│   │   └── test_storage.py
│   └── fixtures/
│       ├── traces/
│       └── configs/
│
├── examples/
│   ├── basic_capture.py
│   ├── custom_adapter.py
│   └── custom_analyzer.py
│
├── docs/
│   ├── architecture.md
│   ├── adapter-guide.md
│   ├── backend-guide.md
│   └── analyzer-guide.md
│
├── pyproject.toml
├── uv.lock
├── README.md
├── LICENSE (MIT)
├── BRS.md
├── SRS.md
└── SBoM.md
```

---

## 3. CLI Design

### 3.1 Command Structure

```
chaintrace [GLOBAL OPTIONS] <command> [command options] [arguments]

GLOBAL OPTIONS:
  --config PATH           Config file path (default: ./chaintrace.yaml)
  --verbose, -v           Enable verbose output
  --quiet, -q             Suppress non-essential output
  --output FORMAT         Output format: table, json, simple (default: table)
```

### 3.2 Command Hierarchy

```
chaintrace
├── init [options]              Initialize new project
├── capture
│   ├── start [options]         Start capture (proxy mode)
│   ├── stop                    Stop capture
│   ├── status                  Show capture status
│   └── test                    Test capture configuration
├── trace
│   ├── list [options]          List traces
│   ├── view <id> [options]     View trace details
│   ├── delete <id>             Delete trace
│   └── export [options]        Export traces
├── analyze
│   ├── run <id> [options]      Run analysis on trace
│   ├── pipeline [options]      Run full pipeline
│   └── list                    List available analyzers
├── adapter
│   ├── list                    List installed adapters
│   ├── info <name>             Show adapter details
│   └── install <name>          Install adapter
├── backend
│   ├── list                    List available backends
│   ├── info <name>             Show backend details
│   ├── test                    Test backend connection
│   └── migrate <from> <to>     Migrate between backends
├── config
│   ├── show                    Show current config
│   ├── edit                    Edit config file
│   └── validate                Validate config
└── server
    ├── start [options]         Start web UI / API server
    └── stop                    Stop server
```

### 3.3 Output Design

**Rich Terminal Output:**
- Colored status indicators (✅ green, ❌ red, ⚠️ yellow)
- Tables with alignment and borders
- Progress indicators for long operations
- Syntax-highlighted JSON/code blocks

**Example Output:**
```
$ chaintrace trace list

  ID                                   Model        Created            Steps    Tokens
  ────────────────────────────────────────────────────────────────────────────────
  ct_a1b2c3d4e5f6                     gpt-4o       2025-05-24 14:32    7        2,341
  ct_b2c3d4e5f6g7                     claude-3     2025-05-24 14:28    12       4,892
  ct_c3d4e5f6g7h8                     ollama       2025-05-24 14:15    4        892

  Showing 3 of 247 traces. Use --page 2 for more.
```

### 3.4 Error Handling

- All errors include exit code and helpful message
- `--verbose` shows full traceback
- Config errors point to exact line/setting
- Network errors include retry suggestions

---

## 4. Core Engine Architecture

### 4.1 Engine Components

```python
# Pseudo-structure of core engine

class ChainTraceEngine:
    """Main orchestration engine"""
    
    def __init__(self, config: ChainTraceConfig):
        self.config = config
        self.storage = StorageRegistry.get(config.storage.backend)
        self.adapters = AdapterRegistry()
        self.analyzer_pipeline = AnalysisPipeline()
        self.event_bus = EventBus()
    
    async def capture(
        self,
        adapter_name: str,
        request: Request,
        capture_method: CaptureMethod
    ) -> Trace:
        """Main capture flow"""
        pass
    
    async def store(self, trace: Trace) -> None:
        """Store trace to backend"""
        pass
    
    async def analyze(self, trace: Trace, analyzers: list[str]) -> AnalysisResult:
        """Run analysis pipeline"""
        pass
    
    async def query(self, filters: QueryFilters) -> list[Trace]:
        """Query traces"""
        pass
```

### 4.2 Configuration System

```python
from pydantic import BaseModel, Field
from typing import Literal

class CaptureConfig(BaseModel):
    mode: Literal["proxy", "sdk", "log"] = "sdk"
    adapter: str = "openai"
    proxy: ProxyConfig | None = None
    log: LogConfig | None = None

class StorageConfig(BaseModel):
    backend: str = "sqlite"
    sqlite: SqliteConfig | None = None
    file: FileConfig | None = None
    postgresql: PostgresConfig | None = None

class ChainTraceConfig(BaseModel):
    version: str = "1.0"
    capture: CaptureConfig
    storage: StorageConfig
    analysis: AnalysisConfig
    adapters: dict[str, dict]
    
    # Environment variable support
    class Config:
        env_prefix = "CHAINTRACE_"
```

### 4.3 Event System

```python
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class EventType(Enum):
    CAPTURE_START = "capture_start"
    CAPTURE_COMPLETE = "capture_complete"
    TRACE_STORED = "trace_stored"
    ANALYSIS_COMPLETE = "analysis_complete"
    ERROR = "error"

@dataclass
class Event:
    type: EventType
    timestamp: datetime
    data: dict
    trace_id: str | None = None

class EventBus:
    """Simple pub/sub for internal events"""
    
    def subscribe(self, event_type: EventType, handler: Callable):
        pass
    
    def publish(self, event: Event):
        pass
```

---

## 5. Adapter Framework

### 5.1 Adapter Interface

```python
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar
from pydantic import BaseModel

T = TypeVar('T')

class RequestPayload(BaseModel):
    """Model-agnostic request representation"""
    model: str
    messages: list[dict]
    parameters: dict[str, Any]

class ResponsePayload(BaseModel):
    """Model-agnostic response representation"""
    content: str
    reasoning: str | None = None  # CoT content if available
    usage: dict[str, int]
    model: str
    raw: dict  # Original response for adapter-specific fields

class BaseAdapter(ABC):
    """All adapters must implement this interface"""
    
    name: str  # e.g., "openai", "claude"
    version: str
    
    # Configuration
    @classmethod
    def get_config_schema(cls) -> dict:
        """Return pydantic schema for config validation"""
        pass
    
    # Capture methods
    async def capture_request(self, payload: RequestPayload) -> RequestPayload:
        """Transform/intercept request before sending"""
        return payload
    
    async def capture_response(self, payload: ResponsePayload) -> ResponsePayload:
        """Transform/intercept response after receiving"""
        return payload
    
    # CoT extraction - the core adapter responsibility
    def extract_reasoning(self, response: ResponsePayload) -> list[ReasoningStep]:
        """Extract chain-of-thought from response"""
        pass
    
    # Compatibility
    def supports_streaming(self) -> bool:
        return False
    
    def supports_function_calling(self) -> bool:
        return False
    
    # Metadata
    def get_model_options(self) -> list[str]:
        """List supported models"""
        pass
```

### 5.2 Adapter Registry

```python
class AdapterRegistry:
    """Discovers and manages adapters"""
    
    def __init__(self):
        self._adapters: dict[str, type[BaseAdapter]] = {}
        self._instances: dict[str, BaseAdapter] = {}
    
    def register(self, adapter_class: type[BaseAdapter]):
        """Register an adapter class"""
        self._adapters[adapter_class.name] = adapter_class
    
    def get(self, name: str, config: dict | None = None) -> BaseAdapter:
        """Get adapter instance (singleton per config)"""
        pass
    
    def list_available(self) -> list[dict]:
        """List all registered adapters"""
        pass
    
    def discover_builtins(self):
        """Auto-discover built-in adapters"""
        pass
    
    def discover_plugins(self, plugin_dir: str):
        """Discover third-party adapters"""
        pass
```

### 5.3 Example Adapter (OpenAI)

```python
class OpenAIAdapter(BaseAdapter):
    """OpenAI adapter - ~80 lines of code"""
    
    name = "openai"
    version = "1.0.0"
    
    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "api_key": {"type": "string"},
                "organization": {"type": "string"},
                "base_url": {"type": "string"},
            },
            "required": ["api_key"]
        }
    
    def extract_reasoning(
        self, 
        response: ResponsePayload
    ) -> list[ReasoningStep]:
        """Extract reasoning from o1/o3 models"""
        steps = []
        
        # o1/o3 models put reasoning in a specific field
        if response.reasoning:
            for i, chunk in enumerate(response.reasoning.split("\n\n")):
                steps.append(ReasoningStep(
                    step=i + 1,
                    content=chunk.strip(),
                    timestamp=datetime.utcnow()
                ))
        
        # Also check for XML-style reasoning
        if not steps:
            steps = self._extract_xml_reasoning(response.content)
        
        return steps
    
    def _extract_xml_reasoning(self, content: str) -> list[ReasoningStep]:
        """Extract <reasoning> tags"""
        # Implementation
        pass
    
    def supports_streaming(self) -> bool:
        return True
    
    def get_model_options(self) -> list[str]:
        return ["gpt-4o", "gpt-4o-mini", "o1", "o1-mini", "o3", "o3-mini"]
```

### 5.4 Adding a New Adapter

To add a new adapter (e.g., Hugging Face):

1. Create `src/chaintrace/adapters/builtin/huggingface.py`
2. Implement `BaseAdapter` interface (~50-100 lines)
3. Register in `src/chaintrace/adapters/builtin/__init__.py`

No other changes needed — registry auto-discovers.

---

## 6. Storage Backend Framework

### 6.1 Backend Interface

```python
from abc import ABC, abstractmethod
from typing import AsyncIterator
from chaintrace.types import Trace, QueryFilters, TraceStats

class BaseStorageBackend(ABC):
    """All storage backends must implement this"""
    
    name: str
    
    @abstractmethod
    async def initialize(self, config: dict) -> None:
        """Initialize backend (create tables, connections, etc.)"""
        pass
    
    @abstractmethod
    async def store(self, trace: Trace) -> None:
        """Store a single trace"""
        pass
    
    @abstractmethod
    async def store_batch(self, traces: list[Trace]) -> None:
        """Store multiple traces (for efficiency)"""
        pass
    
    @abstractmethod
    async def get(self, trace_id: str) -> Trace | None:
        """Retrieve a trace by ID"""
        pass
    
    @abstractmethod
    async def query(
        self,
        filters: QueryFilters,
        limit: int = 100,
        offset: int = 0
    ) -> list[Trace]:
        """Query traces with filters"""
        pass
    
    @abstractmethod
    async def delete(self, trace_id: str) -> bool:
        """Delete a trace"""
        pass
    
    @abstractmethod
    async def stats(self) -> TraceStats:
        """Get storage statistics"""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Clean up connections"""
        pass
    
    async def stream(self, filters: QueryFilters) -> AsyncIterator[Trace]:
        """Stream traces (for large exports)"""
        pass
    
    async def migrate_from(self, other: BaseStorageBackend) -> int:
        """Migrate from another backend (returns count)"""
        pass
```

### 6.2 Backend Registry

```python
class StorageBackendRegistry:
    """Discovers and manages storage backends"""
    
    def __init__(self):
        self._backends: dict[str, type[BaseStorageBackend]] = {}
    
    def register(self, backend_class: type[BaseStorageBackend]):
        self._backends[backend_class.name] = backend_class
    
    def get(self, name: str, config: dict) -> BaseStorageBackend:
        backend_class = self._backends.get(name)
        if not backend_class:
            raise ValueError(f"Unknown backend: {name}")
        return backend_class(config)
    
    def list_available(self) -> list[str]:
        return list(self._backends.keys())
```

### 6.3 SQLite Backend (Default)

```python
class SqliteBackend(BaseStorageBackend):
    name = "sqlite"
    
    async def initialize(self, config: dict) -> None:
        path = config.get("path", "./chaintrace.db")
        self.conn = await aiosqlite.connect(path)
        await self._create_tables()
    
    async def _create_tables(self):
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS traces (
                id TEXT PRIMARY KEY,
                adapter TEXT NOT NULL,
                model TEXT NOT NULL,
                request_json TEXT NOT NULL,
                response_json TEXT NOT NULL,
                reasoning_chain_json TEXT,
                metadata_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_created_at ON traces(created_at)
        """)
        await self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_adapter_model ON traces(adapter, model)
        """)
        await self.conn.commit()
```

---

## 7. Analysis Pipeline

### 7.1 Analyzer Interface

```python
from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import Any

class AnalysisResult(BaseModel):
    analyzer: str
    score: float | None = None
    findings: list[dict] = []
    metadata: dict[str, Any] = {}

class BaseAnalyzer(ABC):
    """Base class for all analyzers"""
    
    name: str
    version: str
    description: str
    
    @abstractmethod
    async def analyze(self, trace: Trace) -> AnalysisResult:
        """Run analysis on a trace"""
        pass
    
    @classmethod
    def get_config_schema(cls) -> dict | None:
        """Optional configuration"""
        return None
```

### 7.2 Pipeline Composition

```python
class AnalysisPipeline:
    """Composable analysis pipeline"""
    
    def __init__(self, analyzers: list[BaseAnalyzer] | None = None):
        self.analyzers = analyzers or []
    
    def add(self, analyzer: BaseAnalyzer) -> "AnalysisPipeline":
        """Add analyzer (chainable)"""
        self.analyzers.append(analyzer)
        return self
    
    def remove(self, name: str) -> "AnalysisPipeline":
        """Remove analyzer by name"""
        self.analyzers = [a for a in self.analyzers if a.name != name]
        return self
    
    async def run(
        self, 
        trace: Trace, 
        analyzer_names: list[str] | None = None
    ) -> list[AnalysisResult]:
        """Run pipeline on trace"""
        results = []
        for analyzer in self.analyzers:
            if analyzer_names and analyzer.name not in analyzer_names:
                continue
            result = await analyzer.analyze(trace)
            results.append(result)
        return results
    
    async def run_parallel(
        self, 
        trace: Trace,
        analyzer_names: list[str] | None = None
    ) -> list[AnalysisResult]:
        """Run analyzers in parallel"""
        # Use asyncio.gather for parallel execution
        pass
```

### 7.3 Built-in Analyzers

| Analyzer | Description | Output |
|----------|-------------|--------|
| `token_count` | Count tokens used | Usage breakdown |
| `step_count` | Count reasoning steps | Step count per trace |
| `latency` | Measure request latency | Latency in ms |
| `reasoning_quality` | (Premium) Score reasoning quality | Quality score 0-100 |
| `error_detection` | (Premium) Detect reasoning errors | Error list |
| `similarity` | (Premium) Compare to similar traces | Similarity score |

---

## 8. Capture Methods

### 8.1 SDK Injection Mode

```python
# User usage:
from chaintrace.sdk import trace

# Simple decorator usage
@trace(adapter="openai", metadata={"project": "my-app"})
async def call_llm():
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Hello"}]
    )
    return response

# Context manager usage
async def main():
    async with trace(adapter="claude", tags=["test"]) as ctx:
        result = await client.messages.create(...)
        # Trace automatically captured
        trace_id = ctx.trace_id
```

### 8.2 Proxy Mode

```python
# Start proxy
$ chaintrace capture start --adapter openai --port 8080

# Configure client to use proxy
export HTTP_PROXY=http://localhost:8080
export OPENAI_API_KEY=sk-...

# All requests automatically traced
```

### 8.3 Log Parser Mode

```python
# Watch directory for new logs
$ chaintrace capture start --mode log --pattern "*.jsonl" --path ./logs

# Or one-time parse
$ chaintrace capture parse --path ./old_logs/*.jsonl
```

---

## 9. Extension Points

### 9.1 Custom Adapter

```python
# examples/custom_adapter.py
from chaintrace.adapters.base import BaseAdapter, RequestPayload, ResponsePayload
from chaintrace.adapters import registry

class MyCustomAdapter(BaseAdapter):
    name = "my_custom"
    version = "1.0.0"
    
    def extract_reasoning(self, response):
        # Custom logic
        pass

# Register (can be done in __init__.py or dynamically)
registry.register(MyCustomAdapter)
```

### 9.2 Custom Analyzer

```python
# examples/custom_analyzer.py
from chaintrace.analysis.base import BaseAnalyzer, AnalysisResult, Trace

class CustomAnalyzer(BaseAnalyzer):
    name = "custom_analyzer"
    description = "My custom analysis"
    
    async def analyze(self, trace: Trace) -> AnalysisResult:
        # Custom logic
        return AnalysisResult(
            analyzer=self.name,
            score=0.85,
            findings=[...],
            metadata={}
        )
```

### 9.3 Custom Backend

```python
# examples/custom_backend.py
from chaintrace.storage.base import BaseStorageBackend

class CustomBackend(BaseStorageBackend):
    name = "custom"
    
    async def initialize(self, config):
        # Custom initialization
        pass
    
    # ... implement all abstract methods
```

---

## 10. Package Distribution

### 10.1 Core Package (MIT)

```
chaintrace/
├── Core CLI
├── SDK injection
├── SQLite + File backends
├── Basic analyzers (token_count, step_count, latency)
└── 5 built-in adapters (OpenAI, Claude, Codex, Ollama, Gemini)
```

### 10.2 Premium Packages (Proprietary)

```
chaintrace-premium          # $99/year
├── Advanced analyzers
│   ├── reasoning_quality
│   ├── error_detection
│   ├── similarity
│   └── comparison
└── Extended support

chaintrace-web              # $199/year
├── Web UI dashboard
├── Visualization
└── Trace comparison UI

chaintrace-api              # $499/year
├── REST API
├── API key auth
├── Rate limiting
└── Webhook support
```

---

## 11. Testing Strategy

### 11.1 Test Organization

```
tests/
├── unit/
│   ├── test_adapters/       # Test each adapter
│   ├── test_storage/        # Test each backend
│   ├── test_analysis/       # Test analyzers
│   └── test_core/           # Test engine
├── integration/
│   ├── test_capture_proxy.py
│   ├── test_capture_sdk.py
│   ├── test_capture_log.py
│   └── test_storage_migration.py
└── fixtures/
    ├── traces/              # Sample trace JSON
    └── configs/             # Sample config YAML
```

### 11.2 Testing Principles

- **Mock external APIs** — Don't hit real LLM APIs in tests
- **Use fixtures** — Pre-recorded traces for repeatable tests
- **Test interface contracts** — Base classes have test suites
- **Property-based testing** — Use hypothesis for edge cases

---

## 12. CI/CD Pipeline

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv pip install --dev
      - run: uv run pytest
      - run: uv run mypy src/chaintrace
      - run: uv run ruff check src/

  publish:
    needs: test
    if: startsWith(github.ref, 'refs/tags/')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv build
      - uses: pypa/gh-action-pypi-publish@release
```

---

## 13. Summary

This architecture provides:

| Goal | Solution |
|------|----------|
| Polished CLI | Click + Rich, hierarchical commands, colored output |
| Solid adapter framework | ~50 line adapter interface, auto-discovery, registry pattern |
| Storage flexibility | Pluggable backends, same interface, migration support |
| Analysis extensibility | Composable pipeline, async analyzers, premium tier |
| Testability | Interfaces over implementations, fixtures, property testing |
| Maintainability | Type hints, pydantic validation, mypy checking, ruff linting |

The structure allows adding new adapters, backends, and analyzers without touching core code — true modularity.

---

**Next Steps:**
1. Review this design
2. Initialize Python project with pyproject.toml
3. Set up project structure
4. Implement core interfaces
5. Build first adapter (OpenAI)
6. Test capture flow end-to-end

**Document Status:** Ready for review/approval