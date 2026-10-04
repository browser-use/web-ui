"""
REST bridge for headless clients such as the n8n community node
`n8n-nodes-browser-use` ("Browser Use Local Bridge API" credential).

The routes mirror the Local Bridge contract that node calls:

    GET  /api/v1/ping
    POST /api/v1/run-task
    GET  /api/v1/task/{task_id}
    GET  /api/v1/task/{task_id}/status
    GET  /api/v1/task/{task_id}/media?type=screenshot|gif
    PUT  /api/v1/stop-task/{task_id}
    PUT  /api/v1/pause-task/{task_id}
    PUT  /api/v1/resume-task/{task_id}
    GET  /api/v1/tasks?limit=N

The router is mounted on the same FastAPI app as the Gradio UI (see webui.py), so a
single exposed port (e.g. Railway's $PORT) serves both.
"""

import asyncio
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from browser_use.browser.browser import BrowserConfig
from browser_use.browser.context import BrowserContextConfig
from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.agent.browser_use.browser_use_agent import BrowserUseAgent
from src.browser.custom_browser import CustomBrowser
from src.controller.custom_controller import CustomController
from src.utils import config, llm_provider

logger = logging.getLogger(__name__)

API_PREFIX = "/api/v1"

# n8n's provider values that differ from the keys used by src/utils/llm_provider.py
PROVIDER_ALIASES = {"azure": "azure_openai"}


class RunTaskRequest(BaseModel):
    task: str
    ai_provider: Optional[str] = None
    model_name: Optional[str] = None
    headful: bool = False
    use_custom_chrome: bool = False
    max_steps: Optional[int] = None


@dataclass
class TaskRecord:
    id: str
    task: str
    provider: str
    model_name: str
    status: str = "created"
    created_at: str = field(default_factory=lambda: _now())
    finished_at: Optional[str] = None
    output: Optional[str] = None
    error: Optional[str] = None
    steps: int = 0
    gif_path: Optional[str] = None
    agent: Optional[BrowserUseAgent] = None
    runner: Optional[asyncio.Task] = None

    def summary(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.id,
            "task": self.task,
            "status": self.status,
            "ai_provider": self.provider,
            "model_name": self.model_name,
            "created_at": self.created_at,
            "finished_at": self.finished_at,
            "steps": self.steps,
            "output": self.output,
            "error": self.error,
        }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value.lower() in ("1", "true", "yes", "y")


class TaskManager:
    def __init__(self):
        self.tasks: Dict[str, TaskRecord] = {}
        max_concurrent = int(os.getenv("BRIDGE_MAX_CONCURRENT_TASKS", "1"))
        self.slots = asyncio.Semaphore(max(1, max_concurrent))
        self.history_dir = os.getenv("BRIDGE_HISTORY_DIR", "./tmp/bridge_tasks")

    def get(self, task_id: str) -> TaskRecord:
        record = self.tasks.get(task_id)
        if not record:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        return record

    def submit(self, request: RunTaskRequest) -> TaskRecord:
        provider = (request.ai_provider or os.getenv("DEFAULT_LLM", "openai")).lower()
        provider = PROVIDER_ALIASES.get(provider, provider)
        if provider not in config.model_names:
            raise HTTPException(status_code=400, detail=f"Unsupported ai_provider: {provider}")
        model_name = (
                request.model_name
                or os.getenv(f"{provider.upper()}_MODEL")
                or config.model_names[provider][0]
        )
        record = TaskRecord(id=str(uuid.uuid4()), task=request.task, provider=provider, model_name=model_name)
        self.tasks[record.id] = record
        record.runner = asyncio.create_task(self._run(record, request))
        return record

    async def _run(self, record: TaskRecord, request: RunTaskRequest):
        browser = None
        browser_context = None
        controller = None
        async with self.slots:
            if record.status == "stopped":
                return
            try:
                llm = llm_provider.get_llm_model(
                    provider=record.provider,
                    model_name=record.model_name,
                    temperature=float(os.getenv("BRIDGE_LLM_TEMPERATURE", "0.6")),
                )

                browser_binary_path = None
                extra_args = []
                if request.use_custom_chrome:
                    browser_binary_path = os.getenv("BROWSER_PATH") or None
                    if os.getenv("BROWSER_USER_DATA"):
                        extra_args.append(f"--user-data-dir={os.getenv('BROWSER_USER_DATA')}")
                window_w = int(os.getenv("RESOLUTION_WIDTH", "1280"))
                window_h = int(os.getenv("RESOLUTION_HEIGHT", "1100"))
                browser = CustomBrowser(
                    config=BrowserConfig(
                        headless=not request.headful,
                        browser_binary_path=browser_binary_path,
                        extra_browser_args=extra_args,
                        cdp_url=os.getenv("BROWSER_CDP") or None,
                        new_context_config=BrowserContextConfig(window_width=window_w, window_height=window_h),
                    )
                )
                browser_context = await browser.new_context(
                    config=BrowserContextConfig(window_width=window_w, window_height=window_h)
                )

                task_dir = os.path.join(self.history_dir, record.id)
                os.makedirs(task_dir, exist_ok=True)
                record.gif_path = os.path.join(task_dir, f"{record.id}.gif")

                # No human is attached to a bridge task, so the ask-for-help action is unavailable
                controller = CustomController(exclude_actions=["ask_for_assistant"])

                def on_step(_state, _output, step_num: int):
                    record.steps = step_num

                record.agent = BrowserUseAgent(
                    task=record.task,
                    llm=llm,
                    browser=browser,
                    browser_context=browser_context,
                    controller=controller,
                    register_new_step_callback=on_step,
                    use_vision=_env_bool("BRIDGE_USE_VISION", True),
                    source="api",
                )
                record.agent.state.agent_id = record.id
                record.agent.settings.generate_gif = record.gif_path

                record.status = "running"
                max_steps = request.max_steps or int(os.getenv("BRIDGE_MAX_STEPS", "100"))
                history = await record.agent.run(max_steps=max_steps)

                record.output = history.final_result()
                errors = [e for e in history.errors() if e]
                if record.agent.state.stopped:
                    record.status = "stopped"
                elif history.is_done():
                    record.status = "finished"
                else:
                    record.status = "failed"
                    record.error = errors[-1] if errors else f"Task did not finish within {max_steps} steps"
            except asyncio.CancelledError:
                record.status = "stopped"
                raise
            except Exception as e:
                logger.error(f"Bridge task {record.id} failed: {e}", exc_info=True)
                record.status = "failed"
                record.error = str(e)
            finally:
                record.finished_at = _now()
                if controller:
                    await controller.close_mcp_client()
                if browser_context:
                    await browser_context.close()
                if browser:
                    await browser.close()


