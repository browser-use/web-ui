"""
Dashboard Sidebar Component

Provides status display, quick presets, task history, browser status, and token usage.
"""

import logging
import os

import gradio as gr

from src.web_ui.utils.mcp_config import get_mcp_config_path, load_mcp_config
from src.web_ui.webui.webui_manager import WebuiManager

logger = logging.getLogger(__name__)

# Preset configurations
PRESETS = {
    "research": {
        "name": "🔬 Research Mode",
        "config": {
            "llm_provider": "anthropic",
            "llm_model_name": "claude-3-5-sonnet-20241022",
            "llm_temperature": 0.7,
            "use_vision": True,
            "max_steps": 150,
            "max_actions": 10,
            "headless": False,
            "keep_browser_open": True,
        },
    },
    "automation": {
        "name": "🤖 Automation Mode",
        "config": {
            "llm_provider": "openai",
            "llm_model_name": "gpt-4o",
            "llm_temperature": 0.6,
            "use_vision": True,
            "max_steps": 100,
            "max_actions": 10,
            "headless": False,
            "keep_browser_open": True,
        },
    },
    "custom_browser": {
        "name": "🌐 Custom Browser",
        "config": {
            "llm_provider": "openai",
            "llm_model_name": "gpt-4o-mini",
            "llm_temperature": 0.6,
            "use_vision": True,
            "max_steps": 100,
            "max_actions": 10,
            "use_own_browser": True,
            "keep_browser_open": True,
            "headless": False,
        },
    },
}


def get_status_summary(webui_manager: WebuiManager) -> dict:
    """
    Get current status of LLM, Browser, and MCP configuration.

    Returns:
        dict with status information
    """
    status = {
        "llm": {"configured": False, "provider": None, "status_text": "⚠️ Not configured"},
        "browser": {"open": False, "status_text": "🔴 Closed"},
        "mcp": {"configured": False, "count": 0, "status_text": "ℹ️ Not configured"},
        "tokens": {"used": 0, "cost": 0.0},
    }

    # Check LLM configuration
    try:
        default_llm = os.getenv("DEFAULT_LLM", "openai")
        api_key_var = f"{default_llm.upper()}_API_KEY"
        api_key_set = bool(os.getenv(api_key_var))

        if api_key_set:
            status["llm"]["configured"] = True
            status["llm"]["provider"] = default_llm.title()
            status["llm"]["status_text"] = f"✅ {default_llm.title()}"
        else:
            status["llm"]["status_text"] = f"⚠️ {default_llm.title()} (no API key)"
    except Exception as e:
        logger.error(f"Error checking LLM status: {e}")

    # Check Browser status
    try:
        if hasattr(webui_manager, "bu_browser") and webui_manager.bu_browser:
            status["browser"]["open"] = True
            status["browser"]["status_text"] = "🟢 Open"
        else:
            status["browser"]["status_text"] = "🔴 Closed"
    except Exception as e:
        logger.error(f"Error checking browser status: {e}")

    # Check MCP configuration
    try:
        get_mcp_config_path()  # Check if config exists
        mcp_config = load_mcp_config()
        if mcp_config and "mcpServers" in mcp_config:
            mcp_count = len(mcp_config["mcpServers"])
            status["mcp"]["configured"] = True
            status["mcp"]["count"] = mcp_count
            status["mcp"]["status_text"] = f"✅ {mcp_count} server(s)"
        else:
            status["mcp"]["status_text"] = "ℹ️ Not configured"
    except Exception as e:
        logger.error(f"Error checking MCP status: {e}")

    # Get token usage if available
    if hasattr(webui_manager, "token_usage") and webui_manager.token_usage:
        status["tokens"] = webui_manager.token_usage

    return status


def format_status_card(webui_manager: WebuiManager) -> str:
    """Format status information as HTML card."""
    status = get_status_summary(webui_manager)

    html = """
    <div class="status-card">
        <h3 style="margin-top: 0; font-size: 1.1em; margin-bottom: 12px;">📊 Status</h3>
        <div style="display: flex; flex-direction: column; gap: 8px;">
            <div style="display: flex; align-items: center;">
                <strong style="width: 80px;">LLM:</strong>
                <span>{llm_status}</span>
            </div>
            <div style="display: flex; align-items: center;">
                <strong style="width: 80px;">Browser:</strong>
                <span>{browser_status}</span>
            </div>
            <div style="display: flex; align-items: center;">
                <strong style="width: 80px;">MCP:</strong>
                <span>{mcp_status}</span>
            </div>
        </div>
    </div>
    """.format(
        llm_status=status["llm"]["status_text"],
        browser_status=status["browser"]["status_text"],
        mcp_status=status["mcp"]["status_text"],
    )

    return html


def format_history_list(webui_manager: WebuiManager) -> str:
    """Format recent task history as HTML."""
    if not hasattr(webui_manager, "recent_tasks") or not webui_manager.recent_tasks:
        return """
        <div class="status-card">
            <h3 style="margin-top: 0; font-size: 1.1em; margin-bottom: 12px;">📜 Recent Tasks</h3>
            <p style="color: rgba(128, 128, 128, 0.7); font-size: 0.9em;">No recent tasks</p>
        </div>
        """

    items = []
    for task in webui_manager.recent_tasks[-5:]:  # Last 5 tasks
        task_text = task.get("task", "Unknown task")
        timestamp = task.get("timestamp", "")
        status_icon = "✅" if task.get("success", False) else "❌"

        # Truncate long task descriptions
        if len(task_text) > 50:
            task_text = task_text[:47] + "..."

        items.append(
            f"""
            <div class="history-item" title="{task.get("task", "")}">
                {status_icon} <span style="font-size: 0.85em; opacity: 0.7;">{timestamp}</span><br/>
                <span style="font-size: 0.9em;">{task_text}</span>
            </div>
        """
        )

    html = f"""
    <div class="status-card">
        <h3 style="margin-top: 0; font-size: 1.1em; margin-bottom: 12px;">📜 Recent Tasks</h3>
        <div class="history-list">
            {"".join(reversed(items))}
        </div>
    </div>
    """

    return html


