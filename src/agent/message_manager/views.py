from dataclasses import dataclass, field
from typing import List, Optional
from langchain_core.messages import BaseMessage

@dataclass
class MessageHistory:
    """Class to store message history"""
    messages: List[BaseMessage] = field(default_factory=list)
    current_tokens: int = 0

    def add_message(self, message: BaseMessage, tokens: Optional[int] = None) -> None:
        """Add message to history"""
        self.messages.append(message)
        if tokens:
            self.current_tokens += tokens

    def remove_message(self, index: int) -> None:
        """Remove message from history"""
        if 0 <= index < len(self.messages):
            self.messages.pop(index)

    def clear(self) -> None:
        """Clear message history"""
        self.messages.clear()
        self.current_tokens = 0 