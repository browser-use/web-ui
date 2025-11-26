"""
MCP Settings Tab Component

Provides UI for editing MCP (Model Context Protocol) server configuration.
"""

import json
import logging
from pathlib import Path

import gradio as gr

from src.web_ui.utils.mcp_config import (
    get_default_mcp_config,
    get_mcp_config_path,
    get_mcp_config_summary,
    load_mcp_config,
    save_mcp_config,
    validate_mcp_config,
)
from src.web_ui.webui.webui_manager import WebuiManager

logger = logging.getLogger(__name__)


def load_mcp_config_ui(custom_path: str | None = None):
    """
    Load MCP configuration for UI display.

    Args:
        custom_path: Optional custom path to load from

    Returns:
        Tuple of (config_json_str, status_message, validation_message)
    """
    try:
        # Determine which path to use
        if custom_path and custom_path.strip():
            config_path = Path(custom_path.strip())
        else:
            config_path = get_mcp_config_path()

        # Load configuration
        config = load_mcp_config(config_path)

        if config is None:
            # File doesn't exist or is invalid, use default
            config = get_default_mcp_config()
            status = (
                f"⚠️ No configuration found at {config_path}. Using default empty configuration."
            )
            validation = "✅ Valid (default configuration)"
        else:
            status = f"✅ Loaded configuration from {config_path}"
            validation = "✅ Valid configuration"

        # Convert to pretty JSON string
        config_json = json.dumps(config, indent=2, ensure_ascii=False)

        return (
            config_json,
            status,
            validation,
            get_mcp_config_summary(config),
        )

    except Exception as e:
        logger.error(f"Error loading MCP configuration: {e}", exc_info=True)
        default_config = get_default_mcp_config()
        return (
            json.dumps(default_config, indent=2),
            f"❌ Error loading configuration: {e}",
            "⚠️ Using default configuration",
            "",
        )


def save_mcp_config_ui(config_text: str, custom_path: str | None = None):
    """
    Save MCP configuration from UI.

    Args:
        config_text: JSON configuration text
        custom_path: Optional custom path to save to

    Returns:
        Tuple of (status_message, validation_message)
    """
    try:
        # Parse JSON
        try:
            config = json.loads(config_text)
        except json.JSONDecodeError as e:
            return (
                f"❌ Invalid JSON: {e}",
                "❌ Cannot save invalid JSON",
                "",
            )

        # Validate configuration
        is_valid, error_msg = validate_mcp_config(config)
        if not is_valid:
            return (
                f"❌ Invalid configuration: {error_msg}",
                "❌ Cannot save invalid configuration",
                "",
            )

        # Determine save path
        if custom_path and custom_path.strip():
            config_path = Path(custom_path.strip())
        else:
            config_path = get_mcp_config_path()

        # Save configuration
        success = save_mcp_config(config, config_path)

        if success:
            return (
                f"✅ Configuration saved to {config_path}",
                "✅ Valid configuration",
                get_mcp_config_summary(config),
            )
        else:
            return (
                f"❌ Failed to save configuration to {config_path}",
                "⚠️ Configuration is valid but save failed",
                "",
            )

    except Exception as e:
        logger.error(f"Error saving MCP configuration: {e}", exc_info=True)
        return (
            f"❌ Error: {e}",
            "❌ Save failed",
            "",
        )


def validate_mcp_config_ui(config_text: str):
    """
    Validate MCP configuration from UI.

    Args:
        config_text: JSON configuration text

    Returns:
        Validation message
    """
    try:
        # Parse JSON
        try:
            config = json.loads(config_text)
        except json.JSONDecodeError as e:
            return (
                f"❌ Invalid JSON: {e}",
                "",
            )

        # Validate configuration
        is_valid, error_msg = validate_mcp_config(config)

        if is_valid:
            return (
                "✅ Valid configuration",
                get_mcp_config_summary(config),
            )
        else:
            return (
                f"❌ Invalid configuration: {error_msg}",
                "",
            )

    except Exception as e:
        logger.error(f"Error validating MCP configuration: {e}", exc_info=True)
        return (
            f"❌ Validation error: {e}",
            "",
        )


def reset_mcp_config_ui():
    """
    Reset MCP configuration to default.

    Returns:
        Tuple of (config_json_str, status_message, validation_message, summary)
    """
    default_config = get_default_mcp_config()
    config_json = json.dumps(default_config, indent=2, ensure_ascii=False)

    return (
        config_json,
        "⚠️ Reset to default configuration (not saved)",
        "✅ Valid (default configuration)",
        get_mcp_config_summary(default_config),
    )


