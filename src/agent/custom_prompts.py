import pdb
from typing import List, Optional

from src.agent.base_views import ActionResult, ActionModel, BrowserState
from langchain_core.messages import HumanMessage, SystemMessage
from datetime import datetime
import importlib

from .custom_views import CustomAgentStepInfo


class CustomSystemPrompt:
    def __init__(self):
        self.prompt_template = None
        self._load_prompt_template()

    def _load_prompt_template(self) -> None:
        """Load the prompt template from the markdown file."""
        try:
            # This works both in development and when installed as a package
            with importlib.resources.files('src.agent').joinpath('custom_system_prompt.md').open('r') as f:
                self.prompt_template = f.read()
        except Exception as e:
            raise RuntimeError(f'Failed to load system prompt template: {e}')

    def get_system_message(self) -> SystemMessage:
        if not self.prompt_template:
            raise RuntimeError('Prompt template not loaded')
        return SystemMessage(content=self.prompt_template)


class CustomAgentMessagePrompt:
    def __init__(
            self,
            state: BrowserState,
            actions: Optional[List[ActionModel]] = None,
            result: Optional[List[ActionResult]] = None,
            include_attributes: list[str] = [],
            step_info: Optional[CustomAgentStepInfo] = None,
    ):
        self.state = state
        self.actions = actions
        self.result = result
        self.include_attributes = include_attributes
        self.step_info = step_info

    def get_user_message(self, use_vision: bool = True) -> HumanMessage:
        if self.step_info:
            step_info_description = f'Current step: {self.step_info.step_number}/{self.step_info.max_steps}\n'
        else:
            step_info_description = ''

        time_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        step_info_description += f"Current date and time: {time_str}"

        elements_text = self.state.element_tree.clickable_elements_to_string(include_attributes=self.include_attributes)

        has_content_above = (self.state.pixels_above or 0) > 0
        has_content_below = (self.state.pixels_below or 0) > 0

        if elements_text != '':
            if has_content_above:
                elements_text = (
                    f'... {self.state.pixels_above} pixels above - scroll or extract content to see more ...\n{elements_text}'
                )
            else:
                elements_text = f'[Start of page]\n{elements_text}'
            if has_content_below:
                elements_text = (
                    f'{elements_text}\n... {self.state.pixels_below} pixels below - scroll or extract content to see more ...'
                )
            else:
                elements_text = f'{elements_text}\n[End of page]'
        else:
            elements_text = 'empty page'

        state_description = f"""
{step_info_description}
1. Task: {self.step_info.task}. 
2. Hints(Optional): 
{self.step_info.add_infos}
3. Memory: 
{self.step_info.memory}
4. Current url: {self.state.url}
5. Available tabs:
{self.state.tabs}
6. Interactive elements:
{elements_text}
        """

        if self.actions and self.result:
            state_description += "\n **Previous Actions** \n"
            state_description += f'Previous step: {self.step_info.step_number - 1}/{self.step_info.max_steps} \n'
            for i, result in enumerate(self.result):
                action = self.actions[i]
                state_description += f"Previous action {i + 1}/{len(self.result)}: {action.model_dump_json(exclude_unset=True)}\n"
                if result.error:
                    # only use last 300 characters of error
                    error = result.error.split('\n')[-1]
                    state_description += (
                        f"Error of previous action {i + 1}/{len(self.result)}: ...{error}\n"
                    )
                if result.include_in_memory:
                    if result.extracted_content:
                        state_description += f"Result of previous action {i + 1}/{len(self.result)}: {result.extracted_content}\n"

        if self.state.screenshot and use_vision == True:
            # Format message for vision model
            return HumanMessage(
                content=[
                    {'type': 'text', 'text': state_description},
                    {
                        'type': 'image_url',
                        'image_url': {'url': f'data:image/png;base64,{self.state.screenshot}'},
                    },
                ]
            )

        return HumanMessage(content=state_description)
