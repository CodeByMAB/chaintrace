"""Markdown CoT extractor.

Handles models that structure reasoning as markdown, e.g.:

    ## Step 1: Understand the problem
    ...content...

    ## Step 2: Devise a plan
    ...content...

    **Reasoning:**
    ...content...

Two heuristics are applied in order:
1. Numbered/labeled headings  (## Step N ..., ### 1. ..., #### Step N)
2. Bold section headers       (**Reasoning:**, **Analysis:**, etc.)
"""

import re
from datetime import datetime

from chaintrace.analysis.extractors.base import BaseExtractor
from chaintrace.types.trace import ReasoningStep

# Heading-based steps: ## Step 1, ### 1., ## 2. Title, etc.
_HEADING_RE = re.compile(
    r"^#{1,4}\s+(?:step\s*\d+[.:)]?|(\d+)[.)\s])\s*(.*)",
    re.IGNORECASE | re.MULTILINE,
)

# Bold section headers at the start of a line
_BOLD_SECTION_TAGS = [
    "reasoning", "analysis", "thinking", "thought", "scratchpad",
    "plan", "approach", "solution", "answer",
]
_BOLD_RE = re.compile(
    r"^\*\*(?:{tags})[:\s]*\*\*\s*(.*)".format(tags="|".join(_BOLD_SECTION_TAGS)),
    re.IGNORECASE | re.MULTILINE,
)


def _split_by_headings(text: str) -> list[str]:
    """Split text into sections using heading matches as delimiters."""
    positions = [m.start() for m in _HEADING_RE.finditer(text)]
    if not positions:
        return []

    sections = []
    for idx, start in enumerate(positions):
        end = positions[idx + 1] if idx + 1 < len(positions) else len(text)
        section = text[start:end].strip()
        # Drop the heading line itself, keep the body
        body_start = section.find("\n")
        body = section[body_start:].strip() if body_start != -1 else ""
        if body:
            sections.append(body)

    return sections


def _split_by_bold(text: str) -> list[str]:
    """Split text into sections using bold section headers as delimiters."""
    positions = [m.start() for m in _BOLD_RE.finditer(text)]
    if not positions:
        return []

    sections = []
    for idx, start in enumerate(positions):
        end = positions[idx + 1] if idx + 1 < len(positions) else len(text)
        section = text[start:end].strip()
        body_start = section.find("\n")
        body = section[body_start:].strip() if body_start != -1 else ""
        if not body:
            # Inline content after the bold header
            match = _BOLD_RE.match(section)
            body = match.group(1).strip() if match and match.group(1).strip() else ""
        if body:
            sections.append(body)

    return sections


class MarkdownExtractor(BaseExtractor):
    """Extract reasoning steps from markdown-structured responses."""

    name = "markdown"

    def can_handle(self, text: str) -> bool:
        return bool(_HEADING_RE.search(text) or _BOLD_RE.search(text))

    def extract(self, text: str) -> list[ReasoningStep]:
        sections = _split_by_headings(text) or _split_by_bold(text)
        return [
            ReasoningStep(step=i, content=s, timestamp=datetime.utcnow())
            for i, s in enumerate(sections, start=1)
            if s
        ]
