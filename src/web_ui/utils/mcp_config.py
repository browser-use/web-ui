"""
MCP Configuration Manager

Handles loading, saving, and validating MCP (Model Context Protocol) server configurations.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default MCP configuration file location
DEFAULT_MCP_CONFIG_PATH = Path("./data/mcp.json")


def get_mcp_config_path() -> Path:
    """
    Get the MCP configuration file path.

    Priority:
    1. MCP_CONFIG_PATH environment variable
    2. ./data/mcp.json in data directory

    Returns:
        Path to the MCP configuration file
    """
    custom_path = os.getenv("MCP_CONFIG_PATH")
    if custom_path:
        return Path(custom_path)
    return DEFAULT_MCP_CONFIG_PATH


def validate_mcp_config(config: dict[str, Any]) -> tuple[bool, str | None]:
    """
    Validate MCP configuration structure.

    Args:
        config: MCP configuration dictionary

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(config, dict):
        return False, "Configuration must be a dictionary"

    # Check if config has mcpServers key or is already in the correct format
    if "mcpServers" in config:
        servers = config["mcpServers"]
    else:
        servers = config

    if not isinstance(servers, dict):
        return False, "MCP servers configuration must be a dictionary"

    # Validate each server configuration
    for server_name, server_config in servers.items():
        if not isinstance(server_config, dict):
            return False, f"Server '{server_name}' configuration must be a dictionary"

        # Check for required fields
        if "command" not in server_config:
            return False, f"Server '{server_name}' must have a 'command' field"

        # Validate command is a string
        if not isinstance(server_config["command"], str):
            return False, f"Server '{server_name}' command must be a string"

        # Validate args if present
        if "args" in server_config:
            if not isinstance(server_config["args"], list):
                return False, f"Server '{server_name}' args must be a list"

            # All args should be strings
            for i, arg in enumerate(server_config["args"]):
                if not isinstance(arg, str):
                    return False, f"Server '{server_name}' args[{i}] must be a string"

        # Validate env if present
        if "env" in server_config:
            if not isinstance(server_config["env"], dict):
                return False, f"Server '{server_name}' env must be a dictionary"

            # All env values should be strings
            for key, value in server_config["env"].items():
                if not isinstance(value, str):
                    return False, f"Server '{server_name}' env['{key}'] must be a string"

    return True, None


def load_mcp_config(config_path: Path | None = None) -> dict[str, Any] | None:
    """
    Load MCP configuration from file.

    Args:
        config_path: Optional path to configuration file. If None, uses default path.

    Returns:
        MCP configuration dictionary or None if file doesn't exist or is invalid
    """
    if config_path is None:
        config_path = get_mcp_config_path()

    if not config_path.exists():
        logger.info(f"MCP configuration file not found at {config_path}")
        return None

    try:
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)

        # Validate configuration
        is_valid, error_msg = validate_mcp_config(config)
        if not is_valid:
            logger.error(f"Invalid MCP configuration: {error_msg}")
            return None

        logger.info(f"Successfully loaded MCP configuration from {config_path}")
        return config

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse MCP configuration JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to load MCP configuration: {e}", exc_info=True)
        return None


def save_mcp_config(config: dict[str, Any], config_path: Path | None = None) -> bool:
    """
    Save MCP configuration to file.

    Args:
        config: MCP configuration dictionary
        config_path: Optional path to configuration file. If None, uses default path.

    Returns:
        True if saved successfully, False otherwise
    """
    if config_path is None:
        config_path = get_mcp_config_path()

    # Validate before saving
    is_valid, error_msg = validate_mcp_config(config)
    if not is_valid:
        logger.error(f"Cannot save invalid MCP configuration: {error_msg}")
        return False

    try:
        # Create parent directories if they don't exist
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Save with pretty printing
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        logger.info(f"Successfully saved MCP configuration to {config_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to save MCP configuration: {e}", exc_info=True)
        return False


def get_default_mcp_config() -> dict[str, Any]:
    """
    Get default/empty MCP configuration structure.

    Returns:
        Default MCP configuration dictionary
    """
    return {"mcpServers": {}}


def merge_mcp_configs(
    base_config: dict[str, Any], override_config: dict[str, Any]
) -> dict[str, Any]:
    """
    Merge two MCP configurations, with override_config taking precedence.

    Args:
        base_config: Base configuration
        override_config: Configuration to override base with

    Returns:
        Merged configuration
    """
    # Extract server configs
    base_servers = base_config.get(
        "mcpServers", base_config if isinstance(base_config, dict) else {}
    )
    override_servers = override_config.get(
        "mcpServers", override_config if isinstance(override_config, dict) else {}
    )

    # Merge servers
    merged_servers = {**base_servers, **override_servers}

    return {"mcpServers": merged_servers}


def get_mcp_server_names(config: dict[str, Any]) -> list[str]:
    """
    Get list of MCP server names from configuration.

    Args:
        config: MCP configuration dictionary

    Returns:
        List of server names
    """
    if "mcpServers" in config:
        return list(config["mcpServers"].keys())
    return list(config.keys())


def get_mcp_config_summary(config: dict[str, Any]) -> str:
    """
    Get a human-readable summary of MCP configuration.

    Args:
        config: MCP configuration dictionary

    Returns:
        Summary string
    """
    server_names = get_mcp_server_names(config)

    if not server_names:
        return "No MCP servers configured"

    summary = f"MCP Servers ({len(server_names)}):\n"
    for name in server_names:
        servers = config.get("mcpServers", config)
        server_config = servers[name]
        command = server_config.get("command", "unknown")
        summary += f"  - {name}: {command}\n"

    return summary.strip()
