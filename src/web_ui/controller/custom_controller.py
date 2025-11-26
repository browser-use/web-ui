import inspect
import logging
import os
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from browser_use.agent.views import ActionModel, ActionResult
from browser_use.browser.context import BrowserContext
from browser_use.controller.registry.service import RegisteredAction
from browser_use.controller.service import Controller
from browser_use.utils import time_execution_sync
from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel

from src.web_ui.utils.mcp_client import create_tool_param_model, setup_mcp_client_and_tools
from src.web_ui.utils.mcp_config import load_mcp_config

logger = logging.getLogger(__name__)

Context = TypeVar("Context")


class CustomController(Controller):
    def __init__(
        self,
        exclude_actions: list[str] | None = None,
        output_model: type[BaseModel] | None = None,
        ask_assistant_callback: Callable[[str, BrowserContext], dict[str, Any]]
        | Callable[[str, BrowserContext], Awaitable[dict[str, Any]]]
        | None = None,
    ):
        if exclude_actions is None:
            exclude_actions = []
        super().__init__(exclude_actions=exclude_actions, output_model=output_model)
        self._register_custom_actions()
        self.ask_assistant_callback = ask_assistant_callback
        self.mcp_client = None
        self.mcp_server_config = None

    def _register_custom_actions(self):
        """Register all custom browser actions"""

        @self.registry.action(
            "When executing tasks, prioritize autonomous completion. However, if you encounter a definitive blocker "
            "that prevents you from proceeding independently – such as needing credentials you don't possess, "
            "requiring subjective human judgment, needing a physical action performed, encountering complex CAPTCHAs, "
            "or facing limitations in your capabilities – you must request human assistance."
        )
        async def ask_for_assistant(query: str, browser: BrowserContext):
            if self.ask_assistant_callback:
                if inspect.iscoroutinefunction(self.ask_assistant_callback):
                    user_response = await self.ask_assistant_callback(query, browser)
                else:
                    user_response = self.ask_assistant_callback(query, browser)
                msg = f"AI ask: {query}. User response: {user_response['response']}"
                logger.info(msg)
                return ActionResult(extracted_content=msg, include_in_memory=True)
            else:
                return ActionResult(
                    extracted_content="Human cannot help you. Please try another way.",
                    include_in_memory=True,
                )

        @self.registry.action(
            "Upload file to interactive element with file path ",
        )
        async def upload_file(
            index: int, path: str, browser: BrowserContext, available_file_paths: list[str]
        ):
            if path not in available_file_paths:
                return ActionResult(error=f"File path {path} is not available")

            if not os.path.exists(path):
                return ActionResult(error=f"File {path} does not exist")

            dom_el = await browser.get_dom_element_by_index(index)

            file_upload_dom_el = dom_el.get_file_upload_element()

            if file_upload_dom_el is None:
                msg = f"No file upload element found at index {index}"
                logger.info(msg)
                return ActionResult(error=msg)

            file_upload_el = await browser.get_locate_element(file_upload_dom_el)

            if file_upload_el is None:
                msg = f"No file upload element found at index {index}"
                logger.info(msg)
                return ActionResult(error=msg)

            try:
                await file_upload_el.set_input_files(path)
                msg = f"Successfully uploaded file to index {index}"
                logger.info(msg)
                return ActionResult(extracted_content=msg, include_in_memory=True)
            except Exception as e:
                msg = f"Failed to upload file to index {index}: {str(e)}"
                logger.info(msg)
                return ActionResult(error=msg)

    @time_execution_sync("--act")
    async def act(
        self,
        action: ActionModel,
        browser_context: BrowserContext | None = None,
        #
        page_extraction_llm: BaseChatModel | None = None,
        sensitive_data: dict[str, str] | None = None,
        available_file_paths: list[str] | None = None,
        #
        context: Context | None = None,
    ) -> ActionResult:
        """Execute an action"""

        try:
            for action_name, params in action.model_dump(exclude_unset=True).items():
                if params is not None:
                    if action_name.startswith("mcp"):
                        # this is a mcp tool
                        logger.debug(f"Invoke MCP tool: {action_name}")
                        mcp_tool = self.registry.registry.actions.get(action_name).function
                        result = await mcp_tool.ainvoke(params)
                    else:
                        result = await self.registry.execute_action(
                            action_name,
                            params,
                            browser=browser_context,
                            page_extraction_llm=page_extraction_llm,
                            sensitive_data=sensitive_data,
                            available_file_paths=available_file_paths,
                            context=context,
                        )

                    if isinstance(result, str):
                        return ActionResult(extracted_content=result)
                    elif isinstance(result, ActionResult):
                        return result
                    elif result is None:
                        return ActionResult()
                    else:
                        raise ValueError(f"Invalid action result type: {type(result)} of {result}")
            return ActionResult()
        except Exception as e:
            raise e

    async def setup_mcp_client(self, mcp_server_config: dict[str, Any] | None = None):
        """
        Setup MCP client with provided config or auto-load from data/mcp.json.

        Args:
            mcp_server_config: Optional MCP server configuration dict.
                              If None, attempts to load from data/mcp.json file.
        """
        # If no config provided, try to load from file
        if mcp_server_config is None:
            logger.info("No MCP config provided, attempting to load from data/mcp.json")
            mcp_server_config = load_mcp_config()

            if mcp_server_config is None:
                logger.info("No MCP configuration file found. MCP tools will not be available.")
                return

        self.mcp_server_config = mcp_server_config

        # Setup client and register tools
        if self.mcp_server_config:
            self.mcp_client = await setup_mcp_client_and_tools(self.mcp_server_config)
            if self.mcp_client:
                await self.register_mcp_tools()
                logger.info("MCP client setup completed successfully")
            else:
                logger.warning("MCP client setup failed")

    async def register_mcp_tools(self):
        """
        Register the MCP tools used by this controller.
        Uses the new langchain-mcp-adapters 0.1.0+ API.
        """
        if self.mcp_client and self.mcp_server_config:
            try:
                # Get all server names from the config
                if "mcpServers" in self.mcp_server_config:
                    server_names = list(self.mcp_server_config["mcpServers"].keys())
                else:
                    server_names = list(self.mcp_server_config.keys())

                total_tools = 0
                for server_name in server_names:
                    # Get tools for each server individually
                    tools = await self.mcp_client.get_tools(server_name=server_name)

                    for tool in tools:
                        tool_name = f"mcp.{server_name}.{tool.name}"
                        param_model_class = create_tool_param_model(tool)
                        self.registry.registry.actions[tool_name] = RegisteredAction(
                            name=tool_name,
                            description=tool.description,
                            function=tool,
                            param_model=param_model_class,
                        )
                        logger.info(f"Add mcp tool: {tool_name}")
                    logger.debug(f"Registered {len(tools)} mcp tools for {server_name}")
                    total_tools += len(tools)

                logger.info(
                    f"Successfully registered {total_tools} MCP tools from {len(server_names)} servers"
                )
            except Exception as e:
                logger.error(f"Failed to register MCP tools: {e}", exc_info=True)
        else:
            logger.warning("MCP client not started.")

    async def close_mcp_client(self):
        """Close MCP client and cleanup resources."""
        if self.mcp_client:
            try:
                await self.mcp_client.__aexit__(None, None, None)
                logger.info("MCP client closed successfully")
            except Exception as e:
                logger.error(f"Error closing MCP client: {e}", exc_info=True)
            finally:
                self.mcp_client = None

    async def reload_mcp_client(self, mcp_server_config: dict[str, Any] | None = None):
        """
        Reload MCP client with new configuration.

        This closes the existing client and sets up a new one.

        Args:
            mcp_server_config: Optional new MCP server configuration dict.
                              If None, reloads from data/mcp.json file.
        """
        logger.info("Reloading MCP client...")

        # Close existing client
        await self.close_mcp_client()

        # Unregister existing MCP tools
        if self.registry and hasattr(self.registry, "registry"):
            tools_to_remove = [
                name for name in self.registry.registry.actions.keys() if name.startswith("mcp.")
            ]
            for tool_name in tools_to_remove:
                del self.registry.registry.actions[tool_name]
                logger.debug(f"Removed MCP tool: {tool_name}")

        # Setup new client
        await self.setup_mcp_client(mcp_server_config)
        logger.info("MCP client reload completed")

    def get_registered_mcp_tools(self) -> dict[str, list[str]]:
        """
        Get list of currently registered MCP tools grouped by server.

        Returns:
            Dictionary mapping server names to lists of tool names
        """
        tools_by_server = {}

        if self.registry and hasattr(self.registry, "registry"):
            for tool_name in self.registry.registry.actions.keys():
                if tool_name.startswith("mcp."):
                    # Parse tool name: mcp.{server_name}.{tool_name}
                    parts = tool_name.split(".", 2)
                    if len(parts) >= 3:
                        server_name = parts[1]
                        actual_tool_name = parts[2]

                        if server_name not in tools_by_server:
                            tools_by_server[server_name] = []

                        tools_by_server[server_name].append(actual_tool_name)

        return tools_by_server
