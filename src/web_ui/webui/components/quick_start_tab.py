"""
Quick Start Tab Component

Provides a landing page with preset configurations, status display, and quick actions.
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
        "description": "Optimized for deep research tasks with comprehensive analysis",
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
        "description": "Fast and efficient for browser automation tasks",
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
        "name": "🌐 Custom Browser Mode",
        "description": "Use your own Chrome profile for authenticated sessions",
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


def get_current_config_status() -> str:
    """
    Get current configuration status from environment.

    Returns:
        Markdown string with configuration status
    """
    try:
        # Check LLM configuration
        default_llm = os.getenv("DEFAULT_LLM", "openai")
        api_key_var = f"{default_llm.upper()}_API_KEY"
        api_key_set = bool(os.getenv(api_key_var))

        llm_status = "✅ Configured" if api_key_set else "⚠️ No API key"
        llm_display = default_llm.title()

        # Check MCP configuration
        get_mcp_config_path()  # Check if config exists
        mcp_config = load_mcp_config()
        if mcp_config and "mcpServers" in mcp_config:
            mcp_count = len(mcp_config["mcpServers"])
            mcp_status = f"✅ {mcp_count} server(s) configured"
        else:
            mcp_status = "ℹ️ Not configured (optional)"

        # Check browser configuration
        use_own_browser = os.getenv("USE_OWN_BROWSER", "false").lower() == "true"
        browser_status = "Custom Chrome" if use_own_browser else "Default Playwright"

        status_md = f"""
**Current Configuration:**

- **LLM Provider:** {llm_display} {llm_status}
- **Browser:** {browser_status}
- **MCP Servers:** {mcp_status}

💡 **Tip:** Use preset configurations below to quickly set up common scenarios, or configure settings manually in the Settings tab.
"""
        return status_md

    except Exception as e:
        logger.error(f"Error getting config status: {e}", exc_info=True)
        return """
**Current Configuration:**

⚠️ Error reading configuration. Please check your .env file.
"""


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
        "llm_provider": "agent_settings.llm_provider",
        "llm_model_name": "agent_settings.llm_model_name",
        "llm_temperature": "agent_settings.llm_temperature",
        "use_vision": "agent_settings.use_vision",
        "max_steps": "agent_settings.max_steps",
        "max_actions": "agent_settings.max_actions",
        "headless": "browser_settings.headless",
        "keep_browser_open": "browser_settings.keep_browser_open",
        "use_own_browser": "browser_settings.use_own_browser",
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


def create_quick_start_tab(webui_manager: WebuiManager):
    """
    Creates a Quick Start tab with status display and preset configurations.

    Args:
        webui_manager: WebUI manager instance
    """
    tab_components = {}

    # Header
    gr.Markdown(
        """
        ## 🚀 Welcome to Browser Use WebUI
        Get started quickly with preset configurations or jump directly to your desired section.
        """,
        elem_classes=["tab-header-text"],
    )

    with gr.Row():
        # Left column: Quick Actions
        with gr.Column(scale=1):
            gr.Markdown("### 📋 Quick Actions")

            with gr.Group():
                gr.Markdown("**Preset Configurations**")
                gr.Markdown(
                    "Load optimized settings for common use cases. These will populate the Settings tab."
                )

                research_btn = gr.Button(
                    "🔬 Load Research Mode",
                    variant="primary",
                    size="lg",
                )
                gr.Markdown(
                    "_Optimized for deep research with Claude Sonnet_",
                    elem_classes=["preset-description"],
                )

                automation_btn = gr.Button(
                    "🤖 Load Automation Mode",
                    variant="secondary",
                    size="lg",
                )
                gr.Markdown(
                    "_Fast automation with GPT-4o_",
                    elem_classes=["preset-description"],
                )

                custom_browser_btn = gr.Button(
                    "🌐 Load Custom Browser Mode",
                    variant="secondary",
                    size="lg",
                )
                gr.Markdown(
                    "_Use your Chrome profile for authenticated tasks_",
                    elem_classes=["preset-description"],
                )

            preset_status = gr.Markdown(
                "",
                visible=False,
                elem_classes=["preset-status"],
            )

        # Right column: Status and Info
        with gr.Column(scale=2):
            gr.Markdown("### ℹ️ Configuration Status")

            status_display = gr.Markdown(
                get_current_config_status(),
                elem_classes=["status-display"],
            )

            refresh_status_btn = gr.Button(
                "🔄 Refresh Status",
                size="sm",
                variant="secondary",
            )

            gr.Markdown("### 🎯 Common Use Cases")

            with gr.Row():
                with gr.Column():
                    gr.Markdown(
                        """
                    **🔍 Web Research**
                    - Use Deep Research agent in Agent Marketplace
                    - Enable MCP servers for extended capabilities
                    - Recommended: GPT-4 or Claude Sonnet
                    - Higher temperature (0.7-0.8) for creativity
                    """
                    )
                with gr.Column():
                    gr.Markdown(
                        """
                    **🤖 Browser Automation**
                    - Use standard Run Agent tab
                    - Configure custom browser if accessing authenticated sites
                    - Enable vision for better element detection
                    - Lower temperature (0.5-0.6) for consistency
                    """
                    )

            gr.Markdown("### 📚 Getting Started Guide")
            with gr.Accordion("📖 Quick Setup Instructions", open=False):
                gr.Markdown(
                    """
                #### First Time Setup:

                1. **Configure API Keys** (if not in .env)
                   - Go to Settings > Agent Settings
                   - Select your LLM provider
                   - Add API key if needed

                2. **Choose Your Mode**
                   - Click a preset button above to auto-configure
                   - OR manually configure in Settings tab

                3. **Run Your First Task**
                   - Go to "Run Agent" tab
                   - Enter your task description
                   - Click "Run Agent" and watch the magic happen!

                #### Tips:

                - **Vision Mode**: Enable for better screenshot understanding
                - **Custom Browser**: Use your Chrome profile to access logged-in sites
                - **MCP Servers**: Add filesystem, fetch, or brave-search for extended capabilities
                - **Max Steps**: Increase for complex multi-step tasks
                - **Save Configs**: Use "Config Management" tab to save your favorite setups
                """
                )

    # Register components
    tab_components.update(
        {
            "research_btn": research_btn,
            "automation_btn": automation_btn,
            "custom_browser_btn": custom_browser_btn,
            "preset_status": preset_status,
            "status_display": status_display,
            "refresh_status_btn": refresh_status_btn,
        }
    )

    webui_manager.add_components("quick_start", tab_components)

    # Connect preset buttons
    def load_research_preset():
        """Load research preset configuration."""
        updates = load_preset_config("research", webui_manager)
        status_msg = """
