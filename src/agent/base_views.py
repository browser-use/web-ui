from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Type
from pydantic import BaseModel, Field
import uuid

class ActionResult(BaseModel):
    error: Optional[str] = None
    extracted_content: Optional[str] = None
    include_in_memory: bool = True

class AgentOutput(BaseModel):
    action: List[Any]  # Will be extended with custom actions

class AgentError(Exception):
    pass

@dataclass
class AgentHistory:
    input: str
    output: str
    timestamp: float

class AgentHistoryList(BaseModel):
    history: List[AgentHistory] = Field(default_factory=list)

class MessageManagerState(BaseModel):
    messages: List[Dict[str, Any]] = Field(default_factory=list)

class BrowserState(BaseModel):
    url: str = ""
    tabs: str = ""
    element_tree: Any = None
    screenshot: Optional[str] = None
    pixels_above: Optional[int] = None
    pixels_below: Optional[int] = None

class ActionModel(BaseModel):
    pass

class AgentState(BaseModel):
    agent_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    n_steps: int = 1
    consecutive_failures: int = 0
    last_result: Optional[List[ActionResult]] = None
    history: AgentHistoryList = Field(default_factory=lambda: AgentHistoryList(history=[]))
    last_plan: Optional[str] = None
    paused: bool = False
    stopped: bool = False
    message_manager_state: MessageManagerState = Field(default_factory=MessageManagerState)
    last_action: Optional[List[ActionModel]] = None
    extracted_content: str = "" 