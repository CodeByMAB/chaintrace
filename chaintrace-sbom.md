# ChainTrace Software Bill of Materials (SBoM)

**Version:** 1.0  
**Date:** 2025-05-24  
**Project:** ChainTrace  

---

## 1. Overview

This document provides a comprehensive Software Bill of Materials for ChainTrace, listing all dependencies, components, and their associated licenses.

---

## 2. Core Dependencies

### 2.1 Python Runtime

| Component | Version | License | Purpose |
|-----------|---------|---------|---------|
| Python | >=3.10 | PSF | Runtime |

### 2.2 Core Framework

| Component | Version | License | Purpose |
|-----------|---------|---------|---------|
| pydantic | ^2.0 | MIT | Data validation, settings |
| pydantic-settings | ^2.0 | MIT | Configuration management |
| click | ^8.1 | BSD-3 | CLI framework |
| typer | ^0.9 | MIT | CLI framework (alt) |
| rich | ^13.0 | MIT | Terminal formatting |

### 2.3 Storage

| Component | Version | License | Purpose |
|-----------|---------|---------|---------|
| sqlalchemy | ^2.0 | MIT | Database ORM |
| aiosqlite | ^0.19 | MIT | Async SQLite |
| asyncpg | ^0.29 | Apache-2 | PostgreSQL async |
| python-dotenv | ^1.0 | BSD | Env file parsing |

### 2.4 HTTP/Networking

| Component | Version | License | Purpose |
|-----------|---------|---------|---------|
| httpx | ^0.25 | BSD-3 | HTTP client (SDK mode) |
| aiohttp | ^3.9 | Apache-2 | Async HTTP server |
| uvicorn | ^0.25 | BSD-3 | ASGI server |
| hypercorn | ^0.14 | MIT | ASGI server (alt) |

### 2.5 Data Processing

| Component | Version | License | Purpose |
|-----------|---------|---------|---------|
| python-json-logger | ^2.0 | BSD | JSON logging |
| orjson | ^3.9 | Apache-2/ISC | Fast JSON |
| msgspec | ^0.18 | Apache-2 | Fast serialization |

### 2.6 Utilities

| Component | Version | License | Purpose |
|-----------|---------|---------|---------|
| python-dateutil | ^2.8 | BSD | Date utilities |
| pytz | ^2023.3 | MIT | Timezone handling |
| pathspec | ^0.11 | MPL-2 | Path matching |
| watchdog | ^3.0 | Apache-2 | File watching |
| aiosignal | ^1.3 | Apache-2 | Async signals |

---

## 3. Optional Dependencies

### 3.1 Web UI

| Component | Version | License | Purpose |
|-----------|---------|---------|---------|
| fastapi | ^0.109 | MIT | Web framework |
| jinja2 | ^3.1 | BSD-3 | Template engine |
| websockets | ^12.0 | BSD | WebSocket support |

### 3.2 Analysis

| Component | Version | License | Purpose |
|-----------|---------|---------|---------|
| numpy | ^1.26 | BSD | Numerical computing |
| scipy | ^1.11 | BSD | Statistical analysis |

### 3.3 Cloud Storage

| Component | Version | License | Purpose |
|-----------|---------|---------|---------|
| boto3 | ^1.34 | Apache-2 | AWS S3 |
| google-cloud-storage | ^2.14 | Apache-2 | GCS |

---

## 4. Development Dependencies

### 4.1 Testing

| Component | Version | License | Purpose |
|-----------|---------|---------|---------|
| pytest | ^7.4 | MIT | Testing framework |
| pytest-asyncio | ^0.21 | Apache-2 | Async testing |
| pytest-cov | ^4.1 | MIT | Coverage |
| hypothesis | ^6.88 | MPL-2 | Property testing |
| pytest-mock | ^3.12 | MIT | Mocking |

### 4.2 Linting & Formatting

| Component | Version | License | Purpose |
|-----------|---------|---------|---------|
| ruff | ^0.1 | MIT | Linting |
| black | ^23.0 | MIT | Formatting |
| mypy | ^1.7 | MIT | Type checking |
| pre-commit | ^3.5 | MIT | Git hooks |

