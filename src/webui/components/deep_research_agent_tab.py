import gradio as gr
from gradio.components import Component
from functools import partial

from src.webui.webui_manager import WebuiManager
from src.utils import config
import logging
import os
from typing import Any, Dict, AsyncGenerator, Optional, Tuple, Union
import asyncio
import json
from src.agent.deep_research.deep_research_agent import DeepResearchAgent
from src.utils import llm_provider

logger = logging.getLogger(__name__)


async def _initialize_llm(provider: Optional[str], model_name: Optional[str], temperature: float,
                          base_url: Optional[str], api_key: Optional[str], num_ctx: Optional[int] = None):
    """Initializes the LLM based on settings. Returns None if provider/model is missing."""
    if not provider or not model_name:
        logger.info("LLM Provider or Model Name not specified, LLM will be None.")
        return None
    try:
        logger.info(f"Initializing LLM: Provider={provider}, Model={model_name}, Temp={temperature}")
        # Use your actual LLM provider logic here
        llm = llm_provider.get_llm_model(
            provider=provider,
            model_name=model_name,
            temperature=temperature,
            base_url=base_url or None,
            api_key=api_key or None,
            num_ctx=num_ctx if provider == "ollama" else None
        )
        return llm
    except Exception as e:
        logger.error(f"Failed to initialize LLM: {e}", exc_info=True)
        gr.Warning(
            f"Failed to initialize LLM '{model_name}' for provider '{provider}'. Please check settings. Error: {e}")
        return None


def _read_file_safe(file_path: str) -> Optional[str]:
    """Safely read a file, returning None if it doesn't exist or on error."""
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return None


# --- Deep Research Agent Specific Logic ---

