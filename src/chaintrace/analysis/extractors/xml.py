"""XML-tag CoT extractor.

Handles models that wrap reasoning in XML-style tags, e.g.:

    <thinking>...</thinking>
    <reasoning>...</reasoning>
    <step>...</step>

Each tag occurrence becomes one ReasoningStep.  Nested content is kept as-is.
"""

import re
from datetime import datetime

from chaintrace.analysis.extractors.base import BaseExtractor
from chaintrace.types.trace import ReasoningStep

# Tags that typically contain reasoning content, in priority order
_REASONING_TAGS = ["thinking", "reasoning", "thought", "scratchpad", "analysis", "step"]

# Compiled pattern: matches <tag>...</tag> (non-greedy, DOTALL)
_TAG_RE = re.compile(
    r"<({tags})(\s[^>]*)?>(.+?)</\1>".format(tags="|".join(_REASONING_TAGS)),
    re.DOTALL | re.IGNORECASE,
)


class XmlExtractor(BaseExtractor):
    """Extract reasoning from XML-tagged content."""

    name = "xml"

    def can_handle(self, text: str) -> bool:
        return bool(_TAG_RE.search(text))

    def extract(self, text: str) -> list[ReasoningStep]:
        steps = []
        for i, match in enumerate(_TAG_RE.finditer(text), start=1):
            content = match.group(3).strip()
            if content:
                steps.append(
                    ReasoningStep(step=i, content=content, timestamp=datetime.utcnow())
                )
        return steps
