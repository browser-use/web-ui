from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Type
import uuid

from src.agent.base_views import AgentOutput, AgentState, ActionResult, AgentHistoryList, MessageManagerState, ActionModel
from pydantic import BaseModel, ConfigDict, Field, create_model


# Type for tool calling method
ToolCallingMethod = Literal['auto', 'function_call', 'json']


@dataclass
class AgentSettings:
    """Settings for the agent"""
    use_vision: bool = True
    use_vision_for_planner: bool = False
    save_conversation_path: Optional[str] = None
    save_conversation_path_encoding: Optional[str] = 'utf-8'
    max_failures: int = 3
    retry_delay: int = 10
    max_input_tokens: int = 128000
    validate_output: bool = False
    message_context: Optional[str] = None
    generate_gif: bool | str = False
    available_file_paths: Optional[list[str]] = None
    include_attributes: list[str] = Field(default_factory=lambda: [
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
    ])
    max_actions_per_step: int = 10
    tool_calling_method: Optional[ToolCallingMethod] = 'auto'


@dataclass
class AgentStepInfo:
    """Information about the current step of the agent"""
    step_number: int
    max_steps: int
    task: str
    memory: str = ""


@dataclass
class StepMetadata:
    """Metadata about a step in the agent's execution"""
    step_number: int
    timestamp: float
    duration: float
    success: bool
    error: Optional[str] = None
    action_results: Optional[List[Dict[str, Any]]] = None


@dataclass
class CustomAgentStepInfo:
    step_number: int
    max_steps: int
    task: str
    add_infos: str
    memory: str


class CustomAgentBrain(BaseModel):
    """Current state of the agent"""

    evaluation_previous_goal: str
    important_contents: str
    thought: str
    next_goal: str


class CustomAgentOutput(AgentOutput):
    """Output model for agent

    @dev note: this model is extended with custom actions in AgentService. You can also use some fields that are not in this model as provided by the linter, as long as they are registered in the DynamicActions model.
    """

    current_state: CustomAgentBrain

    @staticmethod
    def type_with_custom_actions(
            custom_actions: Type[ActionModel],
    ) -> Type["CustomAgentOutput"]:
        """Extend actions with custom actions"""
        model_ = create_model(
            "CustomAgentOutput",
            __base__=CustomAgentOutput,
            action=(
                list[custom_actions],
                Field(..., description='List of actions to execute', json_schema_extra={'min_items': 1}),
            ),  # Properly annotated field with no default
            __module__=CustomAgentOutput.__module__,
        )
        model_.__doc__ = 'AgentOutput model with custom actions'
        return model_


class CustomAgentState(BaseModel):
    agent_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    n_steps: int = 1
    consecutive_failures: int = 0
    last_result: Optional[List['ActionResult']] = None
    history: AgentHistoryList = Field(default_factory=lambda: AgentHistoryList(history=[]))
    last_plan: Optional[str] = None
    paused: bool = False
    stopped: bool = False

    message_manager_state: MessageManagerState = Field(default_factory=MessageManagerState)

    last_action: Optional[List['ActionModel']] = None
    extracted_content: str = ''
