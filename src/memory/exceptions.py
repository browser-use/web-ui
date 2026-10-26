"""Exception hierarchy for the Hindsight memory system.

Every error Hindsight raises to its callers is a :class:`HindsightError` (or a
subclass), so UI code can catch one type and show a friendly message instead of
leaking a raw ``OSError`` / ``JSONDecodeError`` / ``KeyError`` from deep inside
the store. Low-level failures are wrapped (see :func:`guard` in ``store.py``)
and keep their original cause on ``__cause__`` for logging.
"""

from __future__ import annotations

from typing import Optional


class HindsightError(Exception):
    """Base class for every error raised by Hindsight."""

    #: A short, stable, machine-readable code (handy for UIs / logs).
    code: str = "hindsight_error"

    def __init__(self, message: str, *, detail: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.detail = detail

    def __str__(self) -> str:  # pragma: no cover - trivial
        # `detail` can carry a raw OSError/traceback string from `guard`, and
        # this is what UI code shows to the end user (see src/ui/agentic_tabs
        # .py) — so __str__ stays to the stable message only. `detail` is
        # still there on the exception object for logging.
        return self.message

    def log_str(self) -> str:
        """Full text including the low-level `detail`, for server-side logs."""
        if self.detail:
            return f"{self.message} ({self.detail})"
        return self.message


class StorageError(HindsightError):
    """The filesystem could not be read from or written to."""

    code = "storage_error"


class NotFoundError(HindsightError):
    """A requested project or memory does not exist."""

    code = "not_found"


class ValidationError(HindsightError):
    """Caller-supplied data failed validation before it could be stored."""

    code = "validation_error"


class CorruptedRecordError(HindsightError):
    """A record on disk exists but could not be parsed into a valid object.

    The offending file is quarantined rather than deleted, so no data is lost
    and the rest of the store keeps working.
    """

    code = "corrupted_record"

    def __init__(self, message: str, *, path: Optional[str] = None,
                 quarantine_path: Optional[str] = None, detail: Optional[str] = None):
        super().__init__(message, detail=detail)
        self.path = path
        self.quarantine_path = quarantine_path


class DuplicateError(HindsightError):
    """An entity with the same unique key already exists."""

    code = "duplicate"
