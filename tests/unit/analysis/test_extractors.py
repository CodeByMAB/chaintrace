"""Tests for CoT extractors."""

import pytest

from chaintrace.analysis.extractors.xml import XmlExtractor
from chaintrace.analysis.extractors.markdown import MarkdownExtractor
from chaintrace.analysis.extractors.json_extractor import JsonExtractor


# ── XML ───────────────────────────────────────────────────────────────────────

class TestXmlExtractor:
    def setup_method(self):
        self.ext = XmlExtractor()

    def test_extracts_thinking_tag(self):
        text = "<thinking>I need to think carefully.</thinking>"
        steps = self.ext.extract(text)
        assert len(steps) == 1
        assert steps[0].content == "I need to think carefully."

    def test_extracts_reasoning_tag(self):
        text = "<reasoning>Step A.\nStep B.</reasoning>"
        steps = self.ext.extract(text)
        assert len(steps) == 1
        assert "Step A." in steps[0].content

    def test_extracts_multiple_tags(self):
        text = "<thinking>First</thinking>\nSome output\n<thinking>Second</thinking>"
        steps = self.ext.extract(text)
        assert len(steps) == 2
        assert steps[0].content == "First"
        assert steps[1].content == "Second"

    def test_step_numbers_sequential(self):
        text = "<step>One</step><step>Two</step><step>Three</step>"
        steps = self.ext.extract(text)
        assert [s.step for s in steps] == [1, 2, 3]

    def test_can_handle_true_with_tags(self):
        assert self.ext.can_handle("<thinking>hello</thinking>") is True

    def test_can_handle_false_without_tags(self):
        assert self.ext.can_handle("Just plain text.") is False

    def test_empty_tags_skipped(self):
        text = "<thinking></thinking><thinking>Real content</thinking>"
        steps = self.ext.extract(text)
        assert len(steps) == 1
        assert steps[0].content == "Real content"

    def test_multiline_content(self):
        text = "<reasoning>\nLine 1\nLine 2\nLine 3\n</reasoning>"
        steps = self.ext.extract(text)
        assert len(steps) == 1
        assert "Line 1" in steps[0].content


# ── Markdown ──────────────────────────────────────────────────────────────────

class TestMarkdownExtractor:
    def setup_method(self):
        self.ext = MarkdownExtractor()

    def test_extracts_numbered_headings(self):
        text = "## Step 1: Setup\nDo setup.\n\n## Step 2: Execute\nDo execute."
        steps = self.ext.extract(text)
        assert len(steps) == 2
        assert "Do setup." in steps[0].content
        assert "Do execute." in steps[1].content

    def test_extracts_bold_sections(self):
        text = "**Reasoning:**\nI think...\n\n**Analysis:**\nBecause..."
        steps = self.ext.extract(text)
        assert len(steps) == 2

    def test_can_handle_with_headings(self):
        assert self.ext.can_handle("## Step 1\nSome content") is True

    def test_can_handle_false_plain(self):
        assert self.ext.can_handle("Just a regular answer.") is False

    def test_returns_empty_for_unstructured(self):
        steps = self.ext.extract("No structure here at all.")
        assert steps == []

    def test_step_numbers_sequential(self):
        text = "## Step 1\nA\n## Step 2\nB\n## Step 3\nC"
        steps = self.ext.extract(text)
        assert [s.step for s in steps] == [1, 2, 3]


# ── JSON ──────────────────────────────────────────────────────────────────────

class TestJsonExtractor:
    def setup_method(self):
        self.ext = JsonExtractor()

    def test_extracts_reasoning_list(self):
        import json
        text = json.dumps({"reasoning": ["Step one", "Step two", "Step three"]})
        steps = self.ext.extract(text)
        assert len(steps) == 3
        assert steps[0].content == "Step one"

    def test_extracts_chain_of_thought_string(self):
        import json
        text = json.dumps({"chain_of_thought": "My reasoning process here."})
        steps = self.ext.extract(text)
        assert len(steps) == 1
        assert steps[0].content == "My reasoning process here."

    def test_extracts_steps_with_content_key(self):
        import json
        text = json.dumps({"steps": [{"content": "A"}, {"content": "B"}]})
        steps = self.ext.extract(text)
        assert len(steps) == 2

    def test_extracts_from_json_fence(self):
        text = 'Here is my response:\n```json\n{"reasoning": ["Alpha", "Beta"]}\n```'
        steps = self.ext.extract(text)
        assert len(steps) == 2
        assert steps[0].content == "Alpha"

    def test_can_handle_json_object(self):
        assert self.ext.can_handle('{"key": "value"}') is True

    def test_can_handle_false_plain_text(self):
        assert self.ext.can_handle("Just plain text without braces.") is False

    def test_returns_empty_for_irrelevant_json(self):
        import json
        text = json.dumps({"foo": "bar", "baz": 123})
        steps = self.ext.extract(text)
        assert steps == []

    def test_step_numbers_sequential(self):
        import json
        text = json.dumps({"reasoning": ["A", "B", "C"]})
        steps = self.ext.extract(text)
        assert [s.step for s in steps] == [1, 2, 3]
