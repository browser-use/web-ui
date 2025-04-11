from __future__ import annotations

import logging
import pdb
from typing import List, Optional, Type, Dict

from browser_use.agent.message_manager.service import MessageManager
from browser_use.agent.message_manager.views import MessageHistory
from browser_use.agent.prompts import SystemPrompt, AgentMessagePrompt
from browser_use.agent.views import ActionResult, AgentStepInfo, ActionModel
from browser_use.browser.views import BrowserState
from browser_use.agent.message_manager.service import MessageManagerSettings
from browser_use.agent.views import ActionResult, AgentOutput, AgentStepInfo, MessageManagerState
from langchain_core.language_models import BaseChatModel
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    ToolMessage,
    SystemMessage
)
from langchain_openai import ChatOpenAI
from ..utils.llm import DeepSeekR1ChatOpenAI
from .custom_prompts import CustomAgentMessagePrompt

logger = logging.getLogger(__name__)


class CustomMessageManagerSettings(MessageManagerSettings):
    agent_prompt_class: Type[AgentMessagePrompt] = AgentMessagePrompt


class CustomMessageManager(MessageManager):
    def __init__(
            self,
            task: str,
            system_message: SystemMessage,
            settings: MessageManagerSettings = MessageManagerSettings(),
            state: MessageManagerState = MessageManagerState(),
    ):
        super().__init__(
            task=task,
            system_message=system_message,
            settings=settings,
            state=state
        )

    def _init_messages(self) -> None:
        """Initialize the message history with system message, context, task, and other initial messages"""
        self._add_message_with_tokens(self.system_prompt)
        self.context_content = ""

        if self.settings.message_context:
            self.context_content += 'Context for the task' + self.settings.message_context

        if self.settings.sensitive_data:
            info = f'Here are placeholders for sensitive data: {list(self.settings.sensitive_data.keys())}'
            info += 'To use them, write <secret>the placeholder name</secret>'
            self.context_content += info

        if self.settings.available_file_paths:
            filepaths_msg = f'Here are file paths you can use: {self.settings.available_file_paths}'
            self.context_content += filepaths_msg

        if self.context_content:
            context_message = HumanMessage(content=self.context_content)
            self._add_message_with_tokens(context_message)

    def cut_messages(self):
        """Get current message list, potentially trimmed to max tokens"""
        diff = self.state.history.current_tokens - self.settings.max_input_tokens
        min_message_len = 2 if self.context_content is not None else 1

        while diff > 0 and len(self.state.history.messages) > min_message_len:
            self.state.history.remove_message(min_message_len)  # always remove the oldest message
            diff = self.state.history.current_tokens - self.settings.max_input_tokens

    def add_state_message(
            self,
            state: BrowserState,
            actions: Optional[List[ActionModel]] = None,
            result: Optional[List[ActionResult]] = None,
            step_info: Optional[AgentStepInfo] = None,
            use_vision=True,
    ) -> None:
        """Add browser state as human message"""
        # otherwise add state message and result to next message (which will not stay in memory)
        state_message = self.settings.agent_prompt_class(
            state,
            actions,
            result,
            include_attributes=self.settings.include_attributes,
            step_info=step_info,
        ).get_user_message(use_vision)
        self._add_message_with_tokens(state_message)

    def _remove_state_message_by_index(self, remove_ind=-1) -> None:
        """Remove state message by index from history"""
        i = len(self.state.history.messages) - 1
        remove_cnt = 0
        while i >= 0:
            if isinstance(self.state.history.messages[i].message, HumanMessage):
                remove_cnt += 1
            if remove_cnt == abs(remove_ind):
                self.state.history.messages.pop(i)
                break
            i -= 1


def convert_input_messages(messages: List[BaseMessage]) -> List[BaseMessage]:
    """Convert input messages to the format expected by the message manager"""
    converted_messages = []
    for message in messages:
        if isinstance(message, HumanMessage):
            converted_messages.append(HumanMessage(content=message.content))
        elif isinstance(message, AIMessage):
            converted_messages.append(AIMessage(content=message.content))
        elif isinstance(message, SystemMessage):
            converted_messages.append(SystemMessage(content=message.content))
        elif isinstance(message, ToolMessage):
            converted_messages.append(ToolMessage(content=message.content, tool_call_id=message.tool_call_id))
    return converted_messages


def extract_json_from_model_output(output: str) -> Dict:
    """Extract JSON from model output string"""
    import json
    import re
    
    # Try to find JSON content between ```json and ``` markers
    json_match = re.search(r'```json\s*(.*?)\s*```', output, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        # If no markers found, try to find JSON content directly
        json_str = output.strip()
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        # If JSON parsing fails, try to repair the JSON
        from json_repair import repair_json
        repaired_json = repair_json(json_str)
        return json.loads(repaired_json)


def save_conversation(messages: List[BaseMessage], path: str, encoding: str = 'utf-8') -> None:
    """Save conversation messages to a file"""
    import json
    from datetime import datetime
    
    conversation = []
    for message in messages:
        msg_dict = {
            'type': message.__class__.__name__,
            'content': message.content,
            'timestamp': datetime.now().isoformat()
        }
        if isinstance(message, ToolMessage):
            msg_dict['tool_call_id'] = message.tool_call_id
        conversation.append(msg_dict)
    
    with open(path, 'w', encoding=encoding) as f:
        json.dump(conversation, f, indent=2, ensure_ascii=False)
