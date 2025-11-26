import asyncio
import json
import os
import shutil
import time
from datetime import datetime

import gradio as gr
from browser_use.agent.service import Agent
from gradio.components import Component

from src.web_ui.agent.deep_research.deep_research_agent import DeepResearchAgent
from src.web_ui.browser.custom_browser import CustomBrowser
from src.web_ui.browser.custom_context import CustomBrowserContext
from src.web_ui.controller.custom_controller import CustomController
from src.web_ui.utils.config import (
    DEFAULT_SETTINGS_FILE,
    OLD_SETTINGS_DIR,
    SETTINGS_ARCHIVE_DIR,
    ensure_settings_directories,
    is_runtime_component,
)


class WebuiManager:
    def __init__(self, settings_save_dir: str = SETTINGS_ARCHIVE_DIR):
        self.id_to_component: dict[str, Component] = {}
        self.component_to_id: dict[Component, str] = {}

        self.settings_save_dir = settings_save_dir
        ensure_settings_directories()

        # Dashboard state management
        self.settings_panel_visible: bool = False
        self.current_agent_type: str = "browser_use"  # "browser_use" or "deep_research"
        self.recent_tasks: list[dict] = []  # List of recent task executions
        self.token_usage: dict = {"used": 0, "cost": 0.0}  # Token usage tracking

    def init_browser_use_agent(self) -> None:
        """
        init browser use agent
        """
        self.bu_agent: Agent | None = None
        self.bu_browser: CustomBrowser | None = None
        self.bu_browser_context: CustomBrowserContext | None = None
        self.bu_controller: CustomController | None = None
        self.bu_chat_history: list[dict[str, str | None]] = []
        self.bu_response_event: asyncio.Event | None = None
        self.bu_user_help_response: str | None = None
        self.bu_current_task: asyncio.Task | None = None
        self.bu_agent_task_id: str | None = None

    def init_deep_research_agent(self) -> None:
        """
        init deep research agent
        """
        self.dr_agent: DeepResearchAgent | None = None
        self.dr_current_task = None
        self.dr_agent_task_id: str | None = None
        self.dr_task_id: str | None = None
        self.dr_save_dir: str | None = None

    def add_components(self, tab_name: str, components_dict: dict[str, Component]) -> None:
        """
        Add tab components
        """
        for comp_name, component in components_dict.items():
            comp_id = f"{tab_name}.{comp_name}"
            self.id_to_component[comp_id] = component
            self.component_to_id[component] = comp_id

    def get_components(self) -> list[Component]:
        """
        Get all components
        """
        return list(self.id_to_component.values())

    def get_component_by_id(self, comp_id: str) -> Component:
        """
        Get component by id
        """
        return self.id_to_component[comp_id]

    def get_id_by_component(self, comp: Component) -> str:
        """
        Get id by component
        """
        return self.component_to_id[comp]

    def save_config(self, *args, as_default: bool = False) -> str:
        """
        Save config to timestamped file or as default.

        Args:
            *args: Component values
            as_default: If True, save as default_settings.json instead of timestamped file

        Returns:
            Path to saved config file
        """
        # Convert args to components dict
        components = {}
        all_components = list(self.id_to_component.values())
        for i, comp in enumerate(all_components):
            if i < len(args):
                components[comp] = args[i]

        cur_settings = {}
        for comp in components:
            if (
                not isinstance(comp, gr.Button)
                and not isinstance(comp, gr.File)
                and str(getattr(comp, "interactive", True)).lower() != "false"
            ):
                comp_id = self.get_id_by_component(comp)
                # Filter out runtime-only components
                if not is_runtime_component(comp_id):
                    cur_settings[comp_id] = components[comp]

        if as_default:
            config_path = DEFAULT_SETTINGS_FILE
        else:
            config_name = datetime.now().strftime("%Y%m%d-%H%M%S")
            config_path = os.path.join(self.settings_save_dir, f"{config_name}.json")

        with open(config_path, "w") as fw:
            json.dump(cur_settings, fw, indent=4)

        return config_path

    def load_config(self, config_path: str):
        """
        Load config
        """
        with open(config_path) as fr:
            ui_settings = json.load(fr)

        update_components = {}
        for comp_id, comp_val in ui_settings.items():
            if comp_id in self.id_to_component:
                comp = self.id_to_component[comp_id]
                if comp.__class__.__name__ == "Chatbot":
                    update_components[comp] = comp.__class__(value=comp_val, type="messages")
                else:
                    update_components[comp] = comp.__class__(value=comp_val)
                    if comp_id == "agent_settings.planner_llm_provider":
                        yield update_components  # yield provider, let callback run
                        time.sleep(0.1)  # wait for Gradio UI callback

        config_status = self.id_to_component["load_save_config.config_status"]
        update_components.update(
            {
                config_status: config_status.__class__(
                    value=f"Successfully loaded config: {config_path}"
                )
            }
        )
        yield update_components

    def load_default_settings(self) -> bool:
        """
        Load default settings if they exist.

        Returns:
            True if default settings were loaded, False otherwise
        """
        if os.path.exists(DEFAULT_SETTINGS_FILE):
            try:
                # Load default settings without showing status message
                with open(DEFAULT_SETTINGS_FILE) as fr:
                    ui_settings = json.load(fr)

                update_components = {}
                provider_changed = False
                provider_value = None

                for comp_id, comp_val in ui_settings.items():
                    if comp_id in self.id_to_component:
                        comp = self.id_to_component[comp_id]
                        if comp.__class__.__name__ == "Chatbot":
                            update_components[comp] = comp.__class__(
                                value=comp_val, type="messages"
                            )
                        else:
                            update_components[comp] = comp.__class__(value=comp_val)

                        # Track if provider changed to trigger model dropdown update
                        if "llm_provider" in comp_id:
                            provider_changed = True
                            provider_value = comp_val

                # Apply updates without yielding (blocking update)
                for comp, val in update_components.items():
                    comp.value = val

                # Manually trigger provider change to update model dropdown
                if provider_changed and provider_value:
                    try:
                        # Import here to avoid circular dependencies
                        from src.web_ui.webui.components.dashboard_settings import (
                            update_model_dropdown,
                        )

                        # Update model dropdown for the provider
                        model_update = update_model_dropdown(provider_value)

                        # Find and update the model component
                        model_comp_id = comp_id.replace("llm_provider", "llm_model_name")
                        if model_comp_id in self.id_to_component:
                            model_comp = self.id_to_component[model_comp_id]
                            model_comp.value = model_update.get("value", "")
                            # Also update choices if available
                            if "choices" in model_update:
                                model_comp.choices = model_update["choices"]

                    except Exception as e:
                        print(f"Warning: Could not trigger model dropdown update: {e}")

                return True
            except Exception as e:
                print(f"Failed to load default settings: {e}")
                return False
        return False

    def save_as_default(self, *args) -> str:
        """
        Save current settings as default.

        Args:
            *args: Component values

        Returns:
            Path to saved default settings file
        """
        return self.save_config(*args, as_default=True)

    def migrate_old_settings(self) -> int:
        """
        Migrate old settings from tmp/webui_settings to data/saved_configs.

        Returns:
            Number of files migrated
        """
        migrated_count = 0
        if os.path.exists(OLD_SETTINGS_DIR):
            try:
                for filename in os.listdir(OLD_SETTINGS_DIR):
                    if filename.endswith(".json"):
                        src = os.path.join(OLD_SETTINGS_DIR, filename)
                        dst = os.path.join(self.settings_save_dir, filename)
                        shutil.copy2(src, dst)
                        migrated_count += 1
                print(f"Migrated {migrated_count} settings files from {OLD_SETTINGS_DIR}")
            except Exception as e:
                print(f"Failed to migrate old settings: {e}")
        return migrated_count

    def toggle_settings_panel(self) -> bool:
        """
        Toggle the settings panel visibility.

        Returns:
            bool: New visibility state
        """
        self.settings_panel_visible = not self.settings_panel_visible
        return self.settings_panel_visible

    def add_recent_task(self, task: str, success: bool = True, result: str | None = None) -> None:
        """
        Add a task to recent tasks history.

        Args:
            task: Task description
            success: Whether the task completed successfully
            result: Optional result summary
        """
        from datetime import datetime

        task_entry = {
            "task": task,
            "success": success,
            "result": result,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        }

        self.recent_tasks.append(task_entry)

        # Keep only last 20 tasks
        if len(self.recent_tasks) > 20:
            self.recent_tasks = self.recent_tasks[-20:]

    def update_token_usage(self, tokens: int, cost: float = 0.0) -> None:
        """
        Update token usage statistics.

        Args:
            tokens: Number of tokens used
            cost: Estimated cost in USD
        """
        self.token_usage["used"] += tokens
        self.token_usage["cost"] += cost

    def reset_token_usage(self) -> None:
        """Reset token usage statistics."""
        self.token_usage = {"used": 0, "cost": 0.0}

    def get_status_summary(self) -> dict:
        """
        Get a summary of current system status.

        Returns:
            dict with status information
        """
        return {
            "settings_visible": self.settings_panel_visible,
            "current_agent": self.current_agent_type,
            "browser_open": bool(self.bu_browser),
            "recent_task_count": len(self.recent_tasks),
            "token_usage": self.token_usage,
        }
