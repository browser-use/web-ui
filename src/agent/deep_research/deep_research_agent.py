import asyncio
import json
import logging
import os
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict

from browser_use.browser.browser import BrowserConfig
from langchain_community.tools.file_management import (
    ListDirectoryTool,
    ReadFileTool,
    WriteFileTool,
)

# Langchain imports
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import StructuredTool, Tool

# Langgraph imports
from langgraph.graph import StateGraph
from pydantic import BaseModel, Field

from browser_use.browser.context import BrowserContextConfig

from src.agent.browser_use.browser_use_agent import BrowserUseAgent
from src.browser.custom_browser import CustomBrowser
from src.controller.custom_controller import CustomController
from src.utils.mcp_client import setup_mcp_client_and_tools

logger = logging.getLogger(__name__)

# Constants
REPORT_FILENAME = "report.md"
PLAN_FILENAME = "research_plan.md"
SEARCH_INFO_FILENAME = "search_info.json"

_AGENT_STOP_FLAGS = {}
_BROWSER_AGENT_INSTANCES = {}


async def run_single_browser_task(
        task_query: str,
        task_id: str,
        llm: Any,  # Pass the main LLM
        browser_config: Dict[str, Any],
        stop_event: threading.Event,
        use_vision: bool = False,
) -> Dict[str, Any]:
    """
    Runs a single BrowserUseAgent task.
    Manages browser creation and closing for this specific task.
    """
    if not BrowserUseAgent:
        return {
            "query": task_query,
            "error": "BrowserUseAgent components not available.",
        }

    # --- Browser Setup ---
    # These should ideally come from the main agent's config
    headless = browser_config.get("headless", False)
    window_w = browser_config.get("window_width", 1280)
    window_h = browser_config.get("window_height", 1100)
    browser_user_data_dir = browser_config.get("user_data_dir", None)
    use_own_browser = browser_config.get("use_own_browser", False)
    browser_binary_path = browser_config.get("browser_binary_path", None)
    wss_url = browser_config.get("wss_url", None)
    cdp_url = browser_config.get("cdp_url", None)
    disable_security = browser_config.get("disable_security", False)

    bu_browser = None
    bu_browser_context = None
    try:
        logger.info(f"Starting browser task for query: {task_query}")
        extra_args = []
        if use_own_browser:
            browser_binary_path = os.getenv("BROWSER_PATH", None) or browser_binary_path
            if browser_binary_path == "":
                browser_binary_path = None
            browser_user_data = browser_user_data_dir or os.getenv("BROWSER_USER_DATA", None)
            if browser_user_data:
                extra_args += [f"--user-data-dir={browser_user_data}"]
        else:
            browser_binary_path = None

        bu_browser = CustomBrowser(
            config=BrowserConfig(
                headless=headless,
                browser_binary_path=browser_binary_path,
                extra_browser_args=extra_args,
                wss_url=wss_url,
                cdp_url=cdp_url,
                new_context_config=BrowserContextConfig(
                    window_width=window_w,
                    window_height=window_h,
                )
            )
        )

        context_config = BrowserContextConfig(
            save_downloads_path="./tmp/downloads",
            window_height=window_h,
            window_width=window_w,
            force_new_context=True,
        )
        bu_browser_context = await bu_browser.new_context(config=context_config)

        # Simple controller example, replace with your actual implementation if needed
        bu_controller = CustomController()

        # Construct the task prompt for BrowserUseAgent
        # Instruct it to find specific info and return title/URL
        bu_task_prompt = f"""
        Research Task: {task_query}
        Objective: Find relevant information answering the query.
        Output Requirements: For each relevant piece of information found, please provide:
        1. A concise summary of the information.
        2. The title of the source page or document.
        3. The URL of the source.
        Focus on accuracy and relevance. Avoid irrelevant details.
        PDF cannot directly extract _content, please try to download first, then using read_file, if you can't save or read, please try other methods.
        """

        bu_agent_instance = BrowserUseAgent(
            task=bu_task_prompt,
            llm=llm,  # Use the passed LLM
            browser=bu_browser,
            browser_context=bu_browser_context,
            controller=bu_controller,
            use_vision=use_vision,
            source="webui",
        )

        # Store instance for potential stop() call
        task_key = f"{task_id}_{uuid.uuid4()}"
        _BROWSER_AGENT_INSTANCES[task_key] = bu_agent_instance

        # --- Run with Stop Check ---
        # BrowserUseAgent needs to internally check a stop signal or have a stop method.
        # We simulate checking before starting and assume `run` might be interruptible
        # or have its own stop mechanism we can trigger via bu_agent_instance.stop().
        if stop_event.is_set():
            logger.info(f"Browser task for '{task_query}' cancelled before start.")
            return {"query": task_query, "result": None, "status": "cancelled"}

        # The run needs to be awaitable and ideally accept a stop signal or have a .stop() method
        # result = await bu_agent_instance.run(max_steps=max_steps) # Add max_steps if applicable
        # Let's assume a simplified run for now
        logger.info(f"Running BrowserUseAgent for: {task_query}")
        result = await bu_agent_instance.run()  # Assuming run is the main method
        logger.info(f"BrowserUseAgent finished for: {task_query}")

        final_data = result.final_result()

        if stop_event.is_set():
            logger.info(f"Browser task for '{task_query}' stopped during execution.")
            return {"query": task_query, "result": final_data, "status": "stopped"}
        else:
            logger.info(f"Browser result for '{task_query}': {final_data}")
            return {"query": task_query, "result": final_data, "status": "completed"}

    except Exception as e:
        logger.error(
            f"Error during browser task for query '{task_query}': {e}", exc_info=True
        )
        return {"query": task_query, "error": str(e), "status": "failed"}
    finally:
        if bu_browser_context:
            try:
                await bu_browser_context.close()
                bu_browser_context = None
                logger.info("Closed browser context.")
            except Exception as e:
                logger.error(f"Error closing browser context: {e}")
        if bu_browser:
            try:
                await bu_browser.close()
                bu_browser = None
                logger.info("Closed browser.")
            except Exception as e:
                logger.error(f"Error closing browser: {e}")

        if task_key in _BROWSER_AGENT_INSTANCES:
            del _BROWSER_AGENT_INSTANCES[task_key]


