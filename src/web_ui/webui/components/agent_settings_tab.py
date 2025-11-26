import json
import logging
import os

import gradio as gr

from src.web_ui.utils import config
from src.web_ui.utils.mcp_config import get_mcp_config_path, get_mcp_config_summary, load_mcp_config
from src.web_ui.webui.webui_manager import WebuiManager

logger = logging.getLogger(__name__)


def update_model_dropdown(llm_provider):
    """
    Update the model name dropdown with predefined models for the selected provider.
    """
    # Use predefined models for the selected provider
    if llm_provider in config.model_names:
        models = config.model_names[llm_provider]
        return gr.update(
            choices=models,
            value=models[0] if models else "",
            interactive=True,
        )
    else:
        return gr.update(choices=[], value="", interactive=True)


async def update_mcp_server(mcp_file: str, webui_manager: WebuiManager):
    """
    Update the MCP server.
    """
    if hasattr(webui_manager, "bu_controller") and webui_manager.bu_controller:
        logger.warning("⚠️ Close controller because mcp file has changed!")
        await webui_manager.bu_controller.close_mcp_client()
        webui_manager.bu_controller = None

    if not mcp_file or not os.path.exists(mcp_file) or not mcp_file.endswith(".json"):
        logger.warning(f"{mcp_file} is not a valid MCP file.")
        return None, gr.update(visible=False)

    with open(mcp_file) as f:
        mcp_server = json.load(f)

    return json.dumps(mcp_server, indent=2), gr.update(visible=True)