async def run_deep_research(webui_manager: WebuiManager, components: Dict[Component, Any]) -> AsyncGenerator[
    Dict[Component, Any], None]:
    """Handles initializing and running the DeepResearchAgent."""

    # --- Get Components ---
    research_task_comp = webui_manager.get_component_by_id("deep_research_agent.research_task")
    resume_task_id_comp = webui_manager.get_component_by_id("deep_research_agent.resume_task_id")
    parallel_num_comp = webui_manager.get_component_by_id("deep_research_agent.parallel_num")
    save_dir_comp = webui_manager.get_component_by_id(
        "deep_research_agent.max_query")  # Note: component ID seems misnamed in original code
    start_button_comp = webui_manager.get_component_by_id("deep_research_agent.start_button")
    stop_button_comp = webui_manager.get_component_by_id("deep_research_agent.stop_button")
    markdown_display_comp = webui_manager.get_component_by_id("deep_research_agent.markdown_display")
    markdown_download_comp = webui_manager.get_component_by_id("deep_research_agent.markdown_download")
    mcp_server_config_comp = webui_manager.get_component_by_id("deep_research_agent.mcp_server_config")

    # New UI components for interaction
    status_display_comp = webui_manager.get_component_by_id("deep_research_agent.status_display")
    confirmation_group_comp = webui_manager.get_component_by_id("deep_research_agent.confirmation_group")
    # confirm_synthesis_button_comp = webui_manager.get_component_by_id("deep_research_agent.confirm_synthesis_button") # Already part of all_managed_inputs if named correctly
    error_feedback_group_comp = webui_manager.get_component_by_id("deep_research_agent.error_feedback_group")
    error_details_display_comp = webui_manager.get_component_by_id("deep_research_agent.error_details_display")
    # error_feedback_choice_comp = webui_manager.get_component_by_id("deep_research_agent.error_feedback_choice") # Already part of all_managed_inputs
    # submit_error_feedback_button_comp = webui_manager.get_component_by_id("deep_research_agent.submit_error_feedback_button") # Already part of all_managed_inputs


    # --- 1. Get Task and Settings ---
    task_topic = components.get(research_task_comp, "").strip()
    task_id_to_resume = components.get(resume_task_id_comp, "").strip() or None
    max_parallel_agents = int(components.get(parallel_num_comp, 1))
    base_save_dir = components.get(save_dir_comp, "./tmp/deep_research").strip()
    safe_root_dir = "./tmp/deep_research"
    normalized_base_save_dir = os.path.abspath(os.path.normpath(base_save_dir))
    if os.path.commonpath([normalized_base_save_dir, os.path.abspath(safe_root_dir)]) != os.path.abspath(safe_root_dir):
        logger.warning(f"Unsafe base_save_dir detected: {base_save_dir}. Using default directory.")
        normalized_base_save_dir = os.path.abspath(safe_root_dir)
    base_save_dir = normalized_base_save_dir
    mcp_server_config_str = components.get(mcp_server_config_comp)
    mcp_config = json.loads(mcp_server_config_str) if mcp_server_config_str else None

    if not task_topic:
        gr.Warning("Please enter a research task.")
        yield {start_button_comp: gr.update(interactive=True)}  # Re-enable start button
        return

    # Store base save dir for stop handler
    webui_manager.dr_save_dir = base_save_dir
    os.makedirs(base_save_dir, exist_ok=True)

    # --- 2. Initial UI Update ---
    yield {
        start_button_comp: gr.update(value="⏳ Running...", interactive=False),
        stop_button_comp: gr.update(interactive=True),
        research_task_comp: gr.update(interactive=False),
        resume_task_id_comp: gr.update(interactive=False),
        parallel_num_comp: gr.update(interactive=False),
        save_dir_comp: gr.update(interactive=False),
        markdown_display_comp: gr.update(value=""), # Clear previous report
        markdown_download_comp: gr.update(value=None, interactive=False),
        status_display_comp: gr.update(value="Starting research...", visible=True),
        confirmation_group_comp: gr.update(visible=False),
        error_feedback_group_comp: gr.update(visible=False),
    }

    # agent_task renamed to agent_run_task_async for clarity
    agent_run_task_async = None
    running_task_id = None
    plan_file_path = None
    report_file_path = None
    last_plan_content = None
    last_plan_mtime = 0

    try:
        # --- 3. Get LLM and Browser Config from other tabs ---
        # Access settings values via components dict, getting IDs from webui_manager
        def get_setting(tab: str, key: str, default: Any = None):
            comp = webui_manager.id_to_component.get(f"{tab}.{key}")
            return components.get(comp, default) if comp else default

        # LLM Config (from agent_settings tab)
        llm_provider_name = get_setting("agent_settings", "llm_provider")
        llm_model_name = get_setting("agent_settings", "llm_model_name")
        llm_temperature = max(get_setting("agent_settings", "llm_temperature", 0.5), 0.5)
        llm_base_url = get_setting("agent_settings", "llm_base_url")
        llm_api_key = get_setting("agent_settings", "llm_api_key")
        ollama_num_ctx = get_setting("agent_settings", "ollama_num_ctx")

        llm = await _initialize_llm(
            llm_provider_name, llm_model_name, llm_temperature, llm_base_url, llm_api_key,
            ollama_num_ctx if llm_provider_name == "ollama" else None
        )
        if not llm:
            raise ValueError("LLM Initialization failed. Please check Agent Settings.")

        # Browser Config (from browser_settings tab)
        # Note: DeepResearchAgent constructor takes a dict, not full Browser/Context objects
        browser_config_dict = {
            "headless": get_setting("browser_settings", "headless", False),
            "disable_security": get_setting("browser_settings", "disable_security", False),
            "browser_binary_path": get_setting("browser_settings", "browser_binary_path"),
            "user_data_dir": get_setting("browser_settings", "browser_user_data_dir"),
            "window_width": int(get_setting("browser_settings", "window_w", 1280)),
            "window_height": int(get_setting("browser_settings", "window_h", 1100)),
            # Add other relevant fields if DeepResearchAgent accepts them
        }

        # --- 4. Initialize or Get Agent ---
        if not webui_manager.dr_agent:
            webui_manager.dr_agent = DeepResearchAgent(
                llm=llm,
                browser_config=browser_config_dict,
                mcp_server_config=mcp_config
            )
            logger.info("DeepResearchAgent initialized.")
        # Persist the agent instance in webui_manager if it's a new run or resuming an existing one
        # This is now implicitly handled by webui_manager.dr_agent not being cleared if paused.

        # --- 5. Start Agent Run ---
        # The agent instance (webui_manager.dr_agent) is now managed across calls if paused.
        # Task ID for resume is handled by the agent itself if passed in initial_state.
        # We use webui_manager.dr_task_id to track the *current* or *resumed* task.

        current_agent_task_id = task_id_to_resume if task_id_to_resume else None

        # Store agent and task_id in webui_manager so other handlers can access it
        webui_manager.dr_task_id = current_agent_task_id # May be updated by agent's run result

        agent_run_coro = webui_manager.dr_agent.run(
            topic=task_topic, # Topic might be ignored if resuming with a plan
            task_id=current_agent_task_id,
            save_dir=base_save_dir,
            max_parallel_browsers=max_parallel_agents
        )
        agent_run_task_async = asyncio.create_task(agent_run_coro)
        webui_manager.dr_current_task_async = agent_run_task_async

        # Initial running_task_id, might be updated by the agent's run method's result
        running_task_id = webui_manager.dr_agent.current_task_id # Agent sets this internally on run
        if not running_task_id and current_agent_task_id: # If resuming, agent.current_task_id might not be set until run
            running_task_id = current_agent_task_id

        webui_manager.dr_task_id = running_task_id # Update manager with potentially new task_id from a fresh run

        # --- 6. Monitor Progress & Handle Intermediate States ---
        # This loop replaces the old file monitoring. It now processes agent's dictionary results.
        last_plan_content = "" # To avoid re-rendering identical plan

        while not agent_run_task_async.done():
            # Try to get intermediate results or updates if agent supports streaming them.
            # For now, we'll primarily rely on the final_result_dict after the task is done,
            # but this structure allows for future enhancements if agent.run() becomes a generator.
            # The main loop will break when agent_run_task_async is done.

            # Update plan display if running_task_id is known
            if running_task_id: # Ensure running_task_id is set (agent sets this)
                task_specific_dir = os.path.join(base_save_dir, str(running_task_id))
                plan_file_path = os.path.join(task_specific_dir, "research_plan.md")
                if os.path.exists(plan_file_path):
                    try:
                        current_plan_content = _read_file_safe(plan_file_path)
                        if current_plan_content and current_plan_content != last_plan_content:
                            yield {markdown_display_comp: gr.update(value=current_plan_content)}
                            last_plan_content = current_plan_content
                    except Exception as e:
                        logger.warning(f"Could not read plan file for update: {e}")

            agent_stopped_flag = getattr(webui_manager.dr_agent, 'stopped', False)
            if agent_stopped_flag:
                logger.info("Stop signal detected from agent state during run.")
                break # Exit monitoring loop, let finalization handle result.

            yield {resume_task_id_comp: gr.update(value=running_task_id if running_task_id else "")}
            await asyncio.sleep(1.0)

        logger.info("Agent task processing finished. Awaiting final result from agent.run()...")
        final_result_dict = await agent_run_task_async
        webui_manager.dr_current_task_async = None # Clear finished asyncio task

        running_task_id = final_result_dict.get("task_id", running_task_id) # Update task_id from final result
        webui_manager.dr_task_id = running_task_id # Ensure manager has the definitive task_id

        logger.info(f"Agent run completed. Status: {final_result_dict.get('status')}, Message: {final_result_dict.get('message')}")

        ui_updates = {
            stop_button_comp: gr.update(interactive=False),
            # Default to re-enabling inputs, specific states below will override
            start_button_comp: gr.update(value="▶️ Run", interactive=True),
            research_task_comp: gr.update(interactive=True),
            resume_task_id_comp: gr.update(interactive=True, value=running_task_id), # Show final task ID
            parallel_num_comp: gr.update(interactive=True),
            save_dir_comp: gr.update(interactive=True),
        }

        status = final_result_dict.get("status")

        if status == "awaiting_confirmation":
            ui_updates[status_display_comp] = gr.update(value=final_result_dict.get("message", "Awaiting final confirmation from user."), visible=True)
            ui_updates[confirmation_group_comp] = gr.update(visible=True)
            ui_updates[error_feedback_group_comp] = gr.update(visible=False)
            ui_updates[start_button_comp] = gr.update(interactive=False) # Keep run disabled
            ui_updates[research_task_comp] = gr.update(interactive=False)
            ui_updates[resume_task_id_comp] = gr.update(interactive=False)
            # webui_manager.dr_agent should NOT be cleared here by run_deep_research
        elif status == "awaiting_error_feedback":
            ui_updates[status_display_comp] = gr.update(value=final_result_dict.get("message", "Paused due to an error."), visible=True)
            ui_updates[error_details_display_comp] = gr.update(value=f"**Error in {final_result_dict.get('current_error_node_origin', 'N/A')}:**\n\n```\n{final_result_dict.get('error_details', 'No details provided.')}\n```")
            ui_updates[error_feedback_group_comp] = gr.update(visible=True)
            ui_updates[confirmation_group_comp] = gr.update(visible=False)
            ui_updates[start_button_comp] = gr.update(interactive=False) # Keep run disabled
            ui_updates[research_task_comp] = gr.update(interactive=False)
            ui_updates[resume_task_id_comp] = gr.update(interactive=False)
            # webui_manager.dr_agent should NOT be cleared here
        else: # Terminal states: "completed", "stopped", "error", "finished_incomplete"
            ui_updates[status_display_comp] = gr.update(value=f"Status: {status}. {final_result_dict.get('message', '')}", visible=True)
            ui_updates[confirmation_group_comp] = gr.update(visible=False)
            ui_updates[error_feedback_group_comp] = gr.update(visible=False)

            if running_task_id: # Try to load report for terminal states
                task_specific_dir = os.path.join(base_save_dir, str(running_task_id))
                report_file_path = os.path.join(task_specific_dir, "report.md")
                if os.path.exists(report_file_path):
                    report_content = _read_file_safe(report_file_path)
                    ui_updates[markdown_display_comp] = gr.update(value=report_content if report_content else "Report file found but empty.")
                    ui_updates[markdown_download_comp] = gr.File(value=report_file_path, label=f"Report ({running_task_id}.md)", interactive=True)
                elif final_result_dict.get("final_report"): # If report is in dict (e.g. error before save)
                     ui_updates[markdown_display_comp] = gr.update(value=final_result_dict["final_report"])
                     ui_updates[markdown_download_comp] = gr.update(interactive=False, value=None)
                else:
                    ui_updates[markdown_display_comp] = gr.update(value=f"# Research Ended\n\nStatus: {status}\nMessage: {final_result_dict.get('message', 'No further details.')}")
                    ui_updates[markdown_download_comp] = gr.update(interactive=False, value=None)
            else: # No running_task_id, show message from dict
                ui_updates[markdown_display_comp] = gr.update(value=f"# Research Ended\n\nStatus: {status}\nMessage: {final_result_dict.get('message', 'No task ID was available to load report.')}")

            # Clear agent from manager ONLY if it's a terminal state from the initial run
            webui_manager.dr_agent = None
            webui_manager.dr_task_id = None
            logger.info(f"Agent run concluded with terminal status '{status}'. Cleared active agent from WebuiManager.")

        yield ui_updates

    except Exception as e:
        logger.error(f"Error in run_deep_research: {e}", exc_info=True)
        gr.Error(f"Research failed: {e}")
        yield {
            markdown_display_comp: gr.update(value=f"# Research Failed\n\n**Error:**\n```\n{e}\n```"),
            status_display_comp: gr.update(value=f"Critical error: {e}", visible=True),
            start_button_comp: gr.update(interactive=True), # Re-enable on critical failure
            stop_button_comp: gr.update(interactive=False),
            confirmation_group_comp: gr.update(visible=False),
            error_feedback_group_comp: gr.update(visible=False),
        }
        # Ensure agent is cleared on such an error
        webui_manager.dr_agent = None
        webui_manager.dr_task_id = None
        webui_manager.dr_current_task_async = None
    finally:
        # This finally block now only handles UI elements that need resetting if not handled by status logic
        # The agent instance (webui_manager.dr_agent) is managed based on returned status.
        # dr_current_task_async should be None if task finished or errored out of the main try.
        if webui_manager.dr_current_task_async and not webui_manager.dr_current_task_async.done():
             logger.info("run_deep_research finally block: Task was still running, implies an issue if not paused.")

        # If not paused, ensure buttons are reset. If paused, they are managed by the status block.
        current_status_is_paused = False
        if 'status' in locals() and status in ["awaiting_confirmation", "awaiting_error_feedback"]:
            current_status_is_paused = True

        if not current_status_is_paused:
            final_reset_ui = {
                start_button_comp: gr.update(value="▶️ Run", interactive=True),
                stop_button_comp: gr.update(interactive=False),
                research_task_comp: gr.update(interactive=True),
                resume_task_id_comp: gr.update(interactive=True), # Value already set by status block or remains empty
                parallel_num_comp: gr.update(interactive=True),
                save_dir_comp: gr.update(interactive=True),
            }
            # Only yield if there's something to update and not already covered by a specific status yield
            # This avoids a redundant yield if the last status yield already handled button states.
            if status not in ["awaiting_confirmation", "awaiting_error_feedback"]:
                 yield final_reset_ui
        # Ensure dr_current_task_async is cleared if it's done or was never set properly
        webui_manager.dr_current_task_async = None


