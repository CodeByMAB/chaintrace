"""Tests for the SQLite storage backend."""

import pytest

from chaintrace.storage.sqlite import SqliteBackend
from chaintrace.types.trace import QueryFilters, ReasoningStep, Trace


@pytest.fixture
async def backend(tmp_path):
    db = SqliteBackend()
    await db.initialize({"path": str(tmp_path / "test.db")})
    yield db
    await db.close()


def _make_trace(**kwargs) -> Trace:
    defaults = dict(
        adapter="openai",
        model="gpt-4o",
        request={"model": "gpt-4o", "messages": []},
        response={"choices": [{"message": {"content": "hello"}}]},
        reasoning_chain=[
            ReasoningStep(step=1, content="First thought"),
            ReasoningStep(step=2, content="Second thought"),
        ],
    )
    defaults.update(kwargs)
    return Trace(**defaults)


@pytest.mark.asyncio
async def test_store_and_get(backend):
    trace = _make_trace()
    await backend.store(trace)

    retrieved = await backend.get(trace.id)
    assert retrieved is not None
    assert retrieved.adapter == "openai"
    assert retrieved.model == "gpt-4o"
    assert len(retrieved.reasoning_chain) == 2
    assert retrieved.reasoning_chain[0].content == "First thought"


@pytest.mark.asyncio
async def test_get_nonexistent_returns_none(backend):
    result = await backend.get("does-not-exist")
    assert result is None


@pytest.mark.asyncio
async def test_store_assigns_id(backend):
    trace = _make_trace()
    assert trace.id is None
    await backend.store(trace)
    assert trace.id is not None


@pytest.mark.asyncio
async def test_store_updates_existing(backend):
    trace = _make_trace()
    await backend.store(trace)
    trace_id = trace.id

    trace.model = "gpt-4o-mini"
    await backend.store(trace)

    retrieved = await backend.get(trace_id)
    assert retrieved.model == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_query_all(backend):
    for _ in range(3):
        await backend.store(_make_trace())

    results = await backend.query(QueryFilters())
    assert len(results) == 3


@pytest.mark.asyncio
async def test_query_filter_adapter(backend):
    await backend.store(_make_trace(adapter="openai"))
    await backend.store(_make_trace(adapter="anthropic"))

    results = await backend.query(QueryFilters(adapter="anthropic"))
    assert len(results) == 1
    assert results[0].adapter == "anthropic"


@pytest.mark.asyncio
async def test_query_filter_model(backend):
    await backend.store(_make_trace(model="gpt-4o"))
    await backend.store(_make_trace(model="gpt-3.5-turbo"))

    results = await backend.query(QueryFilters(model="gpt-4o"))
    assert len(results) == 1


@pytest.mark.asyncio
async def test_query_limit_offset(backend):
    for _ in range(5):
        await backend.store(_make_trace())

    page1 = await backend.query(QueryFilters(), limit=2, offset=0)
    page2 = await backend.query(QueryFilters(), limit=2, offset=2)
    assert len(page1) == 2
    assert len(page2) == 2
    assert {t.id for t in page1}.isdisjoint({t.id for t in page2})


@pytest.mark.asyncio
async def test_delete(backend):
    trace = _make_trace()
    await backend.store(trace)

    deleted = await backend.delete(trace.id)
    assert deleted is True

    assert await backend.get(trace.id) is None


@pytest.mark.asyncio
async def test_delete_nonexistent_returns_false(backend):
    result = await backend.delete("ghost-id")
    assert result is False


@pytest.mark.asyncio
async def test_stats(backend):
    await backend.store(_make_trace(adapter="openai", model="gpt-4o"))
    await backend.store(_make_trace(adapter="openai", model="gpt-4o"))
    await backend.store(_make_trace(adapter="anthropic", model="claude-3"))

    s = await backend.stats()
    assert s.total_traces == 3
    assert s.by_adapter["openai"] == 2
    assert s.by_adapter["anthropic"] == 1
    assert s.by_model["gpt-4o"] == 2


@pytest.mark.asyncio
async def test_timestamp_proof_roundtrip(backend):
    proof = {
        "hash": "abc123",
        "submitted_at": "2026-05-24T00:00:00",
        "calendar_url": "https://alice.btc.calendar.opentimestamps.org",
        "status": "pending",
    }
    trace = _make_trace(timestamp_proof=proof, timestamped=True)
    await backend.store(trace)

    retrieved = await backend.get(trace.id)
    assert retrieved.timestamped is True
    assert retrieved.timestamp_proof["hash"] == "abc123"
    assert retrieved.timestamp_proof["status"] == "pending"


@pytest.mark.asyncio
async def test_timestamped_false_by_default(backend):
    trace = _make_trace()
    await backend.store(trace)

    retrieved = await backend.get(trace.id)
    assert retrieved.timestamped is False
    assert retrieved.timestamp_proof is None