def create_agent_settings_tab(webui_manager: WebuiManager):
    """
    Creates an agent settings tab with improved organization using accordions.
    """
    tab_components = {}

    # System Prompts Section
    with gr.Accordion("📝 System Prompts", open=False):
        gr.Markdown("Customize agent behavior with custom system prompts.")
        with gr.Column():
            override_system_prompt = gr.Textbox(
                label="Override System Prompt",
                lines=4,
                interactive=True,
                placeholder="Replace the entire system prompt with your own...",
            )
            extend_system_prompt = gr.Textbox(
                label="Extend System Prompt",
                lines=4,
                interactive=True,
                placeholder="Add additional instructions to the default prompt...",
            )

    # MCP Configuration Section
    with gr.Accordion("🔌 MCP Configuration", open=False):
        gr.Markdown("Model Context Protocol server configuration.")

        # Check if mcp.json exists and show status
        mcp_config_path = get_mcp_config_path()
        mcp_file_exists = mcp_config_path.exists()
        mcp_file_config = load_mcp_config() if mcp_file_exists else None

        if mcp_file_exists and mcp_file_config:
            status_md = f"""
✅ **Using MCP configuration from file:** `{mcp_config_path}`

{get_mcp_config_summary(mcp_file_config)}

To edit MCP settings, go to the **MCP Settings** tab or edit `{mcp_config_path}` directly.
"""
        else:
            status_md = f"""
ℹ️ No MCP configuration file found at `{mcp_config_path}`

You can:
- Upload a JSON file below (temporary, per-session)
- Go to the **MCP Settings** tab to create and edit a persistent configuration
"""

        mcp_file_status = gr.Markdown(status_md)

        mcp_json_file = gr.File(
            label="MCP server json (Upload for temporary override)",
            interactive=True,
            file_types=[".json"],
            visible=not mcp_file_exists,  # Hide if file already exists
        )
        mcp_server_config = gr.Textbox(
            label="MCP server configuration", lines=6, interactive=True, visible=False
        )

    # Primary LLM Configuration
    with gr.Accordion("🤖 Primary LLM Configuration", open=True):
        gr.Markdown("**Main language model** used for agent reasoning and actions.")

        with gr.Row():
            llm_provider = gr.Dropdown(
                choices=[provider for provider, model in config.model_names.items()],
                label="LLM Provider",
                value=os.getenv("DEFAULT_LLM", "openai"),
                info="Select LLM provider",
                interactive=True,
            )
            llm_model_name = gr.Dropdown(
                label="Model Name",
                choices=config.model_names[os.getenv("DEFAULT_LLM", "openai")],
                value=config.model_names[os.getenv("DEFAULT_LLM", "openai")][0],
                interactive=True,
                allow_custom_value=True,
                info="Select or type custom model name",
            )

        with gr.Row():
            llm_temperature = gr.Slider(
                minimum=0.0,
                maximum=2.0,
                value=0.6,
                step=0.1,
                label="Temperature",
                info="Controls randomness (0=deterministic, 2=creative)",
                interactive=True,
            )

            use_vision = gr.Checkbox(
                label="Enable Vision",
                value=True,
                info="Input screenshots to LLM for better context",
                interactive=True,
            )

            ollama_num_ctx = gr.Slider(
                minimum=2**8,
                maximum=2**16,
                value=16000,
                step=1,
                label="Ollama Context Length",
                info="Max context length (less = faster)",
                visible=False,
                interactive=True,
            )

        with gr.Accordion("🔑 API Credentials (Optional)", open=False):
            gr.Markdown("Override environment variables with custom credentials.")
            with gr.Row():
                llm_base_url = gr.Textbox(
                    label="Base URL",
                    value="",
                    info="Custom API endpoint (leave blank for default)",
                    placeholder="https://api.example.com/v1",
                )
                llm_api_key = gr.Textbox(
                    label="API Key",
                    type="password",
                    value="",
                    info="Leave blank to use .env file",
                    placeholder="sk-...",
                )

    # Planner LLM Configuration (Optional)
    with gr.Accordion("🧠 Planner LLM Configuration (Optional)", open=False):
        gr.Markdown("""
        **Separate planning model** for complex multi-step reasoning.

        💡 Leave empty to use the same model for both planning and execution.
        """)

        with gr.Row():
            planner_llm_provider = gr.Dropdown(
                choices=[provider for provider, model in config.model_names.items()],
                label="Planner Provider",
                info="Optional separate provider for planning",
                value=None,
                interactive=True,
            )
            planner_llm_model_name = gr.Dropdown(
                label="Planner Model",
                interactive=True,
                allow_custom_value=True,
                info="Select or type custom model name",
            )

        with gr.Row():
            planner_llm_temperature = gr.Slider(
                minimum=0.0,
                maximum=2.0,
                value=0.6,
                step=0.1,
                label="Temperature",
                info="Planning temperature (lower = more focused)",
                interactive=True,
            )

            planner_use_vision = gr.Checkbox(
                label="Enable Vision",
                value=False,
                info="Enable vision for planner",
                interactive=True,
            )

            planner_ollama_num_ctx = gr.Slider(
                minimum=2**8,
                maximum=2**16,
                value=16000,
                step=1,
                label="Ollama Context",
                info="Max context for Ollama",
                visible=False,
                interactive=True,
            )

        with gr.Accordion("🔑 Planner API Credentials (Optional)", open=False):
            with gr.Row():
                planner_llm_base_url = gr.Textbox(
                    label="Base URL",
                    value="",
                    info="Custom API endpoint",
                    placeholder="https://api.example.com/v1",
                )
                planner_llm_api_key = gr.Textbox(
                    label="API Key",
                    type="password",
                    value="",
                    info="Leave blank to use .env",
                    placeholder="sk-...",
                )

    # Advanced Agent Parameters
    with gr.Accordion("⚡ Advanced Parameters", open=False):
        gr.Markdown("**Fine-tune agent behavior** and performance limits.")

        with gr.Row():
            max_steps = gr.Slider(
                minimum=1,
                maximum=1000,
                value=100,
                step=1,
                label="Max Steps",
                info="Maximum reasoning steps before stopping",
                interactive=True,
            )
            max_actions = gr.Slider(
                minimum=1,
                maximum=100,
                value=10,
                step=1,
                label="Max Actions per Step",
                info="Actions per reasoning step",
                interactive=True,
            )

        with gr.Row():
            max_input_tokens = gr.Number(
                label="Max Input Tokens",
                value=128000,
                precision=0,
                interactive=True,
                info="Context window limit",
            )
            tool_calling_method = gr.Dropdown(
                label="Tool Calling Method",
                value="auto",
                interactive=True,
                allow_custom_value=True,
                choices=["function_calling", "json_mode", "raw", "auto", "tools", "None"],
                info="Auto-detect recommended",
                visible=True,
            )
    tab_components.update(
        {
            "override_system_prompt": override_system_prompt,
            "extend_system_prompt": extend_system_prompt,
            "llm_provider": llm_provider,
            "llm_model_name": llm_model_name,
            "llm_temperature": llm_temperature,
            "use_vision": use_vision,
            "ollama_num_ctx": ollama_num_ctx,
            "llm_base_url": llm_base_url,
            "llm_api_key": llm_api_key,
            "planner_llm_provider": planner_llm_provider,
            "planner_llm_model_name": planner_llm_model_name,
            "planner_llm_temperature": planner_llm_temperature,
            "planner_use_vision": planner_use_vision,
            "planner_ollama_num_ctx": planner_ollama_num_ctx,
            "planner_llm_base_url": planner_llm_base_url,
            "planner_llm_api_key": planner_llm_api_key,
            "max_steps": max_steps,
            "max_actions": max_actions,
            "max_input_tokens": max_input_tokens,
            "tool_calling_method": tool_calling_method,
            "mcp_file_status": mcp_file_status,
            "mcp_json_file": mcp_json_file,
            "mcp_server_config": mcp_server_config,
        }
    )
    webui_manager.add_components("agent_settings", tab_components)

    llm_provider.change(
        fn=lambda x: gr.update(visible=x == "ollama"), inputs=llm_provider, outputs=ollama_num_ctx
    )
    llm_provider.change(
        lambda provider: update_model_dropdown(provider),
        inputs=[llm_provider],
        outputs=[llm_model_name],
    )
    planner_llm_provider.change(
        fn=lambda x: gr.update(visible=x == "ollama"),
        inputs=[planner_llm_provider],
        outputs=[planner_ollama_num_ctx],
    )
    planner_llm_provider.change(
        lambda provider: update_model_dropdown(provider),
        inputs=[planner_llm_provider],
        outputs=[planner_llm_model_name],
    )

    async def update_wrapper(mcp_file):
        """Wrapper for handle_pause_resume."""
        update_dict = await update_mcp_server(mcp_file, webui_manager)
        yield update_dict

    mcp_json_file.change(
        update_wrapper, inputs=[mcp_json_file], outputs=[mcp_server_config, mcp_server_config]
    )
