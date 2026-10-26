"""Data records for Hindsight: :class:`Project` and :class:`Memory`.

These are plain dataclasses with ``to_dict`` / ``from_dict`` helpers and strict
validation on construction, so a malformed file on disk surfaces as a
``ValidationError`` instead of silently producing a half-built object.
"""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from .exceptions import ValidationError

# Memory "kinds" — mirrors the lightweight taxonomy Codex-style systems use.
MEMORY_TYPES = ("note", "fact", "task", "decision", "snippet", "reference")


def _now() -> float:
    return time.time()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _require_str(value: Any, field_name: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"'{field_name}' must be a string",
                              detail=f"got {type(value).__name__}")
    if not allow_empty and not value.strip():
        raise ValidationError(f"'{field_name}' must not be empty")
    return value


def _require_timestamp(value: Any, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"'{field_name}' must be a number",
                              detail=f"got {type(value).__name__}")
    if not math.isfinite(value):
        raise ValidationError(f"'{field_name}' must be a finite number",
                              detail=repr(value))
    return float(value)


def _coerce_tags(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, (list, tuple)):
        raise ValidationError("'tags' must be a list of strings",
                              detail=f"got {type(value).__name__}")
    tags: List[str] = []
    for tag in value:
        if not isinstance(tag, str):
            raise ValidationError("every tag must be a string",
                                  detail=f"got {type(tag).__name__}")
        tag = tag.strip()
        if tag and tag not in tags:
            tags.append(tag)
    return tags


@dataclass
class Project:
    """A container that groups related memories."""

    name: str
    description: str = ""
    id: str = field(default_factory=lambda: _new_id("proj"))
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_str(self.name, "name")
        _require_str(self.description, "description", allow_empty=True)
        _require_str(self.id, "id")
        self.tags = _coerce_tags(self.tags)
        self.created_at = _require_timestamp(self.created_at, "created_at")
        self.updated_at = _require_timestamp(self.updated_at, "updated_at")
        if not isinstance(self.metadata, dict):
            raise ValidationError("'metadata' must be an object",
                                  detail=f"got {type(self.metadata).__name__}")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Project":
        if not isinstance(data, dict):
            raise ValidationError("project record must be an object")
        if not data.get("id"):
            raise ValidationError("project record is missing a required field",
                                  detail="id")
        try:
            return cls(
                name=data["name"],
                description=data.get("description", ""),
                id=data["id"],
                tags=data.get("tags", []),
                created_at=data.get("created_at", _now()),
                updated_at=data.get("updated_at", _now()),
                metadata=data.get("metadata", {}),
            )
        except KeyError as exc:
            raise ValidationError("project record is missing a required field",
                                  detail=str(exc)) from exc
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValidationError("project record has an invalid field",
                                  detail=str(exc)) from exc


@dataclass
class Memory:
    """A single remembered item that lives inside a project."""

    project_id: str
    title: str
    content: str = ""
    type: str = "note"
    id: str = field(default_factory=lambda: _new_id("mem"))
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_str(self.project_id, "project_id")
        _require_str(self.title, "title")
        _require_str(self.content, "content", allow_empty=True)
        _require_str(self.id, "id")
        if self.type not in MEMORY_TYPES:
            raise ValidationError(
                f"'type' must be one of {', '.join(MEMORY_TYPES)}",
                detail=f"got {self.type!r}")
        self.tags = _coerce_tags(self.tags)
        self.created_at = _require_timestamp(self.created_at, "created_at")
        self.updated_at = _require_timestamp(self.updated_at, "updated_at")
        if not isinstance(self.metadata, dict):
            raise ValidationError("'metadata' must be an object",
                                  detail=f"got {type(self.metadata).__name__}")

    def touch(self) -> None:
        self.updated_at = _now()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Memory":
        if not isinstance(data, dict):
            raise ValidationError("memory record must be an object")
        if not data.get("id"):
            raise ValidationError("memory record is missing a required field",
                                  detail="id")
        try:
            return cls(
                project_id=data["project_id"],
                title=data["title"],
                content=data.get("content", ""),
                type=data.get("type", "note"),
                id=data["id"],
                tags=data.get("tags", []),
                created_at=data.get("created_at", _now()),
                updated_at=data.get("updated_at", _now()),
                metadata=data.get("metadata", {}),
            )
        except KeyError as exc:
            raise ValidationError("memory record is missing a required field",
                                  detail=str(exc)) from exc
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValidationError("memory record has an invalid field",
                                  detail=str(exc)) from exc
