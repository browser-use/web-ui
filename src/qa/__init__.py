"""Agentic Q&A over the Hindsight memory store.

This package implements a small retrieval-augmented agent loop on top of
``src.memory.HindsightStore``: it retrieves candidate memories for a question,
decides whether it has enough grounding to answer, optionally reformulates the
query and retrieves again, and only ever answers with explicit citations back
to the memories it used. If nothing in the store supports an answer, it says
so instead of guessing.
"""

from .exceptions import QAError, RetrievalError
from .agent import QAAgent, QAAnswer, QASource

__all__ = [
    "QAAgent",
    "QAAnswer",
    "QASource",
    "QAError",
    "RetrievalError",
]
