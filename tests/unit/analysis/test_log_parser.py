"""Tests for the log parser capture source."""

import json
import pytest

from chaintrace.capture.log_parser import LogParser, _detect_adapter, _parse_line
from pathlib import Path


# ── Unit helpers ──────────────────────────────────────────────────────────────

def test_detect_adapter_openai():
    assert _detect_adapter({"choices": []}) == "openai"

def test_detect_adapter_anthropic():
    assert _detect_adapter({"content": []}) == "anthropic"

def test_detect_adapter_fallback():
    assert _detect_adapter({"unknown": "keys"}) == "openai"

def test_parse_line_wrapped_format(tmp_path):
    line = json.dumps({
        "request": {"model": "gpt-4o", "messages": []},
        "response": {"choices": []},
        "adapter": "openai",
    })
    result = _parse_line(line, tmp_path / "f.jsonl")
    assert result is not None
    req, resp, adapter = result
    assert req["model"] == "gpt-4o"
    assert adapter == "openai"

def test_parse_line_flat_format(tmp_path):
    line = json.dumps({
        "choices": [{"message": {"content": "Hi"}}],
        "model": "gpt-4o",
        "_request": {"messages": [{"role": "user", "content": "Hello"}]},
    })
    result = _parse_line(line, tmp_path / "f.jsonl")
    assert result is not None
    req, resp, adapter = result
    assert adapter == "openai"
    assert req == {"messages": [{"role": "user", "content": "Hello"}]}

def test_parse_line_comment(tmp_path):
    assert _parse_line("# this is a comment", tmp_path / "f.jsonl") is None

def test_parse_line_blank(tmp_path):
    assert _parse_line("   ", tmp_path / "f.jsonl") is None

def test_parse_line_malformed(tmp_path):
    assert _parse_line("{not json}", tmp_path / "f.jsonl") is None


# ── Integration: reading files ─────────────────────────────────────────────────

@pytest.fixture
def sample_jsonl(tmp_path) -> Path:
    records = [
        {
            "request": {"model": "gpt-4o", "messages": []},
            "response": {"choices": [{"message": {"content": "hello"}}], "usage": {}},
            "adapter": "openai",
        },
        {
            "request": {"model": "gpt-4o", "messages": []},
            "response": {"choices": [{"message": {"content": "world"}}], "usage": {}},
        },
    ]
    path = tmp_path / "traces.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in records))
    return path


@pytest.mark.asyncio
async def test_parser_reads_jsonl(sample_jsonl):
    parser = LogParser([sample_jsonl])
    results = [rec async for rec in parser.records()]
    assert len(results) == 2


@pytest.mark.asyncio
async def test_parser_adapter_override(sample_jsonl):
    parser = LogParser([sample_jsonl], adapter="anthropic")
    results = [rec async for rec in parser.records()]
    assert all(adapter == "anthropic" for _, _, adapter in results)


@pytest.mark.asyncio
async def test_parser_skips_missing_file(tmp_path):
    parser = LogParser([tmp_path / "nonexistent.jsonl"])
    results = [rec async for rec in parser.records()]
    assert results == []


@pytest.mark.asyncio
async def test_parser_from_directory(tmp_path, sample_jsonl):
    parser = LogParser.from_directory(tmp_path, pattern="*.jsonl")
    results = [rec async for rec in parser.records()]
    assert len(results) == 2


@pytest.mark.asyncio
async def test_parser_reads_json_array(tmp_path):
    records = [
        {
            "request": {"model": "gpt-4o", "messages": []},
            "response": {"choices": [], "usage": {}},
            "adapter": "openai",
        }
    ]
    path = tmp_path / "batch.json"
    path.write_text(json.dumps(records))

    parser = LogParser([path])
    results = [rec async for rec in parser.records()]
    assert len(results) == 1


@pytest.mark.asyncio
async def test_parser_skips_comments_and_blanks(tmp_path):
    path = tmp_path / "mixed.jsonl"
    path.write_text(
        "# comment\n"
        "\n"
        + json.dumps({
            "request": {},
            "response": {"choices": []},
            "adapter": "openai",
        })
        + "\n"
    )
    parser = LogParser([path])
    results = [rec async for rec in parser.records()]
    assert len(results) == 1
