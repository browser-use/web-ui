"""Provider profile store for the Cursor-style API configuration page.

A *profile* binds a provider type (``openai``, ``anthropic``, ...) to the
credentials and model list the user wants to use with it. Profiles are kept in
a single JSON document, written atomically so an interrupted save can never
corrupt the whole config.

The store never prints secrets: :meth:`ProviderStore.list_profiles` masks API
keys by default; the raw key is only handed out through
:meth:`ProviderStore.get_secret` for the code that actually builds a client.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Provider types the WebUI's get_llm_model() factory understands.
SUPPORTED_PROVIDERS = (
    "openai", "azure_openai", "anthropic", "deepseek", "google",
    "mistral", "ollama", "alibaba", "moonshot", "unbound", "siliconflow",
)

DEFAULT_PATH = os.path.join(".", "tmp", "api_config", "providers.json")


class ProviderConfigError(Exception):
    """Raised for any provider-configuration problem (bad input or storage)."""

    def __init__(self, message: str, *, detail: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.detail = detail

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.message} ({self.detail})" if self.detail else self.message


def build_llm_kwargs(profile: "ProviderProfile") -> Dict[str, Any]:
    """kwargs for ``get_llm_model(profile.provider, **kwargs)`` from a profile.

    Keys with no configured value are left out entirely rather than passed as
    ``""``/``None`` — ``get_llm_model`` uses ``kwargs.get(key, <default>)``,
    and an explicit ``""``/``None`` value defeats that default just as much
    as a real one would, instead of letting the factory fall back to its own
    per-provider default model/endpoint.
    """
    kwargs: Dict[str, Any] = {"api_key": profile.api_key, "temperature": 0.0}
    model_name = profile.default_model or (profile.models[0] if profile.models else "")
    if model_name:
        kwargs["model_name"] = model_name
    if profile.base_url:
        kwargs["base_url"] = profile.base_url
    return kwargs


def _mask(secret: str) -> str:
    if not secret:
        return ""
    if len(secret) <= 8:
        return "•" * len(secret)
    return f"{secret[:4]}{'•' * 6}{secret[-4:]}"


@dataclass
class ProviderProfile:
    """One configured API provider."""

    label: str
    provider: str
    api_key: str = ""
    base_url: str = ""
    models: List[str] = field(default_factory=list)
    default_model: str = ""
    enabled: bool = True
    id: str = field(default_factory=lambda: f"prov_{uuid.uuid4().hex[:12]}")
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if not isinstance(self.label, str) or not self.label.strip():
            raise ProviderConfigError("profile label must not be empty")
        if self.provider not in SUPPORTED_PROVIDERS:
            raise ProviderConfigError(
                "unsupported provider type",
                detail=f"{self.provider!r}; expected one of {', '.join(SUPPORTED_PROVIDERS)}")
        # A malformed scalar here (e.g. a persisted record with api_key as a
        # number) would otherwise only surface later as a crash in _mask()
        # or the UI, well past the point where _load() could quarantine it.
        for field_name in ("api_key", "base_url", "default_model"):
            if not isinstance(getattr(self, field_name), str):
                raise ProviderConfigError(f"'{field_name}' must be a string",
                                          detail=f"got {type(getattr(self, field_name)).__name__}")
        if not isinstance(self.models, list) or any(not isinstance(m, str) for m in self.models):
            raise ProviderConfigError("models must be a list of strings")
        self.models = [m.strip() for m in self.models if m and m.strip()]
        if self.default_model and self.default_model not in self.models:
            # Keep the default consistent rather than rejecting outright.
            self.models.insert(0, self.default_model)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_public_dict(self) -> Dict[str, Any]:
        """A copy safe to display: the API key is masked."""
        data = self.to_dict()
        data["api_key"] = _mask(self.api_key)
        data["has_key"] = bool(self.api_key)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProviderProfile":
        if not isinstance(data, dict):
            raise ProviderConfigError("provider record must be an object")
        try:
            return cls(
                label=data["label"],
                provider=data["provider"],
                api_key=data.get("api_key", ""),
                base_url=data.get("base_url", ""),
                models=list(data.get("models", [])),
                default_model=data.get("default_model", ""),
                enabled=bool(data.get("enabled", True)),
                id=data.get("id") or f"prov_{uuid.uuid4().hex[:12]}",
                created_at=float(data.get("created_at", time.time())),
                updated_at=float(data.get("updated_at", time.time())),
            )
        except KeyError as exc:
            raise ProviderConfigError("provider record missing a required field",
                                      detail=str(exc)) from exc
        except (TypeError, ValueError) as exc:
            raise ProviderConfigError("provider record has an invalid field",
                                      detail=str(exc)) from exc


class ProviderStore:
    """Thread-safe JSON-backed collection of :class:`ProviderProfile`."""

    def __init__(self, path: str = DEFAULT_PATH):
        self.path = os.path.abspath(path)
        self._lock = threading.RLock()
        self._profiles: Dict[str, ProviderProfile] = {}
        self._load()

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #
    def _load(self) -> None:
        with self._lock:
            self._profiles = {}
            if not os.path.exists(self.path):
                return
            try:
                with open(self.path, "r", encoding="utf-8") as fh:
                    raw = json.load(fh)
            except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
                # Corrupt config: back it up instead of losing it, start clean.
                # A random suffix (not just the timestamp) keeps two
                # recoveries within the same second from overwriting each
                # other's backup.
                backup = f"{self.path}.corrupt-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
                try:
                    os.replace(self.path, backup)
                    logger.error("Provider config unreadable, backed up to %s: %s",
                                 backup, exc)
                except OSError:
                    logger.error("Provider config unreadable and un-backupable: %s", exc)
                return
            if not isinstance(raw, dict) or not isinstance(raw.get("providers", []), list):
                # Syntactically valid JSON (so the except above never ran)
                # but not shaped like our document — e.g. a bare array or a
                # `"providers"` that isn't a list. Treat it exactly like a
                # corrupt file: back it up and start clean rather than
                # crashing the whole store.
                # A random suffix (not just the timestamp) keeps two
                # recoveries within the same second from overwriting each
                # other's backup.
                backup = f"{self.path}.corrupt-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
                try:
                    os.replace(self.path, backup)
                    logger.error("Provider config has an unexpected shape, backed up to %s",
                                 backup)
                except OSError as exc:
                    logger.error("Provider config has an unexpected shape and could not "
                                 "be backed up: %s", exc)
                return
            for record in raw.get("providers", []):
                try:
                    profile = ProviderProfile.from_dict(record)
                    self._profiles[profile.id] = profile
                except ProviderConfigError as exc:
                    logger.warning("Skipping invalid provider record: %s", exc)

    def _save(self) -> None:
        directory = os.path.dirname(self.path)
        payload = {"version": 1,
                   "providers": [p.to_dict() for p in self._profiles.values()]}
        try:
            os.makedirs(directory, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=directory, suffix=".tmp")
        except OSError as exc:
            # Setup failures (can't create the directory / can't open a temp
            # file) used to raise a bare OSError here, bypassing the
            # ProviderConfigError hierarchy callers and the UI actually
            # handle.
            raise ProviderConfigError("could not prepare provider config storage",
                                      detail=str(exc)) from exc
        try:
            # API keys are stored in this JSON document in the clear (no OS
            # keyring integration — out of scope for this store), so at
            # least restrict it to the owner. Best-effort: unsupported (e.g.
            # Windows) or failing chmod must not block the save itself.
            try:
                os.chmod(tmp, 0o600)
            except OSError:
                pass
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, self.path)
            try:
                os.chmod(self.path, 0o600)
            except OSError:
                pass
        except OSError as exc:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise ProviderConfigError("could not save provider config",
                                      detail=str(exc)) from exc

    # ------------------------------------------------------------------ #
    # CRUD
    # ------------------------------------------------------------------ #
    def add_profile(self, label: str, provider: str, api_key: str = "",
                    base_url: str = "", models: Optional[List[str]] = None,
                    default_model: str = "", enabled: bool = True) -> ProviderProfile:
        with self._lock:
            if any(p.label == label.strip() for p in self._profiles.values()):
                raise ProviderConfigError("a profile with this label already exists",
                                          detail=label)
            profile = ProviderProfile(
                label=label.strip(), provider=provider, api_key=api_key.strip(),
                base_url=base_url.strip(), models=models or [],
                default_model=default_model.strip(), enabled=enabled)
            self._profiles[profile.id] = profile
            try:
                self._save()
            except ProviderConfigError:
                # Keep the in-memory store consistent with what's actually on
                # disk: a caller that saw this error and retries (or just
                # lists profiles) must not see a profile that was never
                # durably saved.
                del self._profiles[profile.id]
                raise
            return profile

    def get_profile(self, profile_id: str) -> ProviderProfile:
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                raise ProviderConfigError("profile not found", detail=profile_id)
            return profile

    def list_profiles(self, *, public: bool = True) -> List[Dict[str, Any]]:
        with self._lock:
            profiles = sorted(self._profiles.values(), key=lambda p: p.updated_at,
                              reverse=True)
            return [p.to_public_dict() if public else p.to_dict() for p in profiles]

    def update_profile(self, profile_id: str, **changes: Any) -> ProviderProfile:
        with self._lock:
            profile = self.get_profile(profile_id)
            data = profile.to_dict()
            for key, value in changes.items():
                if value is None or key in ("id", "created_at"):
                    continue
                # An empty api_key in an update means "leave the key unchanged".
                if key == "api_key" and value == "":
                    continue
                data[key] = value
            new_label = (data.get("label") or "").strip()
            if any(pid != profile_id and p.label == new_label
                  for pid, p in self._profiles.items()):
                raise ProviderConfigError("a profile with this label already exists",
                                          detail=new_label)
            data["updated_at"] = time.time()
            updated = ProviderProfile.from_dict(data)  # re-validate
            self._profiles[profile_id] = updated
            try:
                self._save()
            except ProviderConfigError:
                self._profiles[profile_id] = profile  # roll back to the pre-update record
                raise
            return updated

    def delete_profile(self, profile_id: str) -> None:
        with self._lock:
            if profile_id not in self._profiles:
                raise ProviderConfigError("profile not found", detail=profile_id)
            removed = self._profiles.pop(profile_id)
            try:
                self._save()
            except ProviderConfigError:
                self._profiles[profile_id] = removed  # roll back the delete
                raise

    def get_secret(self, profile_id: str) -> str:
        """Return the raw (unmasked) API key — for client construction only."""
        return self.get_profile(profile_id).api_key

    # ------------------------------------------------------------------ #
    # Connectivity check
    # ------------------------------------------------------------------ #
    def test_profile(self, profile_id: str, *, live: bool = False) -> Dict[str, Any]:
        """Validate a profile.

        ``live=False`` (default) only builds the LangChain client object, which
        makes no network call — it catches missing keys / bad config safely.
        ``live=True`` additionally sends a 1-token ping; any network/auth error
        is reported, never raised.
        """
        profile = self.get_profile(profile_id)
        try:
            from src.utils import llm_provider  # local import to avoid a heavy import cycle
            llm = llm_provider.get_llm_model(profile.provider, **build_llm_kwargs(profile))
        except Exception as exc:  # noqa: BLE001 - surface as structured result
            return {"ok": False, "stage": "build", "error": str(exc)}

        if not live:
            return {"ok": True, "stage": "build",
                    "message": "client constructed successfully (no network call made)"}

        try:
            llm.invoke("ping")
            return {"ok": True, "stage": "live", "message": "live call succeeded"}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "stage": "live", "error": str(exc)}
