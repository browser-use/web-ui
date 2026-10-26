"""HindsightStore — the file-backed project & memory store.

Layout on disk (default root: ``./tmp/hindsight``)::

    <root>/
      projects/
        <project_id>/
          project.json          # project metadata
          memories/
            <memory_id>.json    # one file per memory
      .quarantine/              # corrupted files moved aside, never deleted

Design goals
------------
* **Durability** — every write is atomic (temp file + ``os.replace``), so a
  crash mid-write can never leave a half-written JSON file.
* **Fault isolation** — a single corrupted record is quarantined and skipped;
  it never takes down a ``list`` call for a whole project.
* **One error type out** — callers only ever see a :class:`HindsightError`.
"""

from __future__ import annotations

import functools
import json
import logging
import os
import shutil
import tempfile
import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, TypeVar

from .exceptions import (
    CorruptedRecordError,
    DuplicateError,
    HindsightError,
    NotFoundError,
    StorageError,
    ValidationError,
)
from .models import Memory, Project

logger = logging.getLogger(__name__)

T = TypeVar("T")

DEFAULT_ROOT = os.path.join(".", "tmp", "hindsight")


def guard(action: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator: translate low-level errors into :class:`HindsightError`.

    Hindsight errors pass through unchanged; ``OSError`` becomes a
    :class:`StorageError`; anything else unexpected is logged and re-raised as a
    generic :class:`HindsightError` carrying the original as ``__cause__``.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return func(*args, **kwargs)
            except HindsightError:
                raise
            except OSError as exc:
                logger.error("Hindsight storage failure during %s: %s", action, exc)
                raise StorageError(f"could not {action}", detail=str(exc)) from exc
            except Exception as exc:  # noqa: BLE001 - last-resort guard
                logger.exception("Unexpected Hindsight failure during %s", action)
                raise HindsightError(f"unexpected failure while trying to {action}",
                                     detail=str(exc)) from exc

        return wrapper

    return decorator


class HindsightStore:
    """A thread-safe, file-backed store of projects and memories."""

    def __init__(self, root: str = DEFAULT_ROOT):
        self.root = os.path.abspath(root)
        self.projects_dir = os.path.join(self.root, "projects")
        self.quarantine_dir = os.path.join(self.root, ".quarantine")
        self._lock = threading.RLock()
        self._ensure_dirs()

    # ------------------------------------------------------------------ #
    # Filesystem plumbing
    # ------------------------------------------------------------------ #
    @guard("initialize the memory store")
    def _ensure_dirs(self) -> None:
        os.makedirs(self.projects_dir, exist_ok=True)
        os.makedirs(self.quarantine_dir, exist_ok=True)

    @staticmethod
    def _safe_component(value: str, field_name: str) -> str:
        """Reject anything that isn't a plain path segment.

        ``project_id`` / ``memory_id`` end up directly in filesystem paths;
        without this check a crafted id like ``"../../etc"`` or an absolute
        path could read, overwrite, or (via ``delete_project``'s
        ``shutil.rmtree``) recursively delete anything outside ``root``.
        """
        if (not isinstance(value, str) or not value
                or value in (os.curdir, os.pardir)
                or os.sep in value
                or (os.altsep and os.altsep in value)
                or value != os.path.basename(value)):
            raise ValidationError(f"'{field_name}' is not a valid id",
                                  detail=repr(value))
        return value

    def _project_dir(self, project_id: str) -> str:
        project_id = self._safe_component(project_id, "project_id")
        return os.path.join(self.projects_dir, project_id)

    def _project_file(self, project_id: str) -> str:
        return os.path.join(self._project_dir(project_id), "project.json")

    def _memories_dir(self, project_id: str) -> str:
        return os.path.join(self._project_dir(project_id), "memories")

    def _memory_file(self, project_id: str, memory_id: str) -> str:
        memory_id = self._safe_component(memory_id, "memory_id")
        return os.path.join(self._memories_dir(project_id), f"{memory_id}.json")

    def _atomic_write(self, path: str, data: Dict[str, Any]) -> None:
        """Write JSON atomically: dump to a temp file in the same dir, fsync,
        then ``os.replace`` over the target (atomic on POSIX and Windows)."""
        directory = os.path.dirname(path)
        os.makedirs(directory, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=directory, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, path)
        except BaseException:
            # Clean up the temp file on any failure, including interrupts.
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def _quarantine(self, path: str, reason: str) -> str:
        """Move a bad file into ``.quarantine`` and return its new path."""
        stamp = time.strftime("%Y%m%d-%H%M%S")
        # A short random suffix keeps two records quarantined within the same
        # second (same basename) from colliding and clobbering each other.
        unique = uuid.uuid4().hex[:8]
        base = f"{stamp}-{unique}-{os.path.basename(path)}"
        dest = os.path.join(self.quarantine_dir, base)
        try:
            shutil.move(path, dest)
            logger.warning("Quarantined corrupted record %s -> %s (%s)", path, dest, reason)
        except OSError as exc:
            logger.error("Failed to quarantine %s: %s", path, exc)
            return ""
        return dest

    def _read_json(self, path: str) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    def _load_project_record(self, path: str) -> Project:
        """Read + parse one project file, quarantining it if it is corrupt."""
        try:
            raw = self._read_json(path)
            project = Project.from_dict(raw)
            # A record whose *content* carries a path-like id (as opposed to
            # a bad filename, already rejected in _project_dir) would
            # otherwise pass from_dict's validation — it doesn't check id
            # shape — and only fail later, as an uncaught ValidationError
            # out of whatever store method next tries to build a path from
            # it. Catch that here instead, at load time, so it's quarantined
            # like any other corrupt record rather than crashing a caller.
            self._safe_component(project.id, "id")
            # A *safe but wrong* id (e.g. this project's file copied/edited
            # under a different id, or a file hand-renamed into another
            # project's directory) would otherwise load successfully but be
            # permanently unreachable through that id: every lookup builds
            # its path from the id, which would point elsewhere. Only an id
            # matching the directory it was actually found in is usable.
            on_disk_id = os.path.basename(os.path.dirname(path))
            if project.id != on_disk_id:
                raise ValidationError(
                    "project record's id does not match its directory",
                    detail=f"id={project.id!r} directory={on_disk_id!r}")
            return project
        except (json.JSONDecodeError, ValidationError, UnicodeDecodeError) as exc:
            qpath = self._quarantine(path, f"invalid project record: {exc}")
            raise CorruptedRecordError(
                "a project record on disk was unreadable and has been quarantined",
                path=path, quarantine_path=qpath, detail=str(exc)) from exc

    def _load_memory_record(self, path: str) -> Memory:
        try:
            raw = self._read_json(path)
            memory = Memory.from_dict(raw)
            self._safe_component(memory.id, "id")
            on_disk_id = os.path.splitext(os.path.basename(path))[0]
            if memory.id != on_disk_id:
                raise ValidationError(
                    "memory record's id does not match its filename",
                    detail=f"id={memory.id!r} filename={on_disk_id!r}")
            return memory
        except (json.JSONDecodeError, ValidationError, UnicodeDecodeError) as exc:
            qpath = self._quarantine(path, f"invalid memory record: {exc}")
            raise CorruptedRecordError(
                "a memory record on disk was unreadable and has been quarantined",
                path=path, quarantine_path=qpath, detail=str(exc)) from exc

    # ------------------------------------------------------------------ #
    # Projects
    # ------------------------------------------------------------------ #
    @guard("create a project")
    def create_project(self, name: str, description: str = "",
                        tags: Optional[List[str]] = None,
                        metadata: Optional[Dict[str, Any]] = None) -> Project:
        project = Project(name=name, description=description,
                          tags=tags or [], metadata=metadata or {})
        with self._lock:
            path = self._project_file(project.id)
            if os.path.exists(path):  # vanishingly unlikely UUID clash
                raise DuplicateError("a project with this id already exists",
                                     detail=project.id)
            self._atomic_write(path, project.to_dict())
        return project

    @guard("load a project")
    def get_project(self, project_id: str) -> Project:
        path = self._project_file(project_id)
        if not os.path.exists(path):
            raise NotFoundError("project not found", detail=project_id)
        with self._lock:
            return self._load_project_record(path)

    @guard("list projects")
    def list_projects(self) -> List[Project]:
        projects: List[Project] = []
        if not os.path.isdir(self.projects_dir):
            return projects
        with self._lock:
            for entry in sorted(os.listdir(self.projects_dir)):
                pfile = self._project_file(entry)
                if not os.path.isfile(pfile):
                    continue
                try:
                    projects.append(self._load_project_record(pfile))
                except CorruptedRecordError:
                    # One bad project must not hide the others.
                    continue
        projects.sort(key=lambda p: p.updated_at, reverse=True)
        return projects

    @guard("update a project")
    def update_project(self, project_id: str, *, name: Optional[str] = None,
                       description: Optional[str] = None,
                       tags: Optional[List[str]] = None,
                       metadata: Optional[Dict[str, Any]] = None) -> Project:
        with self._lock:
            project = self.get_project(project_id)
            if name is not None:
                project.name = name
            if description is not None:
                project.description = description
            if tags is not None:
                project.tags = tags
            if metadata is not None:
                project.metadata = metadata
            project.updated_at = time.time()
            # Re-validate by round-tripping through the dataclass.
            project = Project.from_dict(project.to_dict())
            self._atomic_write(self._project_file(project_id), project.to_dict())
        return project

    @guard("delete a project")
    def delete_project(self, project_id: str) -> None:
        with self._lock:
            pdir = self._project_dir(project_id)
            if not os.path.isdir(pdir):
                raise NotFoundError("project not found", detail=project_id)
            shutil.rmtree(pdir)

    # ------------------------------------------------------------------ #
    # Memories
    # ------------------------------------------------------------------ #
    @guard("add a memory")
    def add_memory(self, project_id: str, title: str, content: str = "",
                   type: str = "note", tags: Optional[List[str]] = None,
                   metadata: Optional[Dict[str, Any]] = None) -> Memory:
        with self._lock:
            # Ensure the parent project exists before writing a child record.
            if not os.path.exists(self._project_file(project_id)):
                raise NotFoundError("cannot add memory: project not found",
                                    detail=project_id)
            memory = Memory(project_id=project_id, title=title, content=content,
                            type=type, tags=tags or [], metadata=metadata or {})
            self._atomic_write(self._memory_file(project_id, memory.id),
                               memory.to_dict())
            self._bump_project(project_id)
        return memory

    @guard("load a memory")
    def get_memory(self, project_id: str, memory_id: str) -> Memory:
        path = self._memory_file(project_id, memory_id)
        if not os.path.exists(path):
            raise NotFoundError("memory not found", detail=memory_id)
        with self._lock:
            return self._load_memory_record(path)

    @guard("list memories")
    def list_memories(self, project_id: str) -> List[Memory]:
        mdir = self._memories_dir(project_id)
        if not os.path.exists(self._project_file(project_id)):
            raise NotFoundError("project not found", detail=project_id)
        memories: List[Memory] = []
        if not os.path.isdir(mdir):
            return memories
        with self._lock:
            for entry in os.listdir(mdir):
                if not entry.endswith(".json"):
                    continue
                try:
                    memories.append(self._load_memory_record(os.path.join(mdir, entry)))
                except CorruptedRecordError:
                    continue
        memories.sort(key=lambda m: m.updated_at, reverse=True)
        return memories

    @guard("update a memory")
    def update_memory(self, project_id: str, memory_id: str, *,
                      title: Optional[str] = None, content: Optional[str] = None,
                      type: Optional[str] = None, tags: Optional[List[str]] = None,
                      metadata: Optional[Dict[str, Any]] = None) -> Memory:
        with self._lock:
            memory = self.get_memory(project_id, memory_id)
            if title is not None:
                memory.title = title
            if content is not None:
                memory.content = content
            if type is not None:
                memory.type = type
            if tags is not None:
                memory.tags = tags
            if metadata is not None:
                memory.metadata = metadata
            memory.touch()
            memory = Memory.from_dict(memory.to_dict())  # re-validate
            self._atomic_write(self._memory_file(project_id, memory_id),
                               memory.to_dict())
            self._bump_project(project_id)
        return memory

    @guard("delete a memory")
    def delete_memory(self, project_id: str, memory_id: str) -> None:
        with self._lock:
            path = self._memory_file(project_id, memory_id)
            if not os.path.exists(path):
                raise NotFoundError("memory not found", detail=memory_id)
            os.unlink(path)
            self._bump_project(project_id)

    @guard("search memories")
    def search(self, query: str, project_id: Optional[str] = None,
               type: Optional[str] = None,
               tags: Optional[List[str]] = None) -> List[Memory]:
        """Case-insensitive substring search over title, content and tags."""
        needle = (query or "").strip().lower()
        want_tags = set(t.lower() for t in (tags or []))
        project_ids = ([project_id] if project_id
                       else [p.id for p in self.list_projects()])
        results: List[Memory] = []
        for pid in project_ids:
            try:
                candidates = self.list_memories(pid)
            except NotFoundError:
                continue
            for mem in candidates:
                if type and mem.type != type:
                    continue
                if want_tags and not want_tags.issubset({t.lower() for t in mem.tags}):
                    continue
                if needle:
                    haystack = f"{mem.title}\n{mem.content}\n{' '.join(mem.tags)}".lower()
                    if needle not in haystack:
                        continue
                results.append(mem)
        results.sort(key=lambda m: m.updated_at, reverse=True)
        return results

    # ------------------------------------------------------------------ #
    # Helpers / housekeeping
    # ------------------------------------------------------------------ #
    def _bump_project(self, project_id: str) -> None:
        """Touch a project's ``updated_at`` after its memories change.

        Best-effort: a failure here must not fail the memory write that
        triggered it, so we swallow (and log) problems.
        """
        try:
            path = self._project_file(project_id)
            if not os.path.exists(path):
                return
            project = self._load_project_record(path)
            project.updated_at = time.time()
            self._atomic_write(path, project.to_dict())
        except (HindsightError, OSError) as exc:
            # Best-effort per the docstring: the memory write this follows
            # already succeeded, so a failure here must never surface as a
            # failure of that write.
            logger.warning("Could not bump project %s timestamp: %s", project_id, exc)

    @guard("compute store statistics")
    def stats(self) -> Dict[str, Any]:
        projects = self.list_projects()
        per_project = {}
        total = 0
        for project in projects:
            try:
                count = len(self.list_memories(project.id))
            except NotFoundError:
                count = 0
            per_project[project.id] = count
            total += count
        quarantined = (len(os.listdir(self.quarantine_dir))
                       if os.path.isdir(self.quarantine_dir) else 0)
        return {
            "projects": len(projects),
            "memories": total,
            "per_project": per_project,
            "quarantined": quarantined,
            "root": self.root,
        }
