"""Tests for OpenAI and Anthropic adapters."""

import pytest

from chaintrace.adapters.openai import OpenAIAdapter
from chaintrace.adapters.anthropic import AnthropicAdapter


# ── OpenAI ────────────────────────────────────────────────────────────────────

class TestOpenAIAdapter:
    def setup_method(self):
        self.adapter = OpenAIAdapter()

    def test_extract_content_standard(self):
        response = {"choices": [{"message": {"content": "Hello!"}}]}
        assert self.adapter.extract_content(response) == "Hello!"

    def test_extract_content_empty(self):
        assert self.adapter.extract_content({}) == ""

    def test_extract_usage_standard(self):
        response = {"usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}}
        usage = self.adapter.extract_usage(response)
        assert usage["prompt_tokens"] == 10
        assert usage["completion_tokens"] == 20
        assert usage["total_tokens"] == 30

    def test_extract_usage_missing(self):
        usage = self.adapter.extract_usage({})
        assert usage == {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def test_extract_reasoning_from_content_paragraphs(self):
        response = {
            "choices": [{"message": {"content": "First paragraph.\n\nSecond paragraph."}}]
        }
        steps = self.adapter.extract_reasoning(response)
        assert len(steps) == 2
        assert steps[0].content == "First paragraph."
        assert steps[1].content == "Second paragraph."
        assert steps[0].step == 1
        assert steps[1].step == 2

    def test_extract_reasoning_o1_style(self):
        response = {
            "usage": {"reasoning_content": "Line one\nLine two\nLine three"},
            "choices": [{"message": {"content": "Answer"}}],
        }
        steps = self.adapter.extract_reasoning(response)
        # o1 reasoning takes priority over content
        assert any("Line one" in s.content for s in steps)

    def test_supports_choices(self):
        assert self.adapter.supports({"choices": []}) is True

    def test_supports_usage(self):
        assert self.adapter.supports({"usage": {}}) is True

    def test_supports_rejects_unknown(self):
        assert self.adapter.supports({}) is False


# ── Anthropic ─────────────────────────────────────────────────────────────────

class TestAnthropicAdapter:
    def setup_method(self):
        self.adapter = AnthropicAdapter()

    def test_extract_content_text_block(self):
        response = {"content": [{"type": "text", "text": "Hello!"}]}
        assert self.adapter.extract_content(response) == "Hello!"

    def test_extract_content_multiple_blocks(self):
        response = {
            "content": [
                {"type": "thinking", "thinking": "..."},
                {"type": "text", "text": "Part 1"},
                {"type": "text", "text": "Part 2"},
            ]
        }
        assert self.adapter.extract_content(response) == "Part 1\nPart 2"

    def test_extract_content_string_legacy(self):
        response = {"content": "Legacy string"}
        assert self.adapter.extract_content(response) == "Legacy string"

    def test_extract_usage(self):
        response = {"usage": {"input_tokens": 15, "output_tokens": 25}}
        usage = self.adapter.extract_usage(response)
        assert usage["prompt_tokens"] == 15
        assert usage["completion_tokens"] == 25
        assert usage["total_tokens"] == 40

    def test_extract_reasoning_thinking_blocks(self):
        response = {
            "content": [
                {"type": "thinking", "thinking": "Step A\nStep B"},
                {"type": "text", "text": "Answer"},
            ]
        }
        steps = self.adapter.extract_reasoning(response)
        assert len(steps) >= 1
        assert any("Step A" in s.content for s in steps)

    def test_extract_reasoning_no_thinking(self):
        response = {"content": [{"type": "text", "text": "Just an answer."}]}
        steps = self.adapter.extract_reasoning(response)
        assert steps == []

    def test_supports_list_content(self):
        assert self.adapter.supports({"content": []}) is True

    def test_supports_string_content(self):
        assert self.adapter.supports({"content": "hello"}) is True

    def test_supports_rejects_choices(self):
        assert self.adapter.supports({"choices": []}) is False