### 4.3 Documentation

| Component | Version | License | Purpose |
|-----------|---------|---------|---------|
| mkdocs | ^1.5 | BSD-2 | Documentation |
| mkdocs-material | ^9.4 | MIT | Theme |
| mkdocstrings | ^0.24 | MIT | API docs |

---

## 5. Adapter Dependencies

### 5.1 OpenAI Adapter

| Component | Version | License | Purpose |
|-----------|---------|---------|---------|
| openai | ^1.12 | Apache-2 | OpenAI SDK |

### 5.2 Anthropic Adapter

| Component | Version | License | Purpose |
|-----------|---------|---------|---------|
| anthropic | ^0.18 | Apache-2 | Anthropic SDK |

### 5.3 Ollama Adapter

| Component | Version | License | Purpose |
|-----------|---------|---------|---------|
| ollama | (custom) | MIT | Ollama Python client |

### 5.4 Gemini Adapter

| Component | Version | License | Purpose |
|-----------|---------|---------|---------|
| google-generativeai | ^0.5 | Apache-2 | Gemini SDK |

---

## 6. Project Structure

```
chaintrace/
├── chaintrace/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── engine.py
│   │   └── exceptions.py
│   ├── capture/
│   │   ├── __init__.py
│   │   ├── proxy.py
│   │   ├── sdk.py
│   │   └── log_parser.py
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── backend.py
│   │   ├── sqlite.py
│   │   ├── file.py
│   │   └── postgresql.py
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── openai.py
│   │   ├── anthropic.py
│   │   ├── codex.py
│   │   ├── ollama.py
│   │   └── gemini.py
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── cot_extractor.py
│   │   ├── token_count.py
│   │   └── latency.py
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── commands.py
│   │   └── output.py
│   └── api/
│       ├── __init__.py
│       ├── routes.py
│       └── schemas.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── docs/
├── examples/
├── pyproject.toml
├── uv.lock
├── README.md
├── LICENSE
├── BRS.md
├── SRS.md
└── SBoM.md
```

---

## 7. Dependency Graph

```
chaintrace (package)
├── pydantic
│   └── pydantic-core
├── click
│   └── colorama (Windows)
├── sqlalchemy
│   └── typing-extensions
├── aiosqlite
│   └── aiofiles
├── aiohttp
│   ├── aiodns
│   ├── aiohttp[ speedups]
│   └── frozenlist
├── httpx
│   ├── certifi
│   ├── h11
│   └── idna
├── uvicorn
│   ├── click
│   ├── httptools
│   └── uvloop (Linux/macOS)
├── orjson
├── python-dotenv
├── python-json-logger
├── pathspec
├── watchdog
└── rich
    └── pygments (optional)
```

---

## 8. License Summary

| License | Count | Components |
|---------|-------|------------|
| MIT | 18 | Core frameworks, CLI, storage, utilities |
| BSD-3 | 5 | HTTP, web framework |
| Apache-2 | 8 | Cloud SDKs, AI SDKs |
| BSD-2 | 1 | Documentation |
| PSF | 1 | Python runtime |
| MPL-2 | 2 | Testing utilities |

**Total Direct Dependencies:** ~34  
**Total Transitive Dependencies:** ~120

---

## 9. Security Considerations

### 9.1 Vulnerability Scanning
- Use `pip-audit` or `safety` for dependency vulnerability scanning
- Integrate in CI/CD pipeline

### 9.2 Minimal Dependencies
- Core intentionally lean (~15 direct dependencies)
- Optional features isolated in extra dependencies

---

## 10. Version Pinning Strategy

| Type | Strategy |
|------|----------|
| Core (production) | Minimum version (^), allow patch updates |
| Dev tools | Exact or tight (>=) for consistency |
| Cloud SDKs | Flexible (>=) for compatibility |

---

**Document Status:** Draft v1.0 — Ready for review