✅ **Research Mode Loaded!**

Settings applied:
- LLM: Claude 3.5 Sonnet
- Temperature: 0.7 (creative)
- Vision: Enabled
- Max Steps: 150

Go to the **Settings** tab to review or adjust these settings.
"""
        return [gr.update(value=val) for _, val in updates] + [
            gr.update(value=status_msg, visible=True)
        ]

    def load_automation_preset():
        """Load automation preset configuration."""
        updates = load_preset_config("automation", webui_manager)
        status_msg = """
✅ **Automation Mode Loaded!**

Settings applied:
- LLM: GPT-4o
- Temperature: 0.6 (balanced)
- Vision: Enabled
- Max Steps: 100

Go to the **Settings** tab to review or adjust these settings.
"""
        return [gr.update(value=val) for _, val in updates] + [
            gr.update(value=status_msg, visible=True)
        ]

    def load_custom_browser_preset():
        """Load custom browser preset configuration."""
        updates = load_preset_config("custom_browser", webui_manager)
        status_msg = """
✅ **Custom Browser Mode Loaded!**

Settings applied:
- LLM: GPT-4o Mini (cost-effective)
- Use Own Browser: Enabled
- Vision: Enabled

⚠️ **Important:** Close all Chrome windows before running the agent!

Configure your Chrome path in the **Settings > Browser Settings** tab.
"""
        return [gr.update(value=val) for _, val in updates] + [
            gr.update(value=status_msg, visible=True)
        ]

    def refresh_status():
        """Refresh the status display."""
        return gr.update(value=get_current_config_status())

    # Wire up button clicks
    research_btn.click(
        fn=load_research_preset,
        inputs=[],
        outputs=[
            webui_manager.get_component_by_id("agent_settings.llm_provider"),
            webui_manager.get_component_by_id("agent_settings.llm_model_name"),
            webui_manager.get_component_by_id("agent_settings.llm_temperature"),
            webui_manager.get_component_by_id("agent_settings.use_vision"),
            webui_manager.get_component_by_id("agent_settings.max_steps"),
            webui_manager.get_component_by_id("agent_settings.max_actions"),
            webui_manager.get_component_by_id("browser_settings.headless"),
            webui_manager.get_component_by_id("browser_settings.keep_browser_open"),
            preset_status,
        ],
    )

    automation_btn.click(
        fn=load_automation_preset,
        inputs=[],
        outputs=[
            webui_manager.get_component_by_id("agent_settings.llm_provider"),
            webui_manager.get_component_by_id("agent_settings.llm_model_name"),
            webui_manager.get_component_by_id("agent_settings.llm_temperature"),
            webui_manager.get_component_by_id("agent_settings.use_vision"),
            webui_manager.get_component_by_id("agent_settings.max_steps"),
            webui_manager.get_component_by_id("agent_settings.max_actions"),
            webui_manager.get_component_by_id("browser_settings.headless"),
            webui_manager.get_component_by_id("browser_settings.keep_browser_open"),
            preset_status,
        ],
    )

    custom_browser_btn.click(
        fn=load_custom_browser_preset,
        inputs=[],
        outputs=[
            webui_manager.get_component_by_id("agent_settings.llm_provider"),
            webui_manager.get_component_by_id("agent_settings.llm_model_name"),
            webui_manager.get_component_by_id("agent_settings.llm_temperature"),
            webui_manager.get_component_by_id("agent_settings.use_vision"),
            webui_manager.get_component_by_id("agent_settings.max_steps"),
            webui_manager.get_component_by_id("agent_settings.max_actions"),
            webui_manager.get_component_by_id("browser_settings.headless"),
            webui_manager.get_component_by_id("browser_settings.keep_browser_open"),
            webui_manager.get_component_by_id("browser_settings.use_own_browser"),
            preset_status,
        ],
    )

    refresh_status_btn.click(
        fn=refresh_status,
        inputs=[],
        outputs=[status_display],
    )
