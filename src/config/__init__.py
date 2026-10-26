"""API configuration layer for the WebUI.

Provides a Cursor-style "providers" store: the user defines one or more API
provider profiles (OpenAI, Anthropic, Ollama, a custom OpenAI-compatible
endpoint, ...), each with its own key, base URL and model list. The store is
local JSON, written atomically, and validated on the way in and out.
"""

from .provider_store import (
    ProviderStore,
    ProviderProfile,
    ProviderConfigError,
    SUPPORTED_PROVIDERS,
)

__all__ = [
    "ProviderStore",
    "ProviderProfile",
    "ProviderConfigError",
    "SUPPORTED_PROVIDERS",
]