task_manager: Optional[TaskManager] = None


def _manager() -> TaskManager:
    # Created lazily so the semaphore binds to the server's running event loop
    global task_manager
    if task_manager is None:
        task_manager = TaskManager()
    return task_manager


async def verify_token(authorization: Optional[str] = Header(default=None)):
    expected = os.getenv("BRIDGE_API_TOKEN")
    if not expected:
        return
    if authorization != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="Invalid or missing bearer token")


router = APIRouter(prefix=API_PREFIX, dependencies=[Depends(verify_token)])


@router.get("/ping")
async def ping():
    return {"status": "ok", "message": "Browser Use WebUI bridge is running"}


# The n8n credential test requests `<url>/api/v1/ping`, while the node itself appends
# `/api/v1` only when the URL does not already end with it. Answering the doubled path
# lets users enter `https://<host>/api/v1` and have both the credential test and the
# node requests succeed.
router.add_api_route("/api/v1/ping", ping, methods=["GET"], include_in_schema=False)


@router.post("/run-task")
async def run_task(request: RunTaskRequest):
    record = _manager().submit(request)
    return {**record.summary(), "live_url": None}


@router.get("/task/{task_id}")
async def get_task(task_id: str):
    return _manager().get(task_id).summary()


@router.get("/task/{task_id}/status")
async def get_task_status(task_id: str):
    record = _manager().get(task_id)
    return {
        "id": record.id,
        "status": record.status,
        "steps": record.steps,
        "output": record.output,
        "error": record.error,
    }


@router.get("/task/{task_id}/media")
async def get_task_media(task_id: str, type: str = Query(default="screenshot")):
    record = _manager().get(task_id)
    media_type = type.lower()
    if media_type == "screenshot":
        screenshot = None
        if record.agent:
            for item in reversed(record.agent.state.history.history):
                if item.state and item.state.screenshot:
                    screenshot = item.state.screenshot
                    break
        if not screenshot:
            raise HTTPException(status_code=404, detail="No screenshot available for this task yet")
        return {"id": record.id, "type": "screenshot", "mime_type": "image/png", "data": screenshot}
    if media_type in ("gif", "video"):
        if not record.gif_path or not os.path.exists(record.gif_path):
            raise HTTPException(status_code=404, detail="Recording is generated when the task finishes")
        return FileResponse(record.gif_path, media_type="image/gif", filename=f"{record.id}.gif")
    raise HTTPException(status_code=400, detail=f"Unsupported media type: {type}")


@router.put("/stop-task/{task_id}")
async def stop_task(task_id: str):
    record = _manager().get(task_id)
    if record.status in ("finished", "failed", "stopped"):
        return {"id": record.id, "status": record.status}
    if record.agent:
        record.agent.state.stopped = True
        record.agent.state.paused = False
    else:
        record.status = "stopped"
    return {"id": record.id, "status": "stopping" if record.agent else "stopped"}


@router.put("/pause-task/{task_id}")
async def pause_task(task_id: str):
    record = _manager().get(task_id)
    if record.status != "running" or not record.agent:
        raise HTTPException(status_code=409, detail=f"Task is {record.status}, not running")
    record.agent.pause()
    record.status = "paused"
    return {"id": record.id, "status": record.status}


@router.put("/resume-task/{task_id}")
async def resume_task(task_id: str):
    record = _manager().get(task_id)
    if record.status != "paused" or not record.agent:
        raise HTTPException(status_code=409, detail=f"Task is {record.status}, not paused")
    record.agent.resume()
    record.status = "running"
    return {"id": record.id, "status": record.status}


@router.get("/tasks")
async def list_tasks(limit: int = Query(default=50, ge=1, le=50), status: Optional[str] = None):
    records: List[TaskRecord] = sorted(_manager().tasks.values(), key=lambda r: r.created_at, reverse=True)
    if status:
        records = [r for r in records if r.status == status]
    return {"tasks": [r.summary() for r in records[:limit]], "total_count": len(records)}


def create_api_app() -> FastAPI:
    app = FastAPI(title="Browser Use WebUI")
    app.include_router(router)
    return app