def format_token_usage(webui_manager: WebuiManager) -> str:
    """Format token usage information as HTML."""
    if not hasattr(webui_manager, "token_usage") or not webui_manager.token_usage:
        return ""

    tokens = webui_manager.token_usage
    used = tokens.get("used", 0)
    cost = tokens.get("cost", 0.0)

    html = f"""
    <div class="status-card">
        <h3 style="margin-top: 0; font-size: 1.1em; margin-bottom: 12px;">💰 Usage</h3>
        <div style="display: flex; flex-direction: column; gap: 6px;">
            <div>
                <strong>Tokens:</strong> {used:,}
            </div>
            <div>
                <strong>Est. Cost:</strong> ${cost:.4f}
            </div>
        </div>
    </div>
    """

    return html


def load_preset_config(preset_name: str, webui_manager: WebuiManager):
    """
    Load a preset configuration and return component updates.

    Args:
        preset_name: Name of the preset to load
        webui_manager: WebUI manager instance

    Returns:
        List of gr.update() objects for each component
    """
    if preset_name not in PRESETS:
        logger.warning(f"Unknown preset: {preset_name}")
        return []

    preset = PRESETS[preset_name]
    preset_config = preset["config"]

    # Map preset values to component IDs and create updates
    updates = []

    # Get all components that need updating
    component_mapping = {
        "llm_provider": "dashboard_settings.llm_provider",
        "llm_model_name": "dashboard_settings.llm_model_name",
        "llm_temperature": "dashboard_settings.llm_temperature",
        "use_vision": "dashboard_settings.use_vision",
        "max_steps": "dashboard_settings.max_steps",
        "max_actions": "dashboard_settings.max_actions",
        "headless": "dashboard_settings.headless",
        "keep_browser_open": "dashboard_settings.keep_browser_open",
        "use_own_browser": "dashboard_settings.use_own_browser",
    }

    for config_key, component_id in component_mapping.items():
        if config_key in preset_config:
            try:
                component = webui_manager.get_component_by_id(component_id)
                if isinstance(preset_config, dict):
                    updates.append((component, preset_config[config_key]))
            except KeyError:
                logger.debug(f"Component not found: {component_id}")
                continue

    return updates


def create_dashboard_sidebar(webui_manager: WebuiManager):
    """
    Create the dashboard sidebar with status, presets, and history.

    Args:
        webui_manager: WebUI manager instance
    """
    sidebar_components = {}

    with gr.Column(elem_classes=["dashboard-sidebar"]):
        # Status Card
        status_display = gr.HTML(
            value=format_status_card(webui_manager),
            elem_classes=["status-display"],
        )

        refresh_status_btn = gr.Button(
            "🔄 Refresh",
            size="sm",
            variant="secondary",
            scale=1,
        )

        # Preset Buttons
        gr.HTML("<h3 style='margin: 16px 0 8px 0; font-size: 1.1em;'>🎯 Quick Presets</h3>")

        with gr.Column(elem_classes=["preset-button-group"]):
            research_btn = gr.Button(
                "🔬 Research Mode",
                variant="secondary",
                size="lg",
                elem_classes=["preset-button"],
            )
            automation_btn = gr.Button(
                "🤖 Automation Mode",
                variant="secondary",
                size="lg",
                elem_classes=["preset-button"],
            )
            custom_browser_btn = gr.Button(
                "🌐 Custom Browser",
                variant="secondary",
                size="lg",
                elem_classes=["preset-button"],
            )

        # Task History
        history_display = gr.HTML(
            value=format_history_list(webui_manager),
            elem_classes=["history-display"],
        )

        # Token Usage (optional, only shown if data available)
        token_display = gr.HTML(
            value=format_token_usage(webui_manager),
            visible=bool(hasattr(webui_manager, "token_usage") and webui_manager.token_usage),
            elem_classes=["token-display"],
        )

    # Register components
    sidebar_components.update(
        {
            "status_display": status_display,
            "refresh_status_btn": refresh_status_btn,
            "research_btn": research_btn,
            "automation_btn": automation_btn,
            "custom_browser_btn": custom_browser_btn,
            "history_display": history_display,
            "token_display": token_display,
        }
    )

    webui_manager.add_components("dashboard_sidebar", sidebar_components)

    # Wire up refresh button
    def refresh_status():
        """Refresh all status displays."""
        return [
            gr.update(value=format_status_card(webui_manager)),
            gr.update(value=format_history_list(webui_manager)),
            gr.update(value=format_token_usage(webui_manager)),
        ]

    refresh_status_btn.click(
        fn=refresh_status,
        inputs=[],
        outputs=[status_display, history_display, token_display],
    )

    # Note: Preset button handlers will be wired up after dashboard_settings is created
    # This is done in interface.py to ensure settings components exist first

    return sidebar_components
