from typing import Any, Awaitable, Callable, Dict, List, Optional, Type
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from src.agent.base_views import ActionResult, AgentError, AgentHistory, BrowserState, ActionModel

class Agent:
    def __init__(
        self,
        task: str,
        llm: BaseChatModel,
        add_infos: str = "",
        browser: Any = None,
        browser_context: Any = None,
        controller: Any = None,
        sensitive_data: Optional[Dict[str, str]] = None,
        initial_actions: Optional[List[Dict[str, Dict[str, Any]]]] = None,
        register_new_step_callback: Optional[Callable[['BrowserState', 'AgentOutput', int], Awaitable[None]]] = None,
        register_done_callback: Optional[Callable[['AgentHistoryList'], Awaitable[None]]] = None,
        register_external_agent_status_raise_error_callback: Optional[Callable[[], Awaitable[bool]]] = None,
        use_vision: bool = True,
        use_vision_for_planner: bool = False,
        save_conversation_path: Optional[str] = None,
        save_conversation_path_encoding: Optional[str] = 'utf-8',
        max_failures: int = 3,
        retry_delay: int = 10,
        max_input_tokens: int = 128000,
        validate_output: bool = False,
        message_context: Optional[str] = None,
        generate_gif: bool | str = False,
        available_file_paths: Optional[list[str]] = None,
        include_attributes: list[str] = [
            'title',
            'type',
            'name',
            'role',
            'aria-label',
            'placeholder',
            'value',
            'alt',
            'aria-expanded',
            'data-date-format',
        ],
        max_actions_per_step: int = 10,
        tool_calling_method: Optional[str] = 'auto',
        page_extraction_llm: Optional[BaseChatModel] = None,
        planner_llm: Optional[BaseChatModel] = None,
        planner_interval: int = 1,
    ):
        self.task = task
        self.llm = llm
        self.add_infos = add_infos
        self.browser = browser
        self.browser_context = browser_context
        self.controller = controller
        self.sensitive_data = sensitive_data or {}
        self.initial_actions = initial_actions or []
        self.register_new_step_callback = register_new_step_callback
        self.register_done_callback = register_done_callback
        self.register_external_agent_status_raise_error_callback = register_external_agent_status_raise_error_callback
        self.use_vision = use_vision
        self.use_vision_for_planner = use_vision_for_planner
        self.save_conversation_path = save_conversation_path
        self.save_conversation_path_encoding = save_conversation_path_encoding
        self.max_failures = max_failures
        self.retry_delay = retry_delay
        self.max_input_tokens = max_input_tokens
        self.validate_output = validate_output
        self.message_context = message_context
        self.generate_gif = generate_gif
        self.available_file_paths = available_file_paths or []
        self.include_attributes = include_attributes
        self.max_actions_per_step = max_actions_per_step
        self.tool_calling_method = tool_calling_method
        self.page_extraction_llm = page_extraction_llm
        self.planner_llm = planner_llm
        self.planner_interval = planner_interval

    async def get_next_action(self, input_messages: list[BaseMessage]) -> Any:
        raise NotImplementedError

    async def step(self, step_info: Optional[Any] = None) -> None:
        raise NotImplementedError

    async def run(self, max_steps: int = 100) -> Any:
        raise NotImplementedError 