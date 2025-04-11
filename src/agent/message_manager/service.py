from dataclasses import dataclass
from typing import List, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from .views import MessageHistory

@dataclass
class MessageManagerSettings:
    """Settings for message manager"""
    max_tokens: int = 4000
    system_message: str = "You are a helpful AI assistant."
    token_limit_pct: float = 0.8

    @property
    def token_limit(self) -> int:
        """Get token limit"""
        return int(self.max_tokens * self.token_limit_pct)

class MessageManager:
    """Class to manage message history"""
    def __init__(self, settings: Optional[MessageManagerSettings] = None):
        self.settings = settings or MessageManagerSettings()
        self.history = MessageHistory()
        self._init_messages()

    def _init_messages(self) -> None:
        """Initialize messages with system message"""
        self.history.clear()
        system_msg = SystemMessage(content=self.settings.system_message)
        self.history.add_message(system_msg)

    def add_human_message(self, content: str) -> None:
        """Add human message to history"""
        message = HumanMessage(content=content)
        self.history.add_message(message)

    def add_ai_message(self, content: str) -> None:
        """Add AI message to history"""
        message = AIMessage(content=content)
        self.history.add_message(message)

    def get_messages(self) -> List[BaseMessage]:
        """Get all messages"""
        return self.history.messages

    def cut_messages(self, keep_last_n: int = 4) -> None:
        """Cut message history to keep only last N messages"""
        if len(self.history.messages) > keep_last_n + 1:  # +1 for system message
            self.history.messages = [self.history.messages[0]] + self.history.messages[-keep_last_n:]

    def clear_messages(self) -> None:
        """Clear message history and reinitialize"""
        self._init_messages() 