class BrowserSearchInput(BaseModel):
    queries: List[str] = Field(
        description="List of distinct search queries to find information relevant to the research task."
    )


async def _run_browser_search_tool(
        queries: List[str],
        task_id: str,  # Injected dependency
        llm: Any,  # Injected dependency
        browser_config: Dict[str, Any],
        stop_event: threading.Event,
        max_parallel_browsers: int = 1,
) -> List[Dict[str, Any]]:
    """
    Internal function to execute parallel browser searches based on LLM-provided queries.
    Handles concurrency and stop signals.
    """

    # Limit queries just in case LLM ignores the description
    queries = queries[:max_parallel_browsers]
    logger.info(
        f"[Browser Tool {task_id}] Running search for {len(queries)} queries: {queries}"
    )

    results = []
    semaphore = asyncio.Semaphore(max_parallel_browsers)

    async def task_wrapper(query):
        async with semaphore:
            if stop_event.is_set():
                logger.info(
                    f"[Browser Tool {task_id}] Skipping task due to stop signal: {query}"
                )
                return {"query": query, "result": None, "status": "cancelled"}
            # Pass necessary injected configs and the stop event
            return await run_single_browser_task(
                query,
                task_id,
                llm,  # Pass the main LLM (or a dedicated one if needed)
                browser_config,
                stop_event,
                # use_vision could be added here if needed
            )

    tasks = [task_wrapper(query) for query in queries]
    search_results = await asyncio.gather(*tasks, return_exceptions=True)

    processed_results = []
    for i, res in enumerate(search_results):
        query = queries[i]  # Get corresponding query
        if isinstance(res, Exception):
            logger.error(
                f"[Browser Tool {task_id}] Gather caught exception for query '{query}': {res}",
                exc_info=True,
            )
            processed_results.append(
                {"query": query, "error": str(res), "status": "failed"}
            )
        elif isinstance(res, dict):
            processed_results.append(res)
        else:
            logger.error(
                f"[Browser Tool {task_id}] Unexpected result type for query '{query}': {type(res)}"
            )
            processed_results.append(
                {"query": query, "error": "Unexpected result type", "status": "failed"}
            )

    logger.info(
        f"[Browser Tool {task_id}] Finished search. Results count: {len(processed_results)}"
    )
    return processed_results


def create_browser_search_tool(
        llm: Any,
        browser_config: Dict[str, Any],
        task_id: str,
        stop_event: threading.Event,
        max_parallel_browsers: int = 1,
) -> StructuredTool:
    """Factory function to create the browser search tool with necessary dependencies."""
    # Use partial to bind the dependencies that aren't part of the LLM call arguments
    from functools import partial

    bound_tool_func = partial(
        _run_browser_search_tool,
        task_id=task_id,
        llm=llm,
        browser_config=browser_config,
        stop_event=stop_event,
        max_parallel_browsers=max_parallel_browsers,
    )

    return StructuredTool.from_function(
        coroutine=bound_tool_func,
        name="parallel_browser_search",
        description=f"""Use this tool to actively search the web for information related to a specific research task or question.
It runs up to {max_parallel_browsers} searches in parallel using a browser agent for better results than simple scraping.
Provide a list of distinct search queries(up to {max_parallel_browsers}) that are likely to yield relevant information.""",
        args_schema=BrowserSearchInput,
    )


# --- Langgraph State Definition ---


class ResearchTaskItem(TypedDict):
    # step: int # Maybe step within category, or just implicit by order
    task_description: str
    status: str  # "pending", "completed", "failed"
    queries: Optional[List[str]]
    result_summary: Optional[str]


class ResearchCategoryItem(TypedDict):
    category_name: str
    tasks: List[ResearchTaskItem]
    # Optional: category_status: str # Could be "pending", "in_progress", "completed"


class DeepResearchState(TypedDict):
    task_id: str
    topic: str
    research_plan: List[ResearchCategoryItem]  # CHANGED
    search_results: List[Dict[str, Any]]
    llm: Any
    tools: List[Tool]
    output_dir: Path
    browser_config: Dict[str, Any]
    final_report: Optional[str]
    current_category_index: int
    current_task_index_in_category: int
    stop_requested: bool
    error_message: Optional[str]
    messages: List[BaseMessage]


# --- Langgraph Nodes ---


