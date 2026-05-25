# ChainTrace

**Modular AI Chain-of-Thought Tracer** — capture, store, analyze, and visualize reasoning traces from any AI model.

ChainTrace lets you record and inspect the reasoning processes of LLMs, with support for multiple providers, storage backends, and optional Bitcoin timestamping for cryptographic proof of when traces were created.

---

## Features

- **Multi-Provider Support** — OpenAI, Anthropic, Claude Code, Ollama, DeepSeek, Gemini
- **Three Capture Modes** — API proxy, SDK injection, log parsing
- **Multiple Storage Backends** — SQLite (default), File (JSONL), PostgreSQL
- **Built-in Analyzers** — Token counts, step analysis, latency metrics
- **Bitcoin Timestamping** — Cryptographic proof of trace existence via Open Timestamps
- **Rich CLI** — Colorized terminal output, tree visualization, diff comparison
- **Extensible** — Registry pattern for custom adapters, backends, and analyzers

---

## Installation

```bash
pip install chaintrace
```

Or install with extras:

```bash
pip install chaintrace[postgresql]  # PostgreSQL support
pip install chaintrace[bitcoin]     # Bitcoin timestamping
pip install chaintrace[all]         # All extras
```

---

## Quick Start

```bash
# Initialize config (creates .chaintrace.yaml in current directory)
chaintrace init

# Capture a trace from request/response JSON files
chaintrace capture request.json response.json

# List stored traces
chaintrace list-traces

# Visualize a trace as a color tree
chaintrace visualize <trace-id>

# Analyze a trace
chaintrace analyze <trace-id>

# View storage statistics
chaintrace stats
```

---

## Configuration

ChainTrace uses a YAML configuration file (default: `.chaintrace.yaml`). Initialize with `chaintrace init`.

### Full Configuration Reference

```yaml
version: '1.0'

# Capture settings
capture:
  mode: sdk              # proxy | sdk | log_parser
  adapter: openai        # auto-detect from payload if omitted

# Storage backend
storage:
  backend: sqlite        # sqlite | file | postgresql
  sqlite:
    path: ./chaintrace.db
  file:
    path: ./traces/      # Directory for JSONL files
  postgresql:
    host: localhost
    port: 5432
    database: chaintrace
    user: postgres
    password: ""

# Analysis pipeline
analysis:
  analyzers:
    - token_count        # Count input/output tokens
    - step_count         # Count reasoning steps
    - latency            # Measure request latency

# Bitcoin timestamping (optional, off by default)
attestation:
  enabled: false
  default_calendar: null # Open Timestamps calendar URL

# Custom adapters
adapters: {}
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CHAINTRACE_CONFIG` | Path to config file | `.chaintrace.yaml` |
| `CHAINTRACE_STORAGE_BACKEND` | Override storage backend | (from config) |
| `CHAINTRACE_ATTESTATION_ENABLED` | Enable Bitcoin timestamping | `false` |

---

## CLI Commands

### `chaintrace init`

Initialize a new ChainTrace configuration.

```bash
chaintrace init                    # Creates .chaintrace.yaml
chaintrace init --path /path/to/config.yaml
```

### `chaintrace capture`

Capture a trace from request/response JSON files.

```bash
chaintrace capture request.json response.json
chaintrace capture req.json res.json --adapter openai
chaintrace capture req.json res.json -o trace-id.txt  # Save ID to file
```

**Request/Response Format:**

```json
// request.json
{
  "model": "gpt-4",
  "messages": [{"role": "user", "content": "Explain gravity"}],
  "temperature": 0.7
}

// response.json
{
  "model": "gpt-4",
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "Gravity is...",
      "reasoning": "Let me think about this step by step..."
    }
  }],
  "usage": {"prompt_tokens": 10, "completion_tokens": 50}
}
```

### `chaintrace list-traces`

List stored traces with optional filters.

```bash
chaintrace list-traces
chaintrace list-traces --adapter openai
chaintrace list-traces --model gpt-4
chaintrace list-traces --limit 10
```

### `chaintrace visualize`

Render a trace as a colorized tree in the terminal.

```bash
chaintrace visualize <trace-id>
chaintrace visualize <trace-id> --full      # Show full content (no truncation)
chaintrace visualize <trace-id> --width 120 # Custom wrap width
chaintrace visualize <trace-id> --metadata  # Include request metadata
```

**Output includes:**
- Trace ID and Bitcoin timestamp badge (if timestamped)
- Info section: adapter, model, created time, step count
- Metadata section (with `--metadata`): full request payload
- Reasoning Chain: each step as a tree node with timestamp

### `chaintrace analyze`

Run analysis pipelines on a trace.

```bash
chaintrace analyze <trace-id>
chaintrace analyze <trace-id> --analyzers token_count,latency
```

**Built-in analyzers:**
- `token_count` — Input/output/token breakdown
- `step_count` — Number of reasoning steps detected
- `latency` — Request duration in seconds

### `chaintrace export`

Export a trace to various formats.

```bash
chaintrace export <trace-id>
chaintrace export <trace-id> --format json
chaintrace export <trace-id> --format markdown
chaintrace export <trace-id> --format csv
chaintrace export <trace-id> -o trace.json  # Write to file
```

**Formats:**
- `json` — Full trace with all metadata
- `markdown` — Human-readable document
- `csv` — Flat table (steps as rows)

### `chaintrace diff`

Compare two traces side-by-side.

```bash
chaintrace diff <trace-id-1> <trace-id-2>
chaintrace diff <trace-id-1> <trace-id-2> --steps  # Step-by-step content diff
```

Shows differences in:
- Model usage
- Token counts
- Step counts
- Latency
- Content (with `--steps`)

### `chaintrace scan`

