# import pdb  # Unused
# import pyperclip  # Unused
from typing import Optional, Type, Callable, Dict, Any, Union, Awaitable, TypeVar
from pydantic import BaseModel
from browser_use.agent.views import ActionResult
from browser_use.browser import BrowserSession
from browser_use import Controller
# from browser_use.controller.registry.service import RegisteredAction  # Not available in browser-use 0.7.10
# Removed unused imports: DoneAction, Registry, MainContentExtractor, and view classes
import logging
import inspect
# import asyncio  # Unused
# import os  # Unused
from browser_use.llm import BaseChatModel
from browser_use.agent.views import ActionModel, ActionResult
from src.utils.mcp_client import get_mcp_manager, MCPManager

from browser_use.utils import time_execution_sync

logger = logging.getLogger(__name__)

# Context = TypeVar('Context')  # Removed - not used in browser-use 0.7.10


class CustomController(Controller):
    def __init__(self, exclude_actions: list[str] = [],
                 output_model: Optional[Type[BaseModel]] = None,
                 ask_assistant_callback: Optional[Union[Callable[[str, BrowserSession], Dict[str, Any]], Callable[
                     [str, BrowserSession], Awaitable[Dict[str, Any]]]]] = None,
                 ):
        super().__init__(exclude_actions=exclude_actions, output_model=output_model)
        self._register_custom_actions()
        self.ask_assistant_callback = ask_assistant_callback
        self.mcp_manager: Optional[MCPManager] = None

    def _register_custom_actions(self):
        """Register all custom browser actions"""

        @self.registry.action(
            "When executing tasks, prioritize autonomous completion. However, if you encounter a definitive blocker "
            "that prevents you from proceeding independently – such as needing credentials you don't possess, "
            "requiring subjective human judgment, needing a physical action performed, encountering complex CAPTCHAs, "
            "or facing limitations in your capabilities – you must request human assistance."
        )
        async def ask_for_assistant(query: str, browser_session: BrowserSession):
            if self.ask_assistant_callback:
                if inspect.iscoroutinefunction(self.ask_assistant_callback):
                    user_response = await self.ask_assistant_callback(query, browser_session)
                else:
                    user_response = self.ask_assistant_callback(query, browser_session)
                msg = f"AI ask: {query}. User response: {user_response['response']}"
                logger.info(msg)
                return ActionResult(extracted_content=msg, include_in_memory=True)
            else:
                return ActionResult(extracted_content="Human cannot help you. Please try another way.",
                                    include_in_memory=True)

        # TODO: Update upload_file action for browser_use 0.6.0 API
        # The old implementation used methods that don't exist in the new version
        # Commenting out for now to avoid schema generation errors
        
        # @self.registry.action(
        #     'Upload file to interactive element with file path ',
        # )
        # async def upload_file(index: int, path: str, browser_session: BrowserSession, available_file_paths: list[str]):
        #     # This needs to be reimplemented using browser_use 0.6.0 API
        #     return ActionResult(error='File upload not yet implemented for browser_use 0.6.0')

    @time_execution_sync('--act')
    async def act(
            self,
            action: ActionModel,
            browser_session: BrowserSession,
            #
            page_extraction_llm: Optional[BaseChatModel] = None,
            sensitive_data: Optional[Dict[str, str]] = None,
            available_file_paths: Optional[list[str]] = None,
            file_system: Optional[Any] = None,  # Added for compatibility with 0.6.0
            #
    ) -> ActionResult:
        """Execute an action using parent class - MCP functionality removed"""
        
        # Delegate to parent class for all actions
        return await super().act(
            action=action,
            browser_session=browser_session,
            page_extraction_llm=page_extraction_llm,
            sensitive_data=sensitive_data,
            available_file_paths=available_file_paths,
            file_system=file_system,
        )

    async def setup_mcp_client(self, mcp_server_config: Optional[Dict[str, Any]] = None):
        """Set up MCP servers using browser-use's native MCP implementation."""
        if not mcp_server_config:
            logger.info("No MCP server configuration provided")
            return
        
        try:
            logger.info("Setting up MCP servers using browser-use implementation...")
            
            # Get the global MCP manager
            self.mcp_manager = get_mcp_manager()
            
            # Set up MCP servers
            success = await self.mcp_manager.setup_mcp_servers(mcp_server_config)
            
            if success:
                # Register MCP tools to this controller
                tool_count = self.mcp_manager.register_tools_to_controller(self)
                logger.info(f"Successfully set up MCP with {tool_count} server(s)")
                
                connected_servers = self.mcp_manager.get_connected_servers()
                logger.info(f"Connected MCP servers: {connected_servers}")
            else:
                logger.warning("Failed to set up MCP servers")
                
        except Exception as e:
            logger.error(f"Error setting up MCP client: {e}", exc_info=True)
    
    async def close_mcp_client(self):
        """Close MCP connections."""
        if self.mcp_manager:
            try:
                await self.mcp_manager.disconnect_all()
                logger.info("Closed all MCP connections")
            except Exception as e:
                logger.error(f"Error closing MCP connections: {e}")
            finally:
                self.mcp_manager = None