def _load_previous_state(task_id: str, output_dir: str) -> Dict[str, Any]:
    state_updates = {}
    plan_file = os.path.join(output_dir, PLAN_FILENAME)
    search_file = os.path.join(output_dir, SEARCH_INFO_FILENAME)

    loaded_plan: List[ResearchCategoryItem] = []
    next_cat_idx, next_task_idx = 0, 0
    found_pending = False

    if os.path.exists(plan_file):
        try:
            with open(plan_file, "r", encoding="utf-8") as f:
                current_category: Optional[ResearchCategoryItem] = None
                lines = f.readlines()
                cat_counter = 0
                task_counter_in_cat = 0

                for line_num, line_content in enumerate(lines):
                    line = line_content.strip()
                    if line.startswith("## "):  # Category
                        if current_category:  # Save previous category
                            loaded_plan.append(current_category)
                            if not found_pending:  # If previous category was all done, advance cat counter
                                cat_counter += 1
                                task_counter_in_cat = 0
                        category_name = line[line.find(" "):].strip()  # Get text after "## X. "
                        current_category = ResearchCategoryItem(category_name=category_name, tasks=[])
                    elif (line.startswith("- [ ]") or line.startswith("- [x]") or line.startswith(
                            "- [-]")) and current_category:  # Task
                        status = "pending"
                        if line.startswith("- [x]"):
                            status = "completed"
                        elif line.startswith("- [-]"):
                            status = "failed"

                        task_desc = line[5:].strip()
                        current_category["tasks"].append(
                            ResearchTaskItem(task_description=task_desc, status=status, queries=None,
                                             result_summary=None)
                        )
                        if status == "pending" and not found_pending:
                            next_cat_idx = cat_counter
                            next_task_idx = task_counter_in_cat
                            found_pending = True
                        if not found_pending:  # only increment if previous tasks were completed/failed
                            task_counter_in_cat += 1

                if current_category:  # Append last category
                    loaded_plan.append(current_category)

            if loaded_plan:
                state_updates["research_plan"] = loaded_plan
                if not found_pending and loaded_plan:  # All tasks were completed or failed
                    next_cat_idx = len(loaded_plan)  # Points beyond the last category
                    next_task_idx = 0
                state_updates["current_category_index"] = next_cat_idx
                state_updates["current_task_index_in_category"] = next_task_idx
                logger.info(
                    f"Loaded hierarchical research plan from {plan_file}. "
                    f"Next task: Category {next_cat_idx}, Task {next_task_idx} in category."
                )
            else:
                logger.warning(f"Plan file {plan_file} was empty or malformed.")

        except Exception as e:
            logger.error(f"Failed to load or parse research plan {plan_file}: {e}", exc_info=True)
            state_updates["error_message"] = f"Failed to load research plan: {e}"
    else:
        logger.info(f"Plan file {plan_file} not found. Will start fresh.")

    if os.path.exists(search_file):
        try:
            with open(search_file, "r", encoding="utf-8") as f:
                state_updates["search_results"] = json.load(f)
                logger.info(f"Loaded search results from {search_file}")
        except Exception as e:
            logger.error(f"Failed to load search results {search_file}: {e}")
            state_updates["error_message"] = (
                    state_updates.get("error_message", "") + f" Failed to load search results: {e}").strip()

    return state_updates


def _save_plan_to_md(plan: List[ResearchCategoryItem], output_dir: str):
    plan_file = os.path.join(output_dir, PLAN_FILENAME)
    try:
        with open(plan_file, "w", encoding="utf-8") as f:
            f.write(f"# Research Plan\n\n")
            for cat_idx, category in enumerate(plan):
                f.write(f"## {cat_idx + 1}. {category['category_name']}\n\n")
                for task_idx, task in enumerate(category['tasks']):
                    marker = "- [x]" if task["status"] == "completed" else "- [ ]" if task[
                                                                                          "status"] == "pending" else "- [-]"  # [-] for failed
                    f.write(f"  {marker} {task['task_description']}\n")
                f.write("\n")
        logger.info(f"Hierarchical research plan saved to {plan_file}")
    except Exception as e:
        logger.error(f"Failed to save research plan to {plan_file}: {e}")


def _save_search_results_to_json(results: List[Dict[str, Any]], output_dir: str):
    """Appends or overwrites search results to a JSON file."""
    search_file = os.path.join(output_dir, SEARCH_INFO_FILENAME)
    try:
        # Simple overwrite for now, could be append
        with open(search_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"Search results saved to {search_file}")
    except Exception as e:
        logger.error(f"Failed to save search results to {search_file}: {e}")


def _save_report_to_md(report: str, output_dir: Path):
    """Saves the final report to a markdown file."""
    report_file = os.path.join(output_dir, REPORT_FILENAME)
    try:
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)
        logger.info(f"Final report saved to {report_file}")
    except Exception as e:
        logger.error(f"Failed to save final report to {report_file}: {e}")


