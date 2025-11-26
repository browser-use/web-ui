"""
Plugin system interface and base classes.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PluginManifest:
    """Plugin metadata."""

    id: str
    name: str
    version: str
    author: str
    description: str
    dependencies: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)

    # Entry points
    controller_actions: list[str] = field(default_factory=list)  # New browser actions
    ui_components: list[str] = field(default_factory=list)  # New UI tabs/components
    event_handlers: dict[str, str] = field(default_factory=dict)  # Event type -> handler method

    # Metadata
    homepage: str | None = None
    license: str | None = None
    min_python_version: str = "3.11"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "dependencies": self.dependencies,
            "permissions": self.permissions,
            "controller_actions": self.controller_actions,
            "ui_components": self.ui_components,
            "event_handlers": self.event_handlers,
            "homepage": self.homepage,
            "license": self.license,
            "min_python_version": self.min_python_version,
        }


class Plugin(ABC):
    """
    Base class for all plugins.

    Plugins can extend functionality by:
    1. Adding new browser actions
    2. Adding UI components
    3. Listening to events
    4. Providing utilities
    """

    def __init__(self, manifest: PluginManifest):
        self.manifest = manifest
        self.enabled = True
        self.config: dict[str, Any] = {}

    @abstractmethod
    async def initialize(self):
        """Initialize the plugin. Called when plugin is loaded."""
        pass

    @abstractmethod
    async def shutdown(self):
        """Clean up resources. Called when plugin is unloaded."""
        pass

    def get_controller_actions(self) -> dict[str, Callable]:
        """
        Return custom browser actions this plugin provides.

        Returns:
            Dict mapping action name to action function
        """
        return {}

    def get_ui_components(self) -> dict[str, Callable]:
        """
        Return UI components this plugin provides.

        Returns:
            Dict mapping component name to Gradio component function
        """
        return {}

    def get_event_handlers(self) -> dict[str, Callable]:
        """
        Return event handlers this plugin provides.

        Returns:
            Dict mapping event type to handler function
        """
        return {}

    def get_config_schema(self) -> dict[str, Any]:
        """
        Return JSON schema for plugin configuration.

        Used to generate configuration UI.
        """
        return {}

    def configure(self, config: dict[str, Any]):
        """
        Configure the plugin with user settings.

        Args:
            config: Configuration dictionary
        """
        self.config = config

    def get_info(self) -> dict[str, Any]:
        """Get plugin information."""
        return {
            "manifest": self.manifest.to_dict(),
            "enabled": self.enabled,
            "config": self.config,
        }


class PluginError(Exception):
    """Base exception for plugin-related errors."""

    pass


class PluginLoadError(PluginError):
    """Raised when a plugin fails to load."""

    pass


class PluginInitError(PluginError):
    """Raised when a plugin fails to initialize."""

    pass


class PluginDependencyError(PluginError):
    """Raised when plugin dependencies are not met."""

    pass
