"""Hindsight — a local, file-based memory & project-management system.

A Codex-style store that organizes long-lived "memories" into projects on the
local filesystem. The package is intentionally dependency-free (standard
library only) so it can be embedded in the Gradio WebUI or used on its own.

Public surface:
    HindsightStore   -- the main entry point (projects + memories)
    Project, Memory  -- lightweight data records
    exceptions       -- the Hindsight error hierarchy
"""

from .exceptions import (
    HindsightError,
    StorageError,
    NotFoundError,
    ValidationError,
    CorruptedRecordError,
    DuplicateError,
)
from .models import Project, Memory
from .store import HindsightStore

__all__ = [
    "HindsightStore",
    "Project",
    "Memory",
    "HindsightError",
    "StorageError",
    "NotFoundError",
    "ValidationError",
    "CorruptedRecordError",
    "DuplicateError",
]