Bulk-import traces from JSONL log files or directories.

```bash
chaintrace scan logs.jsonl
chaintrace scan ./logs/
chaintrace scan ./logs/ --recursive           # Include subdirectories
chaintrace scan ./logs/ --pattern "*.json"    # Custom glob pattern
chaintrace scan ./logs/ --adapter openai      # Force adapter
chaintrace scan ./logs/ --dry-run             # Parse without storing
```

**Input formats:**

```jsonl
# Wrapped format
{"request": {...}, "response": {...}, "adapter": "openai"}

# Flat format (auto-detected)
{"model": "gpt-4", "choices": [...], "_request": {...}}
```

### `chaintrace stats`

Show storage statistics.

```bash
chaintrace stats
```

Output includes:
- Total trace count
- Storage backend and path
- Traces by adapter
- Traces by model
- Timestamp coverage

### `chaintrace timestamp`

Timestamp a trace on Bitcoin via Open Timestamps.

```bash
chaintrace timestamp <trace-id>
chaintrace timestamp <trace-id> --calendar https://alice.btc.calendar.opentimestamps.org
```

**Prerequisites:**
```bash
pip install chaintrace[bitcoin]
```

### `chaintrace timestamp-all`

Timestamp all untimestamped traces.

```bash
chaintrace timestamp-all
chaintrace timestamp-all --adapter openai    # Filter by adapter
chaintrace timestamp-all --model gpt-4       # Filter by model
chaintrace timestamp-all --calendar https://alice.btc.calendar.opentimestamps.org
```

### `chaintrace verify`

Verify a trace's Bitcoin timestamp proof.

```bash
chaintrace verify <trace-id>
```

Validates:
- Merkle proof inclusion
- Calendar server response
- Timestamp anchor block

### `chaintrace audit`

Audit traces timestamped before a specific Bitcoin block.

```bash
chaintrace audit --before-block 850000
chaintrace audit --before-block 850000 --adapter openai
```

---

## Capture Modes

### SDK Mode (default)

Inject ChainTrace into your SDK calls:

```python
from chaintrace.capture.sdk import trace_openai
from openai import OpenAI

# Wrap the client
client = trace_openai(OpenAI())
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello"}]
)
# Trace automatically captured
```

### Proxy Mode

Run ChainTrace as a local API proxy:

```bash
chaintrace proxy --port 8080 --target https://api.openai.com/v1
# Set OPENAI_BASE_URL=http://localhost:8080 in your app
```

### Log Parser Mode

Parse existing log files:

```bash
chaintrace scan logs.jsonl --adapter openai
```

---

## Storage Backends

### SQLite (default)

Simple, local, zero-config:

```yaml
storage:
  backend: sqlite
  sqlite:
    path: ./chaintrace.db
```

### File (JSONL)

Human-readable, version-control friendly:

```yaml
storage:
  backend: file
  file:
    path: ./traces/
```

Each trace → one JSONL file.

### PostgreSQL

For production with multiple users:

```yaml
storage:
  backend: postgresql
  postgresql:
    host: localhost
    port: 5432
    database: chaintrace
    user: postgres
    password: ""
```

---

## Bitcoin Timestamping

ChainTrace supports **Open Timestamps** — a free, decentralized timestamping protocol that anchors data into the Bitcoin blockchain.

### How It Works

1. You timestamp a trace → ChainTrace computes a SHA-256 hash
2. Hash submitted to Open Timestamps calendar server
3. Calendar returns a proof file (`.ots`)
4. Anyone can verify the proof → proves the trace existed at that time

### Usage

```bash
# Enable in config (off by default)
echo "attestation:
  enabled: true" >> .chaintrace.yaml

# Timestamp a trace
chaintrace timestamp <trace-id>

# Verify the proof
chaintrace verify <trace-id>

# Batch timestamp
chaintrace timestamp-all
```

### Why Timestamp?

- **Provenance** — Prove when you created a trace
- **Integrity** — Detect any tampering after the fact
- **Audit** — Meet compliance requirements for evidence retention

---

## Extending ChainTrace

### Custom Adapters

Create `my_adapter.py`:

```python
from chaintrace.adapters.base import BaseAdapter
from chaintrace.types import Request, Response

class MyAdapter(BaseAdapter):
    name = "my_adapter"
    
    def extract_request(self, data: dict) -> Request:
        # Parse your format
        return Request(model=data["model"], messages=data["messages"])
    
    def extract_response(self, data: dict) -> Response:
        return Response(
            content=data["completion"],
            reasoning=data.get("thought_process"),
            tokens=data.get("usage", {})
        )
    
    def extract_reasoning(self, response: Response) -> list[str]:
        # How to find CoT in your responses
        return [response.reasoning] if response.reasoning else []
```

Register in config:

```yaml
adapters:
  my_adapter:
    path: ./my_adapter.py
```

### Custom Analyzers

Create `my_analyzer.py`:

```python
from chaintrace.analysis.base import BaseAnalyzer

class MyAnalyzer(BaseAnalyzer):
    name = "my_analyzer"
    
    def analyze(self, trace: Trace) -> dict:
        return {
            "word_count": len(trace.content.split()),
            "has_code": "```" in trace.content
        }
```

Register in config:

```yaml
analysis:
  analyzers:
    - token_count
    - my_analyzer
```

---

## Architecture

```
chaintrace/
├── core/           # Engine, config, events
├── capture/        # proxy, sdk, log_parser modes
├── storage/        # sqlite, file, postgresql backends
├── adapters/       # Model-specific parsers
├── analysis/       # Analyzers and extractors
├── cli/            # Click commands
└── types/          # Pydantic models
```

See `ARCHITECTURE.md` for full design details.

---

## License

MIT License - see LICENSE file for details.