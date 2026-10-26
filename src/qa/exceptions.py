"""Exception hierarchy for the Q&A agent.

Mirrors the style of ``src.memory.exceptions``: every error this package
raises to its callers is a :class:`QAError` (or a subclass), so UI code can
catch one type. Underlying :class:`~src.memory.exceptions.HindsightError`
failures are wrapped rather than leaked, keeping their cause on
``__cause__``.
"""

from __future__ import annotations

from typing import Optional


class QAError(Exception):
    """Base class for every error raised by the Q&A agent."""

    code: str = "qa_error"

    def __init__(self, message: str, *, detail: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.detail = detail

    def __str__(self) -> str:  # pragma: no cover - trivial
        if self.detail:
            return f"{self.message} ({self.detail})"
        return self.message


class RetrievalError(QAError):
    """The memory store could not be queried."""

    code = "retrieval_error"

# Note: an empty knowledge base and a non-grounded candidate answer are NOT
# QAError subclasses — QAAgent.ask() never raises for either. Both are
# correct, successful outcomes ("I don't know", not "something broke"), so
# they come back as a refusal QAAnswer (see agent.py's `_refusal`) rather
# than an exception a caller would have to catch.
