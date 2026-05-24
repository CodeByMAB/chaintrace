"""ChainTrace - Modular AI Chain-of-Thought Tracer

Capture, store, analyze, and visualize reasoning traces from any AI model.
"""

__version__ = "0.1.0"
__author__ = "CodeByMAB"

from chaintrace.core.engine import ChainTraceEngine
from chaintrace.types.trace import Trace

__all__ = ["ChainTraceEngine", "Trace", "__version__"]