def load_example_config_ui():
    """
    Load example MCP configuration.

    Returns:
        Tuple of (config_json_str, status_message, validation_message, summary)
    """
    try:
        example_path = Path("mcp.example.json")

        if not example_path.exists():
            return (
                gr.update(),  # Don't change editor content
                "❌ mcp.example.json not found",
                "⚠️ Example file not available",
                "",
            )

        with open(example_path, encoding="utf-8") as f:
            config = json.load(f)

        config_json = json.dumps(config, indent=2, ensure_ascii=False)

        return (
            config_json,
            "ℹ️ Loaded example configuration (not saved). Edit and save as needed.",
            "✅ Valid configuration",
            get_mcp_config_summary(config),
        )

    except Exception as e:
        logger.error(f"Error loading example configuration: {e}", exc_info=True)
        return (
            gr.update(),
            f"❌ Error loading example: {e}",
            "",
            "",
        )


def create_mcp_settings_tab(webui_manager: WebuiManager):
    """
    Create the MCP Settings tab for editing MCP server configuration.

    Args:
        webui_manager: WebUI manager instance
    """
    tab_components = {}

    with gr.Column():
        gr.Markdown(
            """
            # MCP Settings

            Configure Model Context Protocol (MCP) servers that provide additional tools and capabilities to agents.

            **Quick Start:**
            1. Click "Load Example Config" to see available MCP servers
            2. Edit the configuration to enable/disable servers
            3. Add API keys where needed (in `env` fields)
            4. Click "Save Configuration"
            5. Restart agents to use new MCP tools
            """
        )

        with gr.Row():
            config_path_input = gr.Textbox(
                label="Configuration File Path",
                value=str(get_mcp_config_path()),
                placeholder="Leave empty for default (./data/mcp.json)",
                scale=3,
            )
            load_button = gr.Button("🔄 Load", scale=1, variant="secondary")

        status_message = gr.Markdown("ℹ️ Ready to load or create configuration")

        mcp_config_editor = gr.Code(
            label="MCP Configuration (JSON)",
            language="json",
            lines=20,
            value="{}",
        )

        validation_message = gr.Markdown("ℹ️ Edit configuration above")

        with gr.Row():
            save_button = gr.Button("💾 Save Configuration", variant="primary", scale=2)
            validate_button = gr.Button("✓ Validate", variant="secondary", scale=1)
            reset_button = gr.Button("↺ Reset to Default", variant="secondary", scale=1)
            example_button = gr.Button("📖 Load Example Config", variant="secondary", scale=2)

        with gr.Accordion("Server Summary", open=False):
            server_summary = gr.Markdown("No servers configured")

        gr.Markdown(
            """
            ---

            ### Common MCP Servers

            - **filesystem**: Access local files and directories
            - **fetch**: Make HTTP requests to external APIs
            - **puppeteer**: Browser automation capabilities
            - **brave-search**: Web search via Brave Search API
            - **github**: GitHub repository operations
            - **postgres/sqlite**: Database operations
            - **memory**: Persistent memory for agents
            - **sequential-thinking**: Enhanced reasoning capabilities

            See `mcp.example.json` for full configuration examples.

            ### Configuration Format

            ```json
            {
              "mcpServers": {
                "server-name": {
                  "command": "npx",
                  "args": ["-y", "@modelcontextprotocol/server-name"],
                  "env": {
                    "API_KEY": "your_key_here"
                  }
                }
              }
            }
            ```

            ⚠️ **Important**: After changing MCP configuration, you must restart agents for changes to take effect.
            Use the "Clear" button in the Browser Use Agent tab to reset the agent.
            """
        )

    # Store components
    tab_components.update(
        {
            "config_path_input": config_path_input,
            "load_button": load_button,
            "save_button": save_button,
            "validate_button": validate_button,
            "reset_button": reset_button,
            "example_button": example_button,
            "mcp_config_editor": mcp_config_editor,
            "status_message": status_message,
            "validation_message": validation_message,
            "server_summary": server_summary,
        }
    )
    webui_manager.add_components("mcp_settings", tab_components)

    # Connect event handlers
    load_button.click(
        fn=load_mcp_config_ui,
        inputs=[config_path_input],
        outputs=[
            mcp_config_editor,
            status_message,
            validation_message,
            server_summary,
        ],
    )

    save_button.click(
        fn=save_mcp_config_ui,
        inputs=[mcp_config_editor, config_path_input],
        outputs=[
            status_message,
            validation_message,
            server_summary,
        ],
    )

    validate_button.click(
        fn=validate_mcp_config_ui,
        inputs=[mcp_config_editor],
        outputs=[
            validation_message,
            server_summary,
        ],
    )

    reset_button.click(
        fn=reset_mcp_config_ui,
        inputs=[],
        outputs=[
            mcp_config_editor,
            status_message,
            validation_message,
            server_summary,
        ],
    )

    example_button.click(
        fn=load_example_config_ui,
        inputs=[],
        outputs=[
            mcp_config_editor,
            status_message,
            validation_message,
            server_summary,
        ],
    )

    # Load configuration on tab creation
    initial_config_json, initial_status, initial_validation, initial_summary = load_mcp_config_ui()
    mcp_config_editor.value = initial_config_json
    status_message.value = initial_status
    validation_message.value = initial_validation
    server_summary.value = initial_summary
