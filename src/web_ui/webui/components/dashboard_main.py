"""
Dashboard Main Content Area

Unified execution area for Browser Use Agent and Deep Research Agent.
Includes agent selector, task input, control buttons, and output display.
"""

import logging

import gradio as gr

from src.web_ui.webui.webui_manager import WebuiManager

logger = logging.getLogger(__name__)


def create_dashboard_main(webui_manager: WebuiManager):
    """
    Create the main dashboard content area with agent selector and unified execution.

    Args:
        webui_manager: WebUI manager instance
    """
    main_components = {}

    with gr.Column(elem_classes=["dashboard-main"]):
        # Agent Selector
        gr.Markdown("### 🤖 Agent Selection")
        agent_selector = gr.Dropdown(
            choices=["Browser Use Agent", "Deep Research Agent"],
            value="Browser Use Agent",
            label="Select Agent",
            info="Choose which agent to use for this task",
            interactive=True,
            elem_classes=["agent-selector"],
        )

        gr.Markdown("---")

        # Browser Use Agent Section
        with gr.Group(visible=True) as browser_use_group:
            gr.Markdown("### 🌐 Browser Use Agent")
            gr.Markdown("_Control a web browser to perform tasks automatically_")

            # Import browser use agent tab components
            # We'll reuse the existing function but adapt it
            with gr.Column():
                # Task Input
                user_input = gr.Textbox(
                    label="Task Description",
                    placeholder="Enter what you want the browser agent to do...",
                    lines=3,
                    interactive=True,
                )

                # Control Buttons
                with gr.Row():
                    run_button = gr.Button("▶️ Run Agent", variant="primary", scale=2)
                    stop_button = gr.Button("⏹️ Stop", variant="stop", scale=1, interactive=False)
                    pause_resume_button = gr.Button(
                        "⏸️ Pause", variant="secondary", scale=1, interactive=False
                    )
                    clear_button = gr.Button("🗑️ Clear", variant="secondary", scale=1)

                # Progress Display
                progress_text = gr.Markdown("**Status:** Ready", elem_classes=["progress-text"])

                # Output Area
                with gr.Tabs():
                    with gr.TabItem("💬 Chat"):
                        chatbot = gr.Chatbot(
                            label="Agent Conversation",
                            type="messages",
                            height=500,
                            show_copy_button=True,
                            elem_classes=["agent-chatbot"],
                        )

                        # User assistance input (for ask_for_assistant callbacks)
                        with gr.Row(visible=False) as user_help_row:
                            user_help_input = gr.Textbox(
                                label="Assistant Response",
                                placeholder="Provide information or confirmation...",
                                lines=2,
                            )
                            submit_help_button = gr.Button("Submit Response", variant="primary")

                    with gr.TabItem("🖼️ Browser View"):
                        browser_view = gr.Image(
                            label="Current Browser View",
                            type="filepath",
                            interactive=False,
                            height=500,
                        )

                    with gr.TabItem("📹 Recording"):
                        recording_gif = gr.File(
                            label="Session Recording (GIF)",
                            interactive=False,
                        )

                    with gr.TabItem("📜 History"):
                        agent_history_file = gr.File(
                            label="Agent History (JSON)",
                            interactive=False,
                        )

        # Deep Research Agent Section
        with gr.Group(visible=False) as deep_research_group:
            gr.Markdown("### 🔬 Deep Research Agent")
            gr.Markdown("_Perform comprehensive multi-source research with automatic synthesis_")

            with gr.Column():
                # Research Task Input
                research_task = gr.Textbox(
                    label="Research Topic",
                    placeholder="Enter the topic you want to research...",
                    lines=3,
                    interactive=True,
                )

                # Research-Specific Options
                with gr.Row():
                    resume_task_id = gr.Textbox(
                        label="Resume Task ID (Optional)",
                        placeholder="Leave empty for new research",
                        interactive=True,
                    )
                    parallel_num = gr.Slider(
                        minimum=1,
                        maximum=5,
                        value=1,
                        step=1,
                        label="Parallel Agents",
                        info="Number of concurrent browser agents",
                        interactive=True,
                    )

                max_query = gr.Textbox(
                    label="Save Directory",
                    value="./tmp/deep_research",
                    interactive=True,
                    info="Directory to save research outputs",
                )

                # Control Buttons
                with gr.Row():
                    start_button = gr.Button("▶️ Start Research", variant="primary", scale=2)
                    stop_button_dr = gr.Button("⏹️ Stop", variant="stop", scale=1, interactive=False)
                    clear_button_dr = gr.Button("🗑️ Clear", variant="secondary", scale=1)

                # Research Output
                with gr.Tabs():
                    with gr.TabItem("📄 Report"):
                        markdown_display = gr.Markdown(
                            "Research results will appear here...",
                            elem_classes=["research-report"],
                        )

                    with gr.TabItem("⬇️ Download"):
                        markdown_download = gr.File(
                            label="Download Research Report",
                            interactive=False,
                        )

                # MCP Server Config (hidden, used internally)
                mcp_server_config = gr.Textbox(visible=False)

        # Register Browser Use Agent components with old-style IDs for compatibility
        browser_use_components = {
            "user_input": user_input,
            "run_button": run_button,
            "stop_button": stop_button,
            "pause_resume_button": pause_resume_button,
            "clear_button": clear_button,
            "progress_text": progress_text,
            "chatbot": chatbot,
            "user_help_row": user_help_row,
            "user_help_input": user_help_input,
            "submit_help_button": submit_help_button,
            "browser_view": browser_view,
            "recording_gif": recording_gif,
            "agent_history_file": agent_history_file,
        }
        webui_manager.add_components("browser_use_agent", browser_use_components)

        # Register Deep Research Agent components with old-style IDs for compatibility
        deep_research_components = {
            "research_task": research_task,
            "resume_task_id": resume_task_id,
            "parallel_num": parallel_num,
            "max_query": max_query,
            "start_button": start_button,
            "stop_button": stop_button_dr,
            "clear_button": clear_button_dr,
            "markdown_display": markdown_display,
            "markdown_download": markdown_download,
            "mcp_server_config": mcp_server_config,
        }
        webui_manager.add_components("deep_research_agent", deep_research_components)

        # Register dashboard-level components
        main_components.update(
            {
                "agent_selector": agent_selector,
                "browser_use_group": browser_use_group,
                "deep_research_group": deep_research_group,
            }
        )
        webui_manager.add_components("dashboard_main", main_components)

        # Agent selector change handler
        def switch_agent(agent_type: str):
            """Toggle visibility of agent-specific UI sections."""
            show_browser_use = agent_type == "Browser Use Agent"
            show_deep_research = agent_type == "Deep Research Agent"

            # Update webui_manager state
            if hasattr(webui_manager, "current_agent_type"):
                webui_manager.current_agent_type = (
                    "browser_use" if show_browser_use else "deep_research"
                )

            return {
                browser_use_group: gr.update(visible=show_browser_use),
                deep_research_group: gr.update(visible=show_deep_research),
            }

        agent_selector.change(
            fn=switch_agent,
            inputs=[agent_selector],
            outputs=[browser_use_group, deep_research_group],
        )

        # Note: Actual agent execution handlers (run_button.click, start_button.click, etc.)
        # will be wired up in interface.py after all components are registered

    return main_components