async def planning_node(state: DeepResearchState) -> Dict[str, Any]:
    logger.info("--- Entering Planning Node ---")
    if state.get("stop_requested"):
        logger.info("Stop requested, skipping planning.")
        return {"stop_requested": True}

    llm = state["llm"]
    topic = state["topic"]
    existing_plan = state.get("research_plan")
    output_dir = state["output_dir"]

    if existing_plan and (
            state.get("current_category_index", 0) > 0 or state.get("current_task_index_in_category", 0) > 0):
        logger.info("Resuming with existing plan.")
        _save_plan_to_md(existing_plan, output_dir)  # Ensure it's saved initially
        # current_category_index and current_task_index_in_category should be set by _load_previous_state
        return {"research_plan": existing_plan}

    logger.info(f"Generating new research plan for topic: {topic}")

    prompt_text = f"""You are a meticulous research assistant. Your goal is to create a hierarchical research plan to thoroughly investigate the topic: "{topic}".
The plan should be structured into several main research categories. Each category should contain a list of specific, actionable research tasks or questions.
Format the output as a JSON list of objects. Each object represents a research category and should have:
1. "category_name": A string for the name of the research category.
2. "tasks": A list of strings, where each string is a specific research task for that category.

Example JSON Output:
[
  {{
    "category_name": "Understanding Core Concepts and Definitions",
    "tasks": [
      "Define the primary terminology associated with '{topic}'.",
      "Identify the fundamental principles and theories underpinning '{topic}'."
    ]
  }},
  {{
    "category_name": "Historical Development and Key Milestones",
    "tasks": [
      "Trace the historical evolution of '{topic}'.",
      "Identify key figures, events, or breakthroughs in the development of '{topic}'."
    ]
  }},
  {{
    "category_name": "Current State-of-the-Art and Applications",
    "tasks": [
      "Analyze the current advancements and prominent applications of '{topic}'.",
      "Investigate ongoing research and active areas of development related to '{topic}'."
    ]
  }},
  {{
    "category_name": "Challenges, Limitations, and Future Outlook",
    "tasks": [
      "Identify the major challenges and limitations currently facing '{topic}'.",
      "Explore potential future trends, ethical considerations, and societal impacts of '{topic}'."
    ]
  }}
]

Generate a plan with 3-10 categories, and 2-6 tasks per category for the topic: "{topic}" according to the complexity of the topic.
Ensure the output is a valid JSON array.
"""
    messages = [
        SystemMessage(content="You are a research planning assistant outputting JSON."),
        HumanMessage(content=prompt_text)
    ]

    try:
        response = await llm.ainvoke(messages)
        raw_content = response.content
        # The LLM might wrap the JSON in backticks
        if raw_content.strip().startswith("```json"):
            raw_content = raw_content.strip()[7:-3].strip()
        elif raw_content.strip().startswith("```"):
            raw_content = raw_content.strip()[3:-3].strip()

        logger.debug(f"LLM response for plan: {raw_content}")
        parsed_plan_from_llm = json.loads(raw_content)

        new_plan: List[ResearchCategoryItem] = []
        for cat_idx, category_data in enumerate(parsed_plan_from_llm):
            if not isinstance(category_data,
                              dict) or "category_name" not in category_data or "tasks" not in category_data:
                logger.warning(f"Skipping invalid category data: {category_data}")
                continue

            tasks: List[ResearchTaskItem] = []
            for task_idx, task_desc in enumerate(category_data["tasks"]):
                if isinstance(task_desc, str):
                    tasks.append(
                        ResearchTaskItem(
                            task_description=task_desc,
                            status="pending",
                            queries=None,
                            result_summary=None,
                        )
                    )
                else:  # Sometimes LLM puts tasks as {"task": "description"}
                    if isinstance(task_desc, dict) and "task_description" in task_desc:
                        tasks.append(
                            ResearchTaskItem(
                                task_description=task_desc["task_description"],
                                status="pending",
                                queries=None,
                                result_summary=None,
                            )
                        )
                    elif isinstance(task_desc, dict) and "task" in task_desc:  # common LLM mistake
                        tasks.append(
                            ResearchTaskItem(
                                task_description=task_desc["task"],
                                status="pending",
                                queries=None,
                                result_summary=None,
                            )
                        )
                    else:
                        logger.warning(
                            f"Skipping invalid task data: {task_desc} in category {category_data['category_name']}")

            new_plan.append(
                ResearchCategoryItem(
                    category_name=category_data["category_name"],
                    tasks=tasks,
                )
            )

        if not new_plan:
            logger.error("LLM failed to generate a valid plan structure from JSON.")
            return {"error_message": "Failed to generate research plan structure."}

        logger.info(f"Generated research plan with {len(new_plan)} categories.")
        _save_plan_to_md(new_plan, output_dir)  # Save the hierarchical plan

        return {
            "research_plan": new_plan,
            "current_category_index": 0,
            "current_task_index_in_category": 0,
            "search_results": [],
        }

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from LLM for plan: {e}. Response was: {raw_content}", exc_info=True)
        return {"error_message": f"LLM generated invalid JSON for research plan: {e}"}
    except Exception as e:
        logger.error(f"Error during planning: {e}", exc_info=True)
        return {"error_message": f"LLM Error during planning: {e}"}


