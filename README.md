# ChainTrace

Modular AI Chain-of-Thought Tracer - capture, store, analyze, and visualize reasoning traces from any AI model.

## Features

- **Multi-provider support**: OpenAI, Anthropic, Claude Code, Ollama, DeepSeek
- **Three capture modes**: API proxy, SDK injection, log parsing
- **Multiple storage backends**: SQLite, File, PostgreSQL
- **Built-in analyzers**: Token counts, step analysis, latency metrics
- **CLI-first design**: Rich terminal output with intuitive commands
- **Extensible**: Registry pattern for adapters, backends, and analyzers

## Installation

```bash
pip install chaintrace
```

## Quick Start

```bash
# Initialize config
chaintrace init

# Capture a trace
chaintrace capture request.json response.json

# List traces
chaintrace list-traces

# Analyze a trace
chaintrace analyze <trace-id>

# View stats
chaintrace stats
```

## License

MIT License - see LICENSE file for details.