import asyncio
import copy
import json
import logging
import os
import re
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, TypedDict

from browser_use.browser.browser import BrowserConfig
from browser_use.browser.context import BrowserContextConfig
from langchain_community.tools.file_management import (
    ListDirectoryTool,
    ReadFileTool,
    WriteFileTool,
)
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool, StructuredTool
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

from src.agent.browser_use.browser_use_agent import BrowserUseAgent
from src.browser.custom_browser import CustomBrowser
from src.controller.custom_controller import CustomController
from src.utils.mcp_client import setup_mcp_client_and_tools

logger = logging.getLogger(__name__)

REPORT_FILENAME = "report.md"
PLAN_FILENAME = "research_plan.md"
SEARCH_INFO_FILENAME = "search_info.json"
DEFAULT_SAVE_ROOT = "./tmp/deep_research"
DOWNLOADS_DIR = "./tmp/downloads"
BROWSER_TOOL_NAME = "parallel_browser_search"

MAX_CATEGORIES = 10
MAX_TASKS_PER_CATEGORY = 6
MAX_QUERIES_PER_CALL = 5
MAX_PRIOR_SUMMARIES = 10
MAX_PRIOR_SUMMARY_CHARS = 500
MAX_TASK_FINDINGS_CHARS = 20_000
MAX_SYNTHESIS_FINDINGS_CHARS = 60_000

_BROWSER_AGENT_INSTANCES: Dict[str, BrowserUseAgent] = {}

_CATEGORY_RE = re.compile(r"^##\s+(?:\d+\.\s*)?(.+)$")
_TASK_RE = re.compile(r"^-\s\[([ x\-])\]\s+(.+)$")
_SUMMARY_RE = re.compile(r"^>\s?(.*)$")
_URL_RE = re.compile(r"https?://[^\s)\]>\"'<]+")
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
_STATUS_BY_MARKER = {" ": "pending", "x": "completed", "-": "failed"}
_MARKER_BY_STATUS = {status: marker for marker, status in _STATUS_BY_MARKER.items()}

BROWSER_TASK_PROMPT = """Research Task: {query}
Objective: Find relevant information answering the query.
Output Requirements: For each relevant piece of information found, provide:
1. A concise summary of the information.
2. The title of the source page or document.
3. The URL of the source.
Focus on accuracy and relevance. Avoid irrelevant details.
PDFs cannot be read directly: download them first, then use read_file. If saving or reading fails, try other methods."""

EXECUTION_SYSTEM_PROMPT = (
    "You are a research assistant executing one task of a larger research plan. "
    "Gather information for the current task only, using the provided tools."
)

SUMMARY_SYSTEM_PROMPT = (
    "You condense raw research findings into a short, factual summary. "
    "Keep source URLs inline next to the facts they support. Do not invent information."
)

SYNTHESIS_SYSTEM_PROMPT = """You are a professional researcher writing a comprehensive, well-structured report from collected findings.
Structure the report logically:
1. Briefly introduce the topic and the report's scope, mentioning the research plan that was followed.
2. Discuss the key findings thematically, aligned with the research categories where sensible. Analyze, compare, and contrast.
3. Summarize the main points and offer concluding thoughts.
Keep the tone objective and professional. Acknowledge contradictory or incomplete findings.
Cite sources inline as [n] using the numbered source list provided. Do not add a references section; it is appended automatically."""


class ResearchTaskItem(TypedDict):
    task_description: str
    status: str
    queries: Optional[List[str]]
    result_summary: Optional[str]


class ResearchCategoryItem(TypedDict):
    category_name: str
    tasks: List[ResearchTaskItem]


class DeepResearchState(TypedDict):
    task_id: str
    topic: str
    research_plan: List[ResearchCategoryItem]
    search_results: List[Dict[str, Any]]
    output_dir: str
    final_report: Optional[str]
    current_category_index: int
    current_task_index_in_category: int
    stop_requested: bool
    error_message: Optional[str]


class PlanCategory(BaseModel):
    category_name: str = Field(description="Name of the research category.")
    tasks: List[str] = Field(description="Specific, actionable research tasks for this category.")