async def research_execution_node(state: DeepResearchState) -> Dict[str, Any]:
    logger.info("--- Entering Research Execution Node ---")
    if state.get("stop_requested"):
        logger.info("Stop requested, skipping research execution.")
        return {
            "stop_requested": True,
            "current_category_index": state["current_category_index"],
            "current_task_index_in_category": state["current_task_index_in_category"],
        }

    plan = state["research_plan"]
    cat_idx = state["current_category_index"]
    task_idx = state["current_task_index_in_category"]
    llm = state["llm"]
    tools = state["tools"]
    output_dir = str(state["output_dir"])
    task_id = state["task_id"]  # For _AGENT_STOP_FLAGS

    # This check should ideally be handled by `should_continue`
    if not plan or cat_idx >= len(plan):
        logger.info("Research plan complete or categories exhausted.")
        return {}  # should route to synthesis

    current_category = plan[cat_idx]
    if task_idx >= len(current_category["tasks"]):
        logger.info(f"All tasks in category '{current_category['category_name']}' completed. Moving to next category.")
        # This logic is now effectively handled by should_continue and the index updates below
        # The next iteration will be caught by should_continue or this node with updated indices
        return {
            "current_category_index": cat_idx + 1,
            "current_task_index_in_category": 0,
            "messages": state["messages"]  # Pass messages along
        }

    current_task = current_category["tasks"][task_idx]

    if current_task["status"] == "completed":
        logger.info(
            f"Task '{current_task['task_description']}' in category '{current_category['category_name']}' already completed. Skipping.")
        # Logic to find next task
        next_task_idx = task_idx + 1
        next_cat_idx = cat_idx
        if next_task_idx >= len(current_category["tasks"]):
            next_cat_idx += 1
            next_task_idx = 0
        return {
            "current_category_index": next_cat_idx,
            "current_task_index_in_category": next_task_idx,
            "messages": state["messages"]  # Pass messages along
        }

    logger.info(
        f"Executing research task: '{current_task['task_description']}' (Category: '{current_category['category_name']}')"
    )

    llm_with_tools = llm.bind_tools(tools)

    # Construct messages for LLM invocation
    task_prompt_content = (
        f"Current Research Category: {current_category['category_name']}\n"
        f"Specific Task: {current_task['task_description']}\n\n"
        "Please use the available tools, especially 'parallel_browser_search', to gather information for this specific task. "
        "Provide focused search queries relevant ONLY to this task. "
        "If you believe you have sufficient information from previous steps for this specific task, you can indicate that you are ready to summarize or that no further search is needed."
    )
    current_task_message_history = [
        HumanMessage(content=task_prompt_content)
    ]
    if not state["messages"]:  # First actual execution message
        invocation_messages = [
                                  SystemMessage(
                                      content="You are a research assistant executing one task of a research plan. Focus on the current task only."),
                              ] + current_task_message_history
    else:
        invocation_messages = state["messages"] + current_task_message_history

    try:
        logger.info(f"Invoking LLM with tools for task: {current_task['task_description']}")
        ai_response: BaseMessage = await llm_with_tools.ainvoke(invocation_messages)
        logger.info("LLM invocation complete.")

        tool_results = []
        executed_tool_names = []
        current_search_results = state.get("search_results", [])  # Get existing search results

        if not isinstance(ai_response, AIMessage) or not ai_response.tool_calls:
            logger.warning(
                f"LLM did not call any tool for task '{current_task['task_description']}'. Response: {ai_response.content[:100]}..."
            )
            current_task["status"] = "pending"  # Or "completed_no_tool" if LLM explains it's done
            current_task["result_summary"] = f"LLM did not use a tool. Response: {ai_response.content}"
            current_task["current_category_index"] = cat_idx
            current_task["current_task_index_in_category"] = task_idx
            return current_task
            # We still save the plan and advance.
        else:
            # Process tool calls
            for tool_call in ai_response.tool_calls:
                tool_name = tool_call.get("name")
                tool_args = tool_call.get("args", {})
                tool_call_id = tool_call.get("id")

                logger.info(f"LLM requested tool call: {tool_name} with args: {tool_args}")
                executed_tool_names.append(tool_name)
                selected_tool = next((t for t in tools if t.name == tool_name), None)

                if not selected_tool:
                    logger.error(f"LLM called tool '{tool_name}' which is not available.")
                    tool_results.append(
                        ToolMessage(content=f"Error: Tool '{tool_name}' not found.", tool_call_id=tool_call_id))
                    continue

                try:
                    stop_event = _AGENT_STOP_FLAGS.get(task_id)
                    if stop_event and stop_event.is_set():
                        logger.info(f"Stop requested before executing tool: {tool_name}")
                        current_task["status"] = "pending"  # Or a new "stopped" status
                        _save_plan_to_md(plan, output_dir)
                        return {"stop_requested": True, "research_plan": plan, "current_category_index": cat_idx,
                                "current_task_index_in_category": task_idx}

                    logger.info(f"Executing tool: {tool_name}")
                    tool_output = await selected_tool.ainvoke(tool_args)
                    logger.info(f"Tool '{tool_name}' executed successfully.")

                    if tool_name == "parallel_browser_search":
                        current_search_results.extend(tool_output)  # tool_output is List[Dict]
                    else:  # For other tools, we might need specific handling or just log
                        logger.info(f"Result from tool '{tool_name}': {str(tool_output)[:200]}...")
                        # Storing non-browser results might need a different structure or key in search_results
                        current_search_results.append(
                            {"tool_name": tool_name, "args": tool_args, "output": str(tool_output),
                             "status": "completed"})

                    tool_results.append(ToolMessage(content=json.dumps(tool_output), tool_call_id=tool_call_id))

                except Exception as e:
                    logger.error(f"Error executing tool '{tool_name}': {e}", exc_info=True)
                    tool_results.append(
                        ToolMessage(content=f"Error executing tool {tool_name}: {e}", tool_call_id=tool_call_id))
                    current_search_results.append(
                        {"tool_name": tool_name, "args": tool_args, "status": "failed", "error": str(e)})

            # After processing all tool calls for this task
            step_failed_tool_execution = any("Error:" in str(tr.content) for tr in tool_results)
            # Consider a task successful if a browser search was attempted and didn't immediately error out during call
            # The browser search itself returns status for each query.
            browser_tool_attempted_successfully = "parallel_browser_search" in executed_tool_names and not step_failed_tool_execution

            if step_failed_tool_execution:
                current_task["status"] = "failed"
                current_task[
                    "result_summary"] = f"Tool execution failed. Errors: {[tr.content for tr in tool_results if 'Error' in str(tr.content)]}"
            elif executed_tool_names:  # If any tool was called
                current_task["status"] = "completed"
                current_task["result_summary"] = f"Executed tool(s): {', '.join(executed_tool_names)}."
                # TODO: Could ask LLM to summarize the tool_results for this task if needed, rather than just listing tools.
            else:  # No tool calls but AI response had .tool_calls structure (empty)
                current_task["status"] = "failed"  # Or a more specific status
                current_task["result_summary"] = "LLM prepared for tool call but provided no tools."

        # Save progress
        _save_plan_to_md(plan, output_dir)
        _save_search_results_to_json(current_search_results, output_dir)

        # Determine next indices
        next_task_idx = task_idx + 1
        next_cat_idx = cat_idx
        if next_task_idx >= len(current_category["tasks"]):
            next_cat_idx += 1
            next_task_idx = 0

        updated_messages = state["messages"] + current_task_message_history + [ai_response] + tool_results

        return {
            "research_plan": plan,
            "search_results": current_search_results,
            "current_category_index": next_cat_idx,
            "current_task_index_in_category": next_task_idx,
            "messages": updated_messages,
        }

    except Exception as e:
        logger.error(f"Unhandled error during research execution for task '{current_task['task_description']}': {e}",
                     exc_info=True)
        current_task["status"] = "failed"
        _save_plan_to_md(plan, output_dir)
        # Determine next indices even on error to attempt to move on
        next_task_idx = task_idx + 1
        next_cat_idx = cat_idx
        if next_task_idx >= len(current_category["tasks"]):
            next_cat_idx += 1
            next_task_idx = 0
        return {
            "research_plan": plan,
            "current_category_index": next_cat_idx,
            "current_task_index_in_category": next_task_idx,
            "error_message": f"Core Execution Error on task '{current_task['task_description']}': {e}",
            "messages": state["messages"] + current_task_message_history  # Preserve messages up to error
        }