async def stop_deep_research(webui_manager: WebuiManager) -> Dict[Component, Any]:
    """Handles the Stop button click."""
    logger.info("Stop button clicked for Deep Research.")
    """Handles the Stop button click."""
    logger.info("Stop button clicked for Deep Research.")
    agent = webui_manager.dr_agent
    async_task = webui_manager.dr_current_task_async # Changed from dr_current_task
    task_id = webui_manager.dr_task_id
    base_save_dir = webui_manager.dr_save_dir # Used for report loading

    # Get components for UI updates
    stop_button_comp = webui_manager.get_component_by_id("deep_research_agent.stop_button")
    start_button_comp = webui_manager.get_component_by_id("deep_research_agent.start_button")
    markdown_display_comp = webui_manager.get_component_by_id("deep_research_agent.markdown_display")
    markdown_download_comp = webui_manager.get_component_by_id("deep_research_agent.markdown_download")
    status_display_comp = webui_manager.get_component_by_id("deep_research_agent.status_display")
    confirmation_group_comp = webui_manager.get_component_by_id("deep_research_agent.confirmation_group")
    error_feedback_group_comp = webui_manager.get_component_by_id("deep_research_agent.error_feedback_group")

    ui_updates = {
        stop_button_comp: gr.update(interactive=False, value="⏹️ Stopping..."),
        start_button_comp: gr.update(interactive=False), # Keep start disabled until fully stopped
        confirmation_group_comp: gr.update(visible=False), # Hide interactive groups
        error_feedback_group_comp: gr.update(visible=False),
        status_display_comp: gr.update(value="Stopping research...", visible=True)
    }

    if agent: # Agent might exist even if task is None (e.g. if run failed before task creation)
        logger.info(f"Signalling DeepResearchAgent (task_id: {task_id}) to stop.")
        try:
            await agent.stop() # This should set the agent's internal stop_event
        except Exception as e:
            logger.error(f"Error calling agent.stop(): {e}", exc_info=True)
            gr.Warning(f"Error trying to stop the agent: {e}")
    else:
        logger.warning("Stop clicked but no active DeepResearchAgent instance found.")
        # If no agent, just reset UI
        ui_updates[start_button_comp] = gr.update(value="▶️ Run", interactive=True)
        ui_updates[stop_button_comp] = gr.update(interactive=False)
        ui_updates[status_display_comp] = gr.update(value="No active research to stop.", visible=True)
        # Clean up manager state if no agent was found, ensuring clean state
        webui_manager.dr_agent = None
        webui_manager.dr_task_id = None
        webui_manager.dr_current_task_async = None
        return ui_updates # Early exit if no agent

    # If there was an asyncio task for the agent's run method
    if async_task and not async_task.done():
        logger.info("Waiting for agent's run task to complete after signalling stop...")
        try:
            # Wait for a short period for the task to acknowledge stop and finish
            # The agent's run method's finally block should handle its cleanup.
            await asyncio.wait_for(async_task, timeout=10.0) # Give it time to process stop
        except asyncio.TimeoutError:
            logger.warning("Timeout waiting for agent task to finish after stop. It might be stuck.")
            ui_updates[status_display_comp] = gr.update(value="Agent stop timed out. Task might be stuck.", visible=True)
            # Attempt to cancel the task if it's truly stuck
            async_task.cancel()
        except Exception as e: # Other errors during await
            logger.error(f"Error while waiting for agent task to finish: {e}", exc_info=True)
            ui_updates[status_display_comp] = gr.update(value=f"Error waiting for agent task: {e}", visible=True)

    # Agent's run method's finally block should have executed and returned a result.
    # The result processing (including UI updates for report) is primarily in run_deep_research's main flow.
    # Here, we ensure UI is reset to a stoppable state.

    # Try to load report, as agent might have finished one upon stopping
    report_content_on_stop = "## Research Stopped by User\n\n"
    report_file_path = None
    if task_id and base_save_dir:
        task_specific_dir = os.path.join(base_save_dir, str(task_id))
        report_file_path = os.path.join(task_specific_dir, "report.md")
        if os.path.exists(report_file_path):
            content = _read_file_safe(report_file_path)
            if content:
                report_content_on_stop += content
                ui_updates[markdown_download_comp] = gr.File(value=report_file_path, label=f"Report ({task_id}.md)", interactive=True)
            else:
                report_content_on_stop += "*Final report file was empty or unreadable.*"
        else:
            report_content_on_stop += "*Final report file not found.*"
    else:
        report_content_on_stop += "*Task ID or save directory not available to load report.*"

    ui_updates[markdown_display_comp] = gr.update(value=report_content_on_stop)
    ui_updates[status_display_comp] = gr.update(value="Research stopped.", visible=True)
    ui_updates[start_button_comp] = gr.update(value="▶️ Run", interactive=True) # Re-enable run
    ui_updates[stop_button_comp] = gr.update(value="⏹️ Stop", interactive=False) # Disable stop
    ui_updates[research_task_comp] = gr.update(interactive=True)
    ui_updates[resume_task_id_comp] = gr.update(interactive=True) # Allow new task or resume
    ui_updates[parallel_num_comp] = gr.update(interactive=True)
    ui_updates[save_dir_comp] = gr.update(interactive=True)

    # Crucially, clear the agent from WebuiManager as the task is now considered terminal.
    webui_manager.dr_agent = None
    webui_manager.dr_task_id = None
    webui_manager.dr_current_task_async = None
    logger.info("DeepResearchAgent and its task have been stopped and cleared from WebuiManager.")

    return ui_updates