class ResearchPlan(BaseModel):
    categories: List[PlanCategory]


class BrowserSearchInput(BaseModel):
    queries: List[str] = Field(
        description=f"Up to {MAX_QUERIES_PER_CALL} distinct search queries relevant to the current research task."
    )


def _content_text(message: BaseMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    parts = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "".join(parts)


def _strip_think(text: str) -> str:
    return _THINK_RE.sub("", text)


def _tool_name(result: Dict[str, Any]) -> Optional[str]:
    return result.get("tool_name") or (BROWSER_TOOL_NAME if "query" in result else None)


def _find_next_pending(plan: List[ResearchCategoryItem]) -> Optional[Tuple[int, int]]:
    for cat_idx, category in enumerate(plan):
        for task_idx, task in enumerate(category["tasks"]):
            if task["status"] == "pending":
                return cat_idx, task_idx
    return None


def _index_update(plan: List[ResearchCategoryItem]) -> Dict[str, int]:
    position = _find_next_pending(plan)
    cat_idx, task_idx = position if position else (len(plan), 0)
    return {"current_category_index": cat_idx, "current_task_index_in_category": task_idx}


def _is_stopped(state: DeepResearchState, stop_event: threading.Event) -> bool:
    return bool(state.get("stop_requested")) or stop_event.is_set()


def _resolve_output_dir(save_dir: str, task_id: str) -> Path:
    root = Path(DEFAULT_SAVE_ROOT).resolve()
    base = Path(save_dir).resolve()
    if not base.is_relative_to(root):
        logger.warning(f"Unsafe save_dir detected: {save_dir}. Using {root}.")
        base = root
    output_dir = (base / task_id).resolve()
    if output_dir == base or not output_dir.is_relative_to(base):
        raise ValueError(f"Invalid task_id: {task_id}")
    return output_dir


def _create_browser(browser_config: Dict[str, Any]) -> CustomBrowser:
    extra_args = []
    browser_binary_path = None
    if browser_config.get("use_own_browser", False):
        browser_binary_path = os.getenv("BROWSER_PATH") or browser_config.get("browser_binary_path") or None
        user_data_dir = browser_config.get("user_data_dir") or os.getenv("BROWSER_USER_DATA")
        if user_data_dir:
            extra_args.append(f"--user-data-dir={user_data_dir}")

    return CustomBrowser(
        config=BrowserConfig(
            headless=browser_config.get("headless", False),
            browser_binary_path=browser_binary_path,
            extra_browser_args=extra_args,
            wss_url=browser_config.get("wss_url"),
            cdp_url=browser_config.get("cdp_url"),
            new_context_config=BrowserContextConfig(
                window_width=browser_config.get("window_width", 1280),
                window_height=browser_config.get("window_height", 1100),
            ),
        )
    )


async def run_single_browser_task(
        task_query: str,
        task_id: str,
        llm: Any,
        browser: CustomBrowser,
        browser_config: Dict[str, Any],
        stop_event: threading.Event,
        use_vision: bool = False,
) -> Dict[str, Any]:
    base = {"tool_name": BROWSER_TOOL_NAME, "query": task_query}
    if stop_event.is_set():
        return {**base, "result": None, "status": "cancelled"}

    task_key = None
    context = None
    try:
        context = await browser.new_context(
            config=BrowserContextConfig(
                save_downloads_path=DOWNLOADS_DIR,
                window_width=browser_config.get("window_width", 1280),
                window_height=browser_config.get("window_height", 1100),
                force_new_context=True,
            )
        )
        agent = BrowserUseAgent(
            task=BROWSER_TASK_PROMPT.format(query=task_query),
            llm=llm,
            browser=browser,
            browser_context=context,
            controller=CustomController(),
            use_vision=use_vision,
            source="webui",
        )
        task_key = f"{task_id}_{uuid.uuid4()}"
        _BROWSER_AGENT_INSTANCES[task_key] = agent

        logger.info(f"Running BrowserUseAgent for: {task_query}")
        history = await agent.run()
        status = "stopped" if stop_event.is_set() else "completed"
        return {**base, "result": history.final_result(), "status": status}

    except Exception as e:
        logger.error(f"Error during browser task for query '{task_query}': {e}", exc_info=True)
        return {**base, "error": str(e), "status": "failed"}
    finally:
        if task_key:
            _BROWSER_AGENT_INSTANCES.pop(task_key, None)
        if context:
            try:
                await context.close()
            except Exception as e:
                logger.error(f"Error closing browser context: {e}")


async def _run_browser_search_tool(
        queries: List[str],
        task_id: str,
        llm: Any,
        browser_config: Dict[str, Any],
        stop_event: threading.Event,
        max_parallel_browsers: int = 1,
) -> List[Dict[str, Any]]:
    queries = [q for q in dict.fromkeys(q.strip() for q in queries) if q][:MAX_QUERIES_PER_CALL]
    if not queries:
        return []

    logger.info(f"[Browser Tool {task_id}] Running {len(queries)} queries: {queries}")
    semaphore = asyncio.Semaphore(max(1, max_parallel_browsers))
    browser = _create_browser(browser_config)

    async def guarded(query: str) -> Dict[str, Any]:
        async with semaphore:
            return await run_single_browser_task(query, task_id, llm, browser, browser_config, stop_event)

    try:
        raw_results = await asyncio.gather(*(guarded(q) for q in queries), return_exceptions=True)
    finally:
        try:
            await browser.close()
        except Exception as e:
            logger.error(f"Error closing browser: {e}")

    results = []
    for query, res in zip(queries, raw_results):
        if isinstance(res, dict):
            results.append(res)
        else:
            logger.error(f"[Browser Tool {task_id}] Query '{query}' raised: {res}")
            results.append({"tool_name": BROWSER_TOOL_NAME, "query": query, "error": str(res), "status": "failed"})
    return results


def create_browser_search_tool(
        llm: Any,
        browser_config: Dict[str, Any],
        task_id: str,
        stop_event: threading.Event,
        max_parallel_browsers: int = 1,
) -> StructuredTool:
    async def search(queries: List[str]) -> List[Dict[str, Any]]:
        return await _run_browser_search_tool(
            queries, task_id, llm, browser_config, stop_event, max_parallel_browsers
        )

    return StructuredTool.from_function(
        coroutine=search,
        name=BROWSER_TOOL_NAME,
        description=(
            "Actively search the web for information related to the current research task using a browser agent. "
            f"Accepts up to {MAX_QUERIES_PER_CALL} distinct queries; up to {max_parallel_browsers} run in parallel."
        ),
        args_schema=BrowserSearchInput,
    )


def _save_plan_to_md(plan: List[ResearchCategoryItem], output_dir: str) -> None:
    lines = ["# Research Plan", ""]
    for cat_idx, category in enumerate(plan, 1):
        lines += [f"## {cat_idx}. {category['category_name']}", ""]
        for task in category["tasks"]:
            lines.append(f"- [{_MARKER_BY_STATUS.get(task['status'], ' ')}] {task['task_description']}")
            if task.get("result_summary"):
                summary = " ".join(task["result_summary"].split())
                lines.append(f"  > {summary}")
        lines.append("")
    try:
        (Path(output_dir) / PLAN_FILENAME).write_text("\n".join(lines), encoding="utf-8")
    except Exception as e:
        logger.error(f"Failed to save research plan: {e}")


def _save_search_results_to_json(results: List[Dict[str, Any]], output_dir: str) -> None:
    try:
        (Path(output_dir) / SEARCH_INFO_FILENAME).write_text(
            json.dumps(results, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
        )
    except Exception as e:
        logger.error(f"Failed to save search results: {e}")


def _save_report_to_md(report: str, output_dir: str) -> None:
    try:
        (Path(output_dir) / REPORT_FILENAME).write_text(report, encoding="utf-8")
        logger.info(f"Final report saved to {output_dir}")
    except Exception as e:
        logger.error(f"Failed to save final report: {e}")


def _load_previous_state(output_dir: Path) -> Dict[str, Any]:
    updates: Dict[str, Any] = {}

    plan_file = output_dir / PLAN_FILENAME
    if plan_file.exists():
        try:
            plan: List[ResearchCategoryItem] = []
            for raw_line in plan_file.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if match := _CATEGORY_RE.match(line):
                    plan.append(ResearchCategoryItem(category_name=match.group(1).strip(), tasks=[]))
                elif (match := _TASK_RE.match(line)) and plan:
                    plan[-1]["tasks"].append(
                        ResearchTaskItem(
                            task_description=match.group(2).strip(),
                            status=_STATUS_BY_MARKER[match.group(1)],
                            queries=None,
                            result_summary=None,
                        )
                    )
                elif (match := _SUMMARY_RE.match(line)) and plan and plan[-1]["tasks"]:
                    plan[-1]["tasks"][-1]["result_summary"] = match.group(1).strip() or None

            plan = [c for c in plan if c["tasks"]]
            if plan:
                updates["research_plan"] = plan
                updates.update(_index_update(plan))
                logger.info(f"Loaded research plan with {len(plan)} categories from {plan_file}.")
            else:
                logger.warning(f"Plan file {plan_file} was empty or malformed. Starting fresh.")
        except Exception as e:
            logger.error(f"Failed to parse research plan {plan_file}: {e}. Starting fresh.", exc_info=True)

    search_file = output_dir / SEARCH_INFO_FILENAME
    if search_file.exists():
        try:
            updates["search_results"] = json.loads(search_file.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(f"Failed to load search results {search_file}: {e}")

    return updates


def _parse_plan_json(text: str) -> List[PlanCategory]:
    match = re.search(r"[\[{].*[\]}]", _strip_think(text), re.DOTALL)
    if not match:
        raise ValueError("No JSON found in planning response.")
    data = json.loads(match.group(0))
    if isinstance(data, dict):
        data = data.get("categories", [])

    categories = []
    for item in data:
        if not isinstance(item, dict) or "category_name" not in item:
            continue
        tasks = []
        for task in item.get("tasks", []):
            if isinstance(task, str):
                tasks.append(task)
            elif isinstance(task, dict):
                desc = task.get("task_description") or task.get("task")
                if isinstance(desc, str):
                    tasks.append(desc)
        categories.append(PlanCategory(category_name=str(item["category_name"]), tasks=tasks))
    return categories


async def _generate_plan(llm: Any, topic: str) -> List[PlanCategory]:
    prompt = f"""Create a hierarchical research plan to thoroughly investigate the topic: "{topic}".
Structure it into 3-{MAX_CATEGORIES} research categories, each with 2-{MAX_TASKS_PER_CATEGORY} specific, actionable research tasks, scaled to the topic's complexity.
Typical categories include core concepts and definitions, historical development, current state and applications, and challenges and future outlook, but adapt them to the topic."""
    messages = [SystemMessage(content="You are a meticulous research planning assistant."), HumanMessage(content=prompt)]

    try:
        result = await llm.with_structured_output(ResearchPlan).ainvoke(messages)
        if isinstance(result, ResearchPlan) and result.categories:
            return result.categories
    except Exception as e:
        logger.info(f"Structured output unavailable ({e}); falling back to JSON parsing.")

    json_instruction = (
        'Respond with JSON only, in the form: '
        '{"categories": [{"category_name": "...", "tasks": ["...", "..."]}]}'
    )
    response = await llm.ainvoke(messages + [HumanMessage(content=json_instruction)])
    return _parse_plan_json(_content_text(response))


async def planning_node(state: DeepResearchState, llm: Any, stop_event: threading.Event) -> Dict[str, Any]:
    logger.info("--- Entering Planning Node ---")
    if _is_stopped(state, stop_event):
        return {"stop_requested": True}

    output_dir = state["output_dir"]
    if state.get("research_plan"):
        logger.info("Resuming with existing plan.")
        _save_plan_to_md(state["research_plan"], output_dir)
        return _index_update(state["research_plan"])

    logger.info(f"Generating new research plan for topic: {state['topic']}")
    try:
        categories = await _generate_plan(llm, state["topic"])
    except Exception as e:
        logger.error(f"Error during planning: {e}", exc_info=True)
        return {"error_message": f"Planning failed: {e}"}

    plan: List[ResearchCategoryItem] = []
    for category in categories[:MAX_CATEGORIES]:
        tasks = [
            ResearchTaskItem(task_description=t.strip(), status="pending", queries=None, result_summary=None)
            for t in category.tasks[:MAX_TASKS_PER_CATEGORY]
            if t.strip()
        ]
        if category.category_name.strip() and tasks:
            plan.append(ResearchCategoryItem(category_name=category.category_name.strip(), tasks=tasks))

    if not plan:
        return {"error_message": "Failed to generate a valid research plan."}

    logger.info(f"Generated research plan with {len(plan)} categories.")
    _save_plan_to_md(plan, output_dir)
    return {"research_plan": plan, "search_results": [], **_index_update(plan)}


def _build_task_prompt(topic: str, plan: List[ResearchCategoryItem], category: ResearchCategoryItem,
                       task: ResearchTaskItem) -> str:
    prior = [
        f"- {t['task_description']}: {t['result_summary'][:MAX_PRIOR_SUMMARY_CHARS]}"
        for c in plan
        for t in c["tasks"]
        if t["status"] == "completed" and t.get("result_summary")
    ][-MAX_PRIOR_SUMMARIES:]
    prior_text = "\n".join(prior) or "None yet."
    return (
        f"Research topic: {topic}\n"
        f"Current category: {category['category_name']}\n"
        f"Current task: {task['task_description']}\n\n"
        f"Findings from earlier tasks:\n{prior_text}\n\n"
        f"Use the '{BROWSER_TOOL_NAME}' tool with focused queries relevant only to the current task. "
        "Avoid repeating searches already covered by earlier findings."
    )


def _format_results_for_llm(results: List[Dict[str, Any]]) -> str:
    parts = []
    for r in results:
        name = _tool_name(r)
        status = r.get("status")
        if name == BROWSER_TOOL_NAME:
            if status == "completed" and r.get("result"):
                parts.append(f'### Web search: "{r.get("query")}"\n{r["result"]}')
            elif status == "failed":
                parts.append(f'### Failed web search: "{r.get("query")}"\nError: {r.get("error")}')
        elif status == "completed" and r.get("output"):
            parts.append(f'### Tool "{name}" (args: {r.get("args")})\n{r["output"]}')
        elif status == "failed":
            parts.append(f'### Failed tool "{name}"\nError: {r.get("error")}')
    return "\n---\n".join(parts)


async def _summarize_task(llm: Any, topic: str, task: ResearchTaskItem, results: List[Dict[str, Any]]) -> str:
    findings = _format_results_for_llm(results)[:MAX_TASK_FINDINGS_CHARS]
    prompt = (
        f"Research topic: {topic}\n"
        f"Task: {task['task_description']}\n\n"
        f"Raw findings:\n{findings}\n\n"
        "Write a concise factual summary (about 200 words at most) of what these findings say about the task. "
        "If they do not answer the task, say so."
    )
    response = await llm.ainvoke([SystemMessage(content=SUMMARY_SYSTEM_PROMPT), HumanMessage(content=prompt)])
    return _strip_think(_content_text(response)).strip()


async def _execute_task(
        llm: Any,
        tools: List[BaseTool],
        topic: str,
        plan: List[ResearchCategoryItem],
        category: ResearchCategoryItem,
        task: ResearchTaskItem,
        stop_event: threading.Event,
) -> Tuple[List[Dict[str, Any]], str, Optional[str], Optional[List[str]]]:
    messages = [
        SystemMessage(content=EXECUTION_SYSTEM_PROMPT),
        HumanMessage(content=_build_task_prompt(topic, plan, category, task)),
    ]
    ai_response = await llm.bind_tools(tools).ainvoke(messages)

    if not isinstance(ai_response, AIMessage) or not ai_response.tool_calls:
        return [], "failed", f"No tool was used. Response: {_content_text(ai_response)[:500]}", None

    tool_map = {t.name: t for t in tools}
    results: List[Dict[str, Any]] = []
    queries: List[str] = []
    any_success = False

    for call in ai_response.tool_calls:
        if stop_event.is_set():
            return results, "pending", None, queries or None

        name, args = call["name"], call.get("args", {})
        tool = tool_map.get(name)
        if tool is None:
            logger.error(f"LLM called unavailable tool '{name}'.")
            results.append({"tool_name": name, "args": args, "status": "failed", "error": "Tool not found"})
            continue

        try:
            logger.info(f"Executing tool '{name}' with args: {args}")
            output = await tool.ainvoke(args)
        except Exception as e:
            logger.error(f"Error executing tool '{name}': {e}", exc_info=True)
            results.append({"tool_name": name, "args": args, "status": "failed", "error": str(e)})
            continue

        if name == BROWSER_TOOL_NAME:
            queries.extend(args.get("queries", []))
            results.extend(output)
            any_success = any_success or any(r.get("status") == "completed" and r.get("result") for r in output)
        else:
            results.append({"tool_name": name, "args": args, "output": str(output), "status": "completed"})
            any_success = True

    if stop_event.is_set():
        return results, "pending", None, queries or None
    if not any_success:
        return results, "failed", "No tool call produced usable results.", queries or None

    try:
        summary = await _summarize_task(llm, topic, task, results)
    except Exception as e:
        logger.error(f"Failed to summarize task results: {e}", exc_info=True)
        summary = f"Executed tool(s): {', '.join(sorted({_tool_name(r) or '?' for r in results}))}."
    return results, "completed", summary, queries or None


async def research_execution_node(
        state: DeepResearchState, llm: Any, tools: List[BaseTool], stop_event: threading.Event
) -> Dict[str, Any]:
    logger.info("--- Entering Research Execution Node ---")
    if _is_stopped(state, stop_event):
        return {"stop_requested": True}

    plan = copy.deepcopy(state["research_plan"])
    position = _find_next_pending(plan)
    if position is None:
        return _index_update(plan)

    cat_idx, task_idx = position
    category = plan[cat_idx]
    task = category["tasks"][task_idx]
    logger.info(f"Executing task '{task['task_description']}' (Category: '{category['category_name']}')")

    try:
        new_results, status, summary, queries = await _execute_task(
            llm, tools, state["topic"], plan, category, task, stop_event
        )
    except Exception as e:
        logger.error(f"Unhandled error during task '{task['task_description']}': {e}", exc_info=True)
        new_results, status, summary, queries = [], "failed", f"Execution error: {e}", None

    stopped = stop_event.is_set()
    task["status"] = "pending" if stopped else status
    task["result_summary"] = None if stopped else summary
    task["queries"] = queries

    search_results = list(state.get("search_results", [])) + new_results
    _save_plan_to_md(plan, state["output_dir"])
    _save_search_results_to_json(search_results, state["output_dir"])

    update: Dict[str, Any] = {"research_plan": plan, "search_results": search_results, **_index_update(plan)}
    if stopped:
        update["stop_requested"] = True
    return update


def _collect_sources(results: List[Dict[str, Any]]) -> List[str]:
    urls: Dict[str, None] = {}
    for r in results:
        text = str(r.get("result") or r.get("output") or "")
        for url in _URL_RE.findall(text):
            urls[url.rstrip(".,;:")] = None
    return list(urls)


def _format_plan_summary(plan: List[ResearchCategoryItem]) -> str:
    lines = []
    for cat_idx, category in enumerate(plan, 1):
        lines.append(f"#### Category {cat_idx}: {category['category_name']}")
        for task in category["tasks"]:
            lines.append(f"- [{_MARKER_BY_STATUS.get(task['status'], ' ')}] {task['task_description']}")
            if task["status"] == "completed" and task.get("result_summary"):
                lines.append(f"  Summary: {task['result_summary']}")
    return "\n".join(lines)


async def synthesis_node(state: DeepResearchState, llm: Any, stop_event: threading.Event) -> Dict[str, Any]:
    logger.info("--- Entering Synthesis Node ---")
    if _is_stopped(state, stop_event):
        return {"stop_requested": True}

    topic = state["topic"]
    output_dir = state["output_dir"]
    results = state.get("search_results", [])
    usable = [r for r in results if r.get("status") == "completed" and (r.get("result") or r.get("output"))]

    if not usable:
        report = f"# Research Report: {topic}\n\nNo information was gathered during the research process."
        _save_report_to_md(report, output_dir)
        return {"final_report": report}

    sources = _collect_sources(usable)
    source_list = "\n".join(f"[{i}] {url}" for i, url in enumerate(sources, 1)) or "No URLs were captured."
    findings = _format_results_for_llm(results)
    if len(findings) > MAX_SYNTHESIS_FINDINGS_CHARS:
        findings = findings[:MAX_SYNTHESIS_FINDINGS_CHARS] + "\n[... findings truncated ...]"

    prompt = (
        f"**Research Topic:** {topic}\n\n"
        f"**Research Plan Followed (with per-task summaries):**\n{_format_plan_summary(state['research_plan'])}\n\n"
        f"**Numbered Sources:**\n{source_list}\n\n"
        f"**Collected Findings:**\n{findings}\n\n"
        "Write the final research report in Markdown based only on the information above."
    )

    try:
        response = await llm.ainvoke([SystemMessage(content=SYNTHESIS_SYSTEM_PROMPT), HumanMessage(content=prompt)])
    except Exception as e:
        logger.error(f"Error during report synthesis: {e}", exc_info=True)
        return {"error_message": f"LLM error during synthesis: {e}"}

    report = _strip_think(_content_text(response)).strip()
    if sources:
        report += "\n\n## References\n\n" + "\n".join(f"[{i}] {url}  " for i, url in enumerate(sources, 1))

    _save_report_to_md(report, output_dir)
    return {"final_report": report}


def _route(state: DeepResearchState, stop_event: threading.Event) -> str:
    if _is_stopped(state, stop_event) or state.get("error_message") or not state.get("research_plan"):
        return "end"
    return "execute_research" if _find_next_pending(state["research_plan"]) else "synthesize_report"


class DeepResearchAgent:
    def __init__(
            self,
            llm: Any,
            browser_config: Dict[str, Any],
            mcp_server_config: Optional[Dict[str, Any]] = None,
    ):
        self.llm = llm
        self.browser_config = browser_config
        self.mcp_server_config = mcp_server_config
        self.mcp_client = None
        self.current_task_id: Optional[str] = None
        self.stop_event: Optional[threading.Event] = None
        self.runner: Optional[asyncio.Task] = None

    async def _setup_tools(
            self, task_id: str, stop_event: threading.Event, output_dir: Path, max_parallel_browsers: int
    ) -> List[BaseTool]:
        root = str(output_dir)
        tools: List[BaseTool] = [
            WriteFileTool(root_dir=root),
            ReadFileTool(root_dir=root),
            ListDirectoryTool(root_dir=root),
            create_browser_search_tool(
                llm=self.llm,
                browser_config=self.browser_config,
                task_id=task_id,
                stop_event=stop_event,
                max_parallel_browsers=max_parallel_browsers,
            ),
        ]
        if self.mcp_server_config:
            try:
                if not self.mcp_client:
                    self.mcp_client = await setup_mcp_client_and_tools(self.mcp_server_config)
                mcp_tools = self.mcp_client.get_tools()
                logger.info(f"Loaded {len(mcp_tools)} MCP tools.")
                tools.extend(mcp_tools)
            except Exception as e:
                logger.error(f"Failed to set up MCP tools: {e}", exc_info=True)
        return list({tool.name: tool for tool in tools}.values())

    async def close_mcp_client(self) -> None:
        if self.mcp_client:
            try:
                await self.mcp_client.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error closing MCP client: {e}")
            finally:
                self.mcp_client = None

    def _compile_graph(self, tools: List[BaseTool], stop_event: threading.Event):
        llm = self.llm

        async def plan_research(state: DeepResearchState) -> Dict[str, Any]:
            return await planning_node(state, llm, stop_event)

        async def execute_research(state: DeepResearchState) -> Dict[str, Any]:
            return await research_execution_node(state, llm, tools, stop_event)

        async def synthesize_report(state: DeepResearchState) -> Dict[str, Any]:
            return await synthesis_node(state, llm, stop_event)

        def route(state: DeepResearchState) -> str:
            return _route(state, stop_event)

        routes = {"execute_research": "execute_research", "synthesize_report": "synthesize_report", "end": END}
        workflow = StateGraph(DeepResearchState)
        workflow.add_node("plan_research", plan_research)
        workflow.add_node("execute_research", execute_research)
        workflow.add_node("synthesize_report", synthesize_report)
        workflow.set_entry_point("plan_research")
        workflow.add_conditional_edges("plan_research", route, routes)
        workflow.add_conditional_edges("execute_research", route, routes)
        workflow.add_edge("synthesize_report", END)
        return workflow.compile()

    async def run(
            self,
            topic: str,
            task_id: Optional[str] = None,
            save_dir: str = DEFAULT_SAVE_ROOT,
            max_parallel_browsers: int = 1,
    ) -> Dict[str, Any]:
        if self.runner and not self.runner.done():
            logger.warning("Agent is already running. Please stop the current task first.")
            return {"status": "error", "message": "Agent already running.", "task_id": self.current_task_id}

        resume = task_id is not None
        task_id = task_id or str(uuid.uuid4())
        try:
            output_dir = _resolve_output_dir(save_dir, task_id)
        except ValueError as e:
            return {"status": "error", "message": str(e), "task_id": task_id, "final_state": {}}
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Starting research task {task_id} for topic: '{topic}' (output: {output_dir})")
        self.current_task_id = task_id
        stop_event = threading.Event()
        self.stop_event = stop_event

        final_state: Optional[Dict[str, Any]] = None
        status, message = "unknown", None
        try:
            tools = await self._setup_tools(task_id, stop_event, output_dir, max_parallel_browsers)
            initial_state: DeepResearchState = {
                "task_id": task_id,
                "topic": topic,
                "research_plan": [],
                "search_results": [],
                "output_dir": str(output_dir),
                "final_report": None,
                "current_category_index": 0,
                "current_task_index_in_category": 0,
                "stop_requested": False,
                "error_message": None,
            }
            if resume:
                initial_state.update(_load_previous_state(output_dir))

            total_tasks = sum(len(c["tasks"]) for c in initial_state["research_plan"])
            recursion_limit = max(MAX_CATEGORIES * MAX_TASKS_PER_CATEGORY, total_tasks) + 10

            graph = self._compile_graph(tools, stop_event)
            self.runner = asyncio.create_task(
                graph.ainvoke(initial_state, config={"recursion_limit": recursion_limit})
            )
            final_state = await self.runner

            if stop_event.is_set():
                status, message = "stopped", "Research process was stopped by request."
            elif final_state.get("error_message"):
                status, message = "error", final_state["error_message"]
            elif final_state.get("final_report"):
                status, message = "completed", "Research process completed successfully."
            else:
                status, message = "finished_incomplete", "Research finished without generating a final report."

        except asyncio.CancelledError:
            status, message = "cancelled", f"Agent run task cancelled for {task_id}."
        except Exception as e:
            status, message = "error", f"Unhandled error during graph execution for {task_id}: {e}"
            logger.error(message, exc_info=True)
        finally:
            self.stop_event = None
            self.current_task_id = None
            self.runner = None
            await self.close_mcp_client()

        logger.info(f"Task {task_id} finished with status: {status}")
        return {"status": status, "message": message, "task_id": task_id, "final_state": final_state or {}}

    async def _stop_lingering_browsers(self, task_id: str) -> None:
        for key in [k for k in _BROWSER_AGENT_INSTANCES if k.startswith(f"{task_id}_")]:
            agent = _BROWSER_AGENT_INSTANCES.get(key)
            if not agent:
                continue
            try:
                await agent.stop()
            except Exception as e:
                logger.error(f"Error stopping browser agent {key}: {e}")

    async def stop(self) -> None:
        if not self.current_task_id or not self.stop_event:
            logger.info("No agent task is currently running.")
            return
        logger.info(f"Stop requested for task ID: {self.current_task_id}")
        self.stop_event.set()
        await self._stop_lingering_browsers(self.current_task_id)

    def close(self) -> None:
        if self.stop_event:
            self.stop_event.set()