async def synthesis_node(state: DeepResearchState) -> Dict[str, Any]:
    """Synthesizes the final report from the collected search results."""
    logger.info("--- Entering Synthesis Node ---")
    if state.get("stop_requested"):
        logger.info("Stop requested, skipping synthesis.")
        return {"stop_requested": True}

    llm = state["llm"]
    topic = state["topic"]
    search_results = state.get("search_results", [])
    output_dir = state["output_dir"]
    plan = state["research_plan"]  # Include plan for context

    if not search_results:
        logger.warning("No search results found to synthesize report.")
        report = f"# Research Report: {topic}\n\nNo information was gathered during the research process."
        _save_report_to_md(report, output_dir)
        return {"final_report": report}

    logger.info(
        f"Synthesizing report from {len(search_results)} collected search result entries."
    )

    # Prepare context for the LLM
    # Format search results nicely, maybe group by query or original plan step
    formatted_results = ""
    references = {}
    ref_count = 1
    for i, result_entry in enumerate(search_results):
        query = result_entry.get("query", "Unknown Query")  # From parallel_browser_search
        tool_name = result_entry.get("tool_name")  # From other tools
        status = result_entry.get("status", "unknown")
        result_data = result_entry.get("result")  # From BrowserUseAgent's final_result
        tool_output_str = result_entry.get("output")  # From other tools

        if tool_name == "parallel_browser_search" and status == "completed" and result_data:
            # result_data is the summary from BrowserUseAgent
            formatted_results += f'### Finding from Web Search Query: "{query}"\n'
            formatted_results += f"- **Summary:**\n{result_data}\n"  # result_data is already a summary string here
            # If result_data contained title/URL, you'd format them here.
            # The current BrowserUseAgent returns a string summary directly as 'final_data' in run_single_browser_task
            formatted_results += "---\n"
        elif tool_name != "parallel_browser_search" and status == "completed" and tool_output_str:
            formatted_results += f'### Finding from Tool: "{tool_name}" (Args: {result_entry.get("args")})\n'
            formatted_results += f"- **Output:**\n{tool_output_str}\n"
            formatted_results += "---\n"
        elif status == "failed":
            error = result_entry.get("error")
            q_or_t = f"Query: \"{query}\"" if query != "Unknown Query" else f"Tool: \"{tool_name}\""
            formatted_results += f'### Failed {q_or_t}\n'
            formatted_results += f"- **Error:** {error}\n"
            formatted_results += "---\n"

    # Prepare the research plan context
    plan_summary = "\nResearch Plan Followed:\n"
    for cat_idx, category in enumerate(plan):
        plan_summary += f"\n#### Category {cat_idx + 1}: {category['category_name']}\n"
        for task_idx, task in enumerate(category['tasks']):
            marker = "[x]" if task["status"] == "completed" else "[ ]" if task["status"] == "pending" else "[-]"
            plan_summary += f"  - {marker} {task['task_description']}\n"

    synthesis_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are a professional researcher tasked with writing a comprehensive and well-structured report based on collected findings.
        The report should address the research topic thoroughly, synthesizing the information gathered from various sources.
        Structure the report logically:
        1.  Briefly introduce the topic and the report's scope (mentioning the research plan followed, including categories and tasks, is good).
        2.  Discuss the key findings, organizing them thematically, possibly aligning with the research categories. Analyze, compare, and contrast information.
        3.  Summarize the main points and offer concluding thoughts.

        Ensure the tone is objective and professional.
        If findings are contradictory or incomplete, acknowledge this.
        """,  # Removed citation part for simplicity for now, as browser agent returns summaries.
            ),
            (
                "human",
                f"""
            **Research Topic:** {topic}

            {plan_summary}

            **Collected Findings:**
            ```
            {formatted_results}
            ```

            Please generate the final research report in Markdown format based **only** on the information above.
            """,
            ),
        ]
    )

    try:
        response = await llm.ainvoke(
            synthesis_prompt.format_prompt(
                topic=topic,
                plan_summary=plan_summary,
                formatted_results=formatted_results,
            ).to_messages()
        )
        final_report_md = response.content

        # Append the reference list automatically to the end of the generated markdown
        if references:
            report_references_section = "\n\n## References\n\n"
            # Sort refs by ID for consistent output
            sorted_refs = sorted(references.values(), key=lambda x: x["id"])
            for ref in sorted_refs:
                report_references_section += (
                    f"[{ref['id']}] {ref['title']} - {ref['url']}\n"
                )
            final_report_md += report_references_section

        logger.info("Successfully synthesized the final report.")
        _save_report_to_md(final_report_md, output_dir)
        return {"final_report": final_report_md}

    except Exception as e:
        logger.error(f"Error during report synthesis: {e}", exc_info=True)
        return {"error_message": f"LLM Error during synthesis: {e}"}


# --- Langgraph Edges and Conditional Logic ---


def should_continue(state: DeepResearchState) -> str:
    logger.info("--- Evaluating Condition: Should Continue? ---")
    if state.get("stop_requested"):
        logger.info("Stop requested, routing to END.")
        return "end_run"
    if state.get("error_message") and "Core Execution Error" in state["error_message"]:  # Critical error in node
        logger.warning(f"Critical error detected: {state['error_message']}. Routing to END.")
        return "end_run"

    plan = state.get("research_plan")
    cat_idx = state.get("current_category_index", 0)
    task_idx = state.get("current_task_index_in_category", 0)  # This is the *next* task to check

    if not plan:
        logger.warning("No research plan found. Routing to END.")
        return "end_run"

    # Check if the current indices point to a valid pending task
    if cat_idx < len(plan):
        current_category = plan[cat_idx]
        if task_idx < len(current_category["tasks"]):
            # We are trying to execute the task at plan[cat_idx]["tasks"][task_idx]
            # The research_execution_node will handle if it's already completed.
            logger.info(
                f"Plan has potential pending tasks (next up: Category {cat_idx}, Task {task_idx}). Routing to Research Execution."
            )
            return "execute_research"
        else:  # task_idx is out of bounds for current category, means we need to check next category
            if cat_idx + 1 < len(plan):  # If there is a next category
                logger.info(
                    f"Finished tasks in category {cat_idx}. Moving to category {cat_idx + 1}. Routing to Research Execution."
                )
                # research_execution_node will update state to {current_category_index: cat_idx + 1, current_task_index_in_category: 0}
                # Or rather, the previous execution node already set these indices to the start of the next category.
                return "execute_research"

    # If we've gone through all categories and tasks (cat_idx >= len(plan))
    logger.info("All plan categories and tasks processed or current indices are out of bounds. Routing to Synthesis.")
    return "synthesize_report"


# --- DeepSearchAgent Class ---


class DeepResearchAgent:
    def __init__(
            self,
            llm: Any,
            browser_config: Dict[str, Any],
            mcp_server_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initializes the DeepSearchAgent.

        Args:
            llm: The Langchain compatible language model instance.
            browser_config: Configuration dictionary for the BrowserUseAgent tool.
                            Example: {"headless": True, "window_width": 1280, ...}
            mcp_server_config: Optional configuration for the MCP client.
        """
        self.llm = llm
        self.browser_config = browser_config
        self.mcp_server_config = mcp_server_config
        self.mcp_client = None
        self.stopped = False
        self.graph = self._compile_graph()
        self.current_task_id: Optional[str] = None
        self.stop_event: Optional[threading.Event] = None
        self.runner: Optional[asyncio.Task] = None  # To hold the asyncio task for run

    async def _setup_tools(
            self, task_id: str, stop_event: threading.Event, max_parallel_browsers: int = 1
    ) -> List[Tool]:
        """Sets up the basic tools (File I/O) and optional MCP tools."""
        tools = [
            WriteFileTool(),
            ReadFileTool(),
            ListDirectoryTool(),
        ]  # Basic file operations
        browser_use_tool = create_browser_search_tool(
            llm=self.llm,
            browser_config=self.browser_config,
            task_id=task_id,
            stop_event=stop_event,
            max_parallel_browsers=max_parallel_browsers,
        )
        tools += [browser_use_tool]
        # Add MCP tools if config is provided
        if self.mcp_server_config:
            try:
                logger.info("Setting up MCP client and tools...")
                if not self.mcp_client:
                    self.mcp_client = await setup_mcp_client_and_tools(
                        self.mcp_server_config
                    )
                mcp_tools = self.mcp_client.get_tools()
                logger.info(f"Loaded {len(mcp_tools)} MCP tools.")
                tools.extend(mcp_tools)
            except Exception as e:
                logger.error(f"Failed to set up MCP tools: {e}", exc_info=True)
        elif self.mcp_server_config:
            logger.warning(
                "MCP server config provided, but setup function unavailable."
            )
        tools_map = {tool.name: tool for tool in tools}
        return tools_map.values()

    async def close_mcp_client(self):
        if self.mcp_client:
            await self.mcp_client.__aexit__(None, None, None)
            self.mcp_client = None

    def _compile_graph(self) -> StateGraph:
        """Compiles the Langgraph state machine."""
        workflow = StateGraph(DeepResearchState)

        # Add nodes
        workflow.add_node("plan_research", planning_node)
        workflow.add_node("execute_research", research_execution_node)
        workflow.add_node("synthesize_report", synthesis_node)
        workflow.add_node(
            "end_run", lambda state: logger.info("--- Reached End Run Node ---") or {}
        )  # Simple end node

        # Define edges
        workflow.set_entry_point("plan_research")

        workflow.add_edge(
            "plan_research", "execute_research"
        )  # Always execute after planning

        # Conditional edge after execution
        workflow.add_conditional_edges(
            "execute_research",
            should_continue,
            {
                "execute_research": "execute_research",  # Loop back if more steps
                "synthesize_report": "synthesize_report",  # Move to synthesis if done
                "end_run": "end_run",  # End if stop requested or error
            },
        )

        workflow.add_edge("synthesize_report", "end_run")  # End after synthesis

        app = workflow.compile()
        return app

    async def run(
            self,
            topic: str,
            task_id: Optional[str] = None,
            save_dir: str = "./tmp/deep_research",
            max_parallel_browsers: int = 1,
    ) -> Dict[str, Any]:
        """
        Starts the deep research process (Async Generator Version).

        Args:
            topic: The research topic.
            task_id: Optional existing task ID to resume. If None, a new ID is generated.

        Yields:
             Intermediate state updates or messages during execution.
        """
        if self.runner and not self.runner.done():
            logger.warning(
                "Agent is already running. Please stop the current task first."
            )
            # Return an error status instead of yielding
            return {
                "status": "error",
                "message": "Agent already running.",
                "task_id": self.current_task_id,
            }

        self.current_task_id = task_id if task_id else str(uuid.uuid4())
        safe_root_dir = "./tmp/deep_research"
        normalized_save_dir = os.path.normpath(save_dir)
        if not normalized_save_dir.startswith(os.path.abspath(safe_root_dir)):
            logger.warning(f"Unsafe save_dir detected: {save_dir}. Using default directory.")
            normalized_save_dir = os.path.abspath(safe_root_dir)
        output_dir = os.path.join(normalized_save_dir, self.current_task_id)
        os.makedirs(output_dir, exist_ok=True)

        logger.info(
            f"[AsyncGen] Starting research task ID: {self.current_task_id} for topic: '{topic}'"
        )
        logger.info(f"[AsyncGen] Output directory: {output_dir}")

        self.stop_event = threading.Event()
        _AGENT_STOP_FLAGS[self.current_task_id] = self.stop_event
        agent_tools = await self._setup_tools(
            self.current_task_id, self.stop_event, max_parallel_browsers
        )
        initial_state: DeepResearchState = {
            "task_id": self.current_task_id,
            "topic": topic,
            "research_plan": [],
            "search_results": [],
            "messages": [],
            "llm": self.llm,
            "tools": agent_tools,
            "output_dir": Path(output_dir),
            "browser_config": self.browser_config,
            "final_report": None,
            "current_category_index": 0,
            "current_task_index_in_category": 0,
            "stop_requested": False,
            "error_message": None,
        }

        if task_id:
            logger.info(f"Attempting to resume task {task_id}...")
            loaded_state = _load_previous_state(task_id, output_dir)
            initial_state.update(loaded_state)
            if loaded_state.get("research_plan"):
                logger.info(
                    f"Resuming with {len(loaded_state['research_plan'])} plan categories "
                    f"and {len(loaded_state.get('search_results', []))} existing results. "
                    f"Next task: Cat {initial_state['current_category_index']}, Task {initial_state['current_task_index_in_category']}"
                )
                initial_state["topic"] = (
                    topic  # Allow overriding topic even when resuming? Or use stored topic? Let's use new one.
                )
            else:
                logger.warning(
                    f"Resume requested for {task_id}, but no previous plan found. Starting fresh."
                )

        # --- Execute Graph using ainvoke ---
        final_state = None
        status = "unknown"
        message = None
        try:
            logger.info(f"Invoking graph execution for task {self.current_task_id}...")
            self.runner = asyncio.create_task(self.graph.ainvoke(initial_state))
            final_state = await self.runner
            logger.info(f"Graph execution finished for task {self.current_task_id}.")

            # Determine status based on final state
            if self.stop_event and self.stop_event.is_set():
                status = "stopped"
                message = "Research process was stopped by request."
                logger.info(message)
            elif final_state and final_state.get("error_message"):
                status = "error"
                message = final_state["error_message"]
                logger.error(f"Graph execution completed with error: {message}")
            elif final_state and final_state.get("final_report"):
                status = "completed"
                message = "Research process completed successfully."
                logger.info(message)
            else:
                # If it ends without error/report (e.g., empty plan, stopped before synthesis)
                status = "finished_incomplete"
                message = "Research process finished, but may be incomplete (no final report generated)."
                logger.warning(message)

        except asyncio.CancelledError:
            status = "cancelled"
            message = f"Agent run task cancelled for {self.current_task_id}."
            logger.info(message)
            # final_state will remain None or the state before cancellation if checkpointing was used
        except Exception as e:
            status = "error"
            message = f"Unhandled error during graph execution for {self.current_task_id}: {e}"
            logger.error(message, exc_info=True)
            # final_state will remain None or the state before the error
        finally:
            logger.info(f"Cleaning up resources for task {self.current_task_id}")
            task_id_to_clean = self.current_task_id

            self.stop_event = None
            self.current_task_id = None
            self.runner = None  # Mark runner as finished
            if self.mcp_client:
                await self.mcp_client.__aexit__(None, None, None)

            # Return a result dictionary including the status and the final state if available
            return {
                "status": status,
                "message": message,
                "task_id": task_id_to_clean,  # Use the stored task_id
                "final_state": final_state
                if final_state
                else {},  # Return the final state dict
            }

    async def _stop_lingering_browsers(self, task_id):
        """Attempts to stop any BrowserUseAgent instances associated with the task_id."""
        keys_to_stop = [
            key for key in _BROWSER_AGENT_INSTANCES if key.startswith(f"{task_id}_")
        ]
        if not keys_to_stop:
            return

        logger.warning(
            f"Found {len(keys_to_stop)} potentially lingering browser agents for task {task_id}. Attempting stop..."
        )
        for key in keys_to_stop:
            agent_instance = _BROWSER_AGENT_INSTANCES.get(key)
            try:
                if agent_instance:
                    # Assuming BU agent has an async stop method
                    await agent_instance.stop()
                    logger.info(f"Called stop() on browser agent instance {key}")
            except Exception as e:
                logger.error(
                    f"Error calling stop() on browser agent instance {key}: {e}"
                )

    async def stop(self):
        """Signals the currently running agent task to stop."""
        if not self.current_task_id or not self.stop_event:
            logger.info("No agent task is currently running.")
            return

        logger.info(f"Stop requested for task ID: {self.current_task_id}")
        self.stop_event.set()  # Signal the stop event
        self.stopped = True
        await self._stop_lingering_browsers(self.current_task_id)

    def close(self):
        self.stopped = False