async def update_mcp_server(mcp_file: str, webui_manager: WebuiManager):
    """
    Update the MCP server.
    """
    if hasattr(webui_manager, "dr_agent") and webui_manager.dr_agent:
        logger.warning("⚠️ Close controller because mcp file has changed!")
        await webui_manager.dr_agent.close_mcp_client()

    if not mcp_file or not os.path.exists(mcp_file) or not mcp_file.endswith('.json'):
        logger.warning(f"{mcp_file} is not a valid MCP file.")
        return None, gr.update(visible=False)

    with open(mcp_file, 'r') as f:
        mcp_server = json.load(f)

    return json.dumps(mcp_server, indent=2), gr.update(visible=True)


def create_deep_research_agent_tab(webui_manager: WebuiManager):
    """
    Creates a deep research agent tab
    """
    input_components = set(webui_manager.get_components())
    tab_components = {}

    with gr.Group():
        with gr.Row():
            mcp_json_file = gr.File(label="MCP server json", interactive=True, file_types=[".json"])
            mcp_server_config = gr.Textbox(label="MCP server", lines=6, interactive=True, visible=False)

    with gr.Group():
        research_task = gr.Textbox(label="Research Task", lines=5,
                                   value="Give me a detailed travel plan to Switzerland from June 1st to 10th.",
                                   interactive=True)
        with gr.Row():
            resume_task_id = gr.Textbox(label="Resume Task ID", value="",
                                        interactive=True)
            parallel_num = gr.Number(label="Parallel Agent Num", value=1,
                                     precision=0,
                                     interactive=True)
            max_query = gr.Textbox(label="Research Save Dir", value="./tmp/deep_research",
                                   interactive=True)
    with gr.Row():
        stop_button = gr.Button("⏹️ Stop", variant="stop", scale=2)
        start_button = gr.Button("▶️ Run", variant="primary", scale=3)
    with gr.Group():
        markdown_display = gr.Markdown(label="Research Report")
        markdown_download = gr.File(label="Download Research Report", interactive=False)
    tab_components.update(
        dict(
            research_task=research_task,
            parallel_num=parallel_num,
            max_query=max_query, # This is actually save_dir
            start_button=start_button,
            stop_button=stop_button,
            markdown_display=markdown_display,
            markdown_download=markdown_download,
            resume_task_id=resume_task_id,
            mcp_json_file=mcp_json_file,
            mcp_server_config=mcp_server_config,
        )
    )
    # Add new UI components to webui_manager and tab_components
    status_display = gr.Markdown(value="Status: Idle", visible=True) # Initially visible
    with gr.Group(visible=False) as confirmation_group:
        confirm_synthesis_button = gr.Button("Confirm and Proceed to Synthesis")
    with gr.Group(visible=False) as error_feedback_group:
        error_details_display = gr.Markdown()
        error_feedback_choice = gr.Radio(choices=["retry", "skip", "abort"], label="Choose action for error", value="retry")
        submit_error_feedback_button = gr.Button("Submit Feedback")

    tab_components.update({
        "status_display": status_display,
        "confirmation_group": confirmation_group,
        "confirm_synthesis_button": confirm_synthesis_button,
        "error_feedback_group": error_feedback_group,
        "error_details_display": error_details_display,
        "error_feedback_choice": error_feedback_choice,
        "submit_error_feedback_button": submit_error_feedback_button,
    })

    webui_manager.add_components("deep_research_agent", tab_components)
    webui_manager.init_deep_research_agent() # Initializes self.dr_agent etc.

    async def update_mcp_wrapper(mcp_file):
        # This function seems to be misnamed in the original, it's for MCP server update
        # It might be better named handle_mcp_upload or similar
        config_str, visibility_update = await update_mcp_server(mcp_file, webui_manager)
        return {mcp_server_config: config_str, mcp_server_config: visibility_update}


    mcp_json_file.change(
        fn=update_mcp_wrapper, # Corrected name if it's for MCP
        inputs=[mcp_json_file],
        outputs=[mcp_server_config, mcp_server_config] # Ensure this matches what update_mcp_server returns
    )

    # Consolidate all components that can be updated by handlers
    # Order matters for Gradio output mapping if not returning a dict keyed by component
    # It's safer to return dicts from handlers: {component_to_update: gr.update(...)}
    # For now, assuming dr_tab_outputs includes all relevant components for updates.
    # We need to add the new components to this list if not using dict returns.

    # Get all components managed by WebuiManager that might need updating
    # This includes components from other tabs if they are in webui_manager.id_to_component
    all_managed_components_list = list(webui_manager.id_to_component.values())


    # --- Define Event Handler Wrappers ---
    # These wrappers will now collect all inputs from the UI that might be needed
    # and pass them to the core logic. They then yield dictionaries of component updates.

    async def handle_run_button_click(comps: Dict[Component, Any]) -> AsyncGenerator[Dict[Component, Any], None]:
        # `comps` is already a dictionary of all managed components from `all_managed_inputs`
        async for update_dict in run_deep_research(webui_manager, comps):
            yield update_dict

    async def handle_stop_button_click() -> AsyncGenerator[Dict[Component, Any], None]:
        update_dict = await stop_deep_research(webui_manager)
        yield update_dict

    async def handle_confirm_synthesis_click() -> AsyncGenerator[Dict[Component, Any], None]:
        logger.info("Confirm Synthesis button clicked.")
        # Disable interaction groups immediately
        yield {
            confirmation_group_comp: gr.update(visible=False),
            status_display_comp: gr.update(value="Confirmation received. Resuming for synthesis..."),
        }
        result = await webui_manager.provide_final_confirmation_to_agent()

        # Process result and update UI (similar to terminal states in run_deep_research)
        ui_updates = {
            start_button_comp: gr.update(interactive=True), # Re-enable run button
            stop_button_comp: gr.update(interactive=False),
            research_task_comp: gr.update(interactive=True),
            resume_task_id_comp: gr.update(interactive=True, value=result.get("task_id","")),
            status_display_comp: gr.update(value=f"Status: {result.get('status')}. {result.get('message', '')}", visible=True),
            confirmation_group_comp: gr.update(visible=False),
            error_feedback_group_comp: gr.update(visible=False),
        }
        if result.get("status") == "completed" and result.get("final_state", {}).get("final_report"):
            ui_updates[markdown_display_comp] = gr.update(value=result["final_state"]["final_report"])
            if result.get("task_id") and webui_manager.dr_save_dir:
                report_file = os.path.join(webui_manager.dr_save_dir, str(result["task_id"]), "report.md")
                if os.path.exists(report_file):
                     ui_updates[markdown_download_comp] = gr.File(value=report_file, label=f"Report ({result['task_id']}.md)", interactive=True)
        elif result.get("status") == "error":
            ui_updates[markdown_display_comp] = gr.update(value=f"# Synthesis Failed\n\nError: {result.get('message')}")
        yield ui_updates

    async def handle_submit_error_feedback_click(feedback_choice: str) -> AsyncGenerator[Dict[Component, Any], None]:
        logger.info(f"Submit Error Feedback button clicked. Choice: {feedback_choice}")
        # Disable interaction groups immediately
        yield {
            error_feedback_group_comp: gr.update(visible=False),
            status_display_comp: gr.update(value=f"Feedback '{feedback_choice}' received. Resuming..."),
        }
        result = await webui_manager.provide_error_feedback_to_agent(feedback_choice)

        ui_updates = { # Default to re-enabling main controls if terminal
            start_button_comp: gr.update(interactive=True),
            stop_button_comp: gr.update(interactive=False),
            research_task_comp: gr.update(interactive=True),
            resume_task_id_comp: gr.update(interactive=True, value=result.get("task_id","")),
        }

        status = result.get("status")
        if status == "awaiting_confirmation":
            ui_updates[status_display_comp] = gr.update(value=result.get("message", "Awaiting final confirmation."), visible=True)
            ui_updates[confirmation_group_comp] = gr.update(visible=True)
            ui_updates[error_feedback_group_comp] = gr.update(visible=False)
            ui_updates[start_button_comp] = gr.update(interactive=False) # Keep run disabled
            ui_updates[research_task_comp] = gr.update(interactive=False)
            ui_updates[resume_task_id_comp] = gr.update(interactive=False)
        elif status == "awaiting_error_feedback":
            ui_updates[status_display_comp] = gr.update(value=result.get("message", "Paused due to an error."), visible=True)
            ui_updates[error_details_display_comp] = gr.update(value=f"**Error in {result.get('current_error_node_origin', 'N/A')}:**\n\n```\n{result.get('error_details', 'No details provided.')}\n```")
            ui_updates[error_feedback_group_comp] = gr.update(visible=True)
            ui_updates[confirmation_group_comp] = gr.update(visible=False)
            ui_updates[start_button_comp] = gr.update(interactive=False) # Keep run disabled
            ui_updates[research_task_comp] = gr.update(interactive=False)
            ui_updates[resume_task_id_comp] = gr.update(interactive=False)
        else: # Terminal states
            ui_updates[status_display_comp] = gr.update(value=f"Status: {status}. {result.get('message', '')}", visible=True)
            ui_updates[confirmation_group_comp] = gr.update(visible=False)
            ui_updates[error_feedback_group_comp] = gr.update(visible=False)
            if status == "completed" and result.get("final_state", {}).get("final_report"):
                ui_updates[markdown_display_comp] = gr.update(value=result["final_state"]["final_report"])
                if result.get("task_id") and webui_manager.dr_save_dir:
                    report_file = os.path.join(webui_manager.dr_save_dir, str(result["task_id"]), "report.md")
                    if os.path.exists(report_file):
                        ui_updates[markdown_download_comp] = gr.File(value=report_file, label=f"Report ({result['task_id']}.md)", interactive=True)
            elif status == "error":
                 ui_updates[markdown_display_comp] = gr.update(value=f"# Task Failed after Feedback\n\nError: {result.get('message')}")
            elif result.get("final_state", {}).get("final_report"): # E.g. for skipped then completed
                 ui_updates[markdown_display_comp] = gr.update(value=result["final_state"]["final_report"])
                 if result.get("task_id") and webui_manager.dr_save_dir:
                    report_file = os.path.join(webui_manager.dr_save_dir, str(result["task_id"]), "report.md")
                    if os.path.exists(report_file):
                        ui_updates[markdown_download_comp] = gr.File(value=report_file, label=f"Report ({result['task_id']}.md)", interactive=True)
        yield ui_updates

    # --- Connect Handlers ---
    # Inputs for start_button are all components webui_manager is aware of.
    # Outputs are all components in the current tab that might be updated.
    # Using dicts for outputs is more robust.

    # The `inputs` for `start_button.click` should be `webui_manager.get_components()`
    # to ensure all settings from other tabs are correctly passed.
    # The `outputs` should be a list of all components that can be affected by `run_deep_research`.
    # This includes the new UI elements.

    # Define the list of ALL components that any of these handlers might update.
    # This is important for Gradio's .click() method when not returning a dict.
    # However, it's better practice for handlers to yield dicts of {component: gr.update()},
    # then the `outputs` list in .click() can be minimal or just those components.
    # For safety, list all potentially affected components if not using dict returns consistently.

    output_components_for_handlers = [
        start_button, stop_button, research_task, resume_task_id, parallel_num, max_query, # max_query is save_dir
        markdown_display, markdown_download, status_display,
        confirmation_group, error_feedback_group, error_details_display
    ]


    start_button.click(
        fn=handle_run_button_click,
        inputs=webui_manager.get_components(), # Pass all managed components as dict
        outputs=output_components_for_handlers # Explicitly list outputs
    )

    stop_button.click(
        fn=handle_stop_button_click,
        inputs=None,
        outputs=output_components_for_handlers
    )

    confirm_synthesis_button.click(
        fn=handle_confirm_synthesis_click,
        inputs=None, # Task_id will be taken from webui_manager
        outputs=output_components_for_handlers
    )

    submit_error_feedback_button.click(
        fn=handle_submit_error_feedback_click,
        inputs=[error_feedback_choice], # Pass the choice from radio
        outputs=output_components_for_handlers
    )
