import base64
import os
import time
from pathlib import Path
from typing import Dict, Optional
import requests
import json
import gradio as gr
import uuid

from langchain_anthropic import ChatAnthropic
from langchain_mistralai import ChatMistralAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import AzureChatOpenAI, ChatOpenAI

from .llm import DeepSeekR1ChatOpenAI, DeepSeekR1ChatOllama

PROVIDER_DISPLAY_NAMES = {
    "openai": "OpenAI",
    "azure_openai": "Azure OpenAI",
    "anthropic": "Anthropic",
    "deepseek": "DeepSeek",
    "google": "Google",
    "mistral": "Mistral",
    "alibaba": "Alibaba",
    "moonshot": "MoonShot"
}

def get_llm_model(provider: str, **kwargs):
    """
    获取LLM 模型
    :param provider: 模型类型
    :param kwargs:
    :return:
    """
    api_key = None
    if provider not in {"ollama"}:
        env_var = f"{provider.upper()}_API_KEY"
        api_key = get_config_value(provider, "api_key", **kwargs)
        if not api_key:
            raise MissingAPIKeyError(provider, env_var)

    base_url = get_config_value(provider, "base_url", **kwargs)
    model_name = get_config_value(provider, "model_name", **kwargs)
    temperature = kwargs.get("temperature", 0.0)

    common_params = {
        "model": model_name,
        "temperature": temperature,
        "base_url": base_url,
        "api_key": api_key,
    }

    if provider == "anthropic":
        return ChatAnthropic(**common_params)
    elif provider == "mistral":
        return ChatMistralAI(**common_params)
    elif provider in {"openai", "alibaba", "moonshot"}:
        return ChatOpenAI(**common_params)
    elif provider == "deepseek":
        if model_name == "deepseek-reasoner":
            return DeepSeekR1ChatOpenAI(**common_params)
        return ChatOpenAI(**common_params)

    elif provider == "google":
        common_params.pop("base_url", None)
        return ChatGoogleGenerativeAI(**common_params)
    elif provider == "ollama":
        common_params.pop("api_key", None)
        common_params["num_ctx"] = kwargs.get("num_ctx", 32000)

        if "deepseek-r1" in model_name:
             common_params["model"] = kwargs.get("model_name", "deepseek-r1:14b")
             return DeepSeekR1ChatOllama(**common_params)
        else:
             common_params["num_predict"] = kwargs.get("num_predict", 1024)
             return ChatOllama(**common_params)
    elif provider == "azure_openai":
        common_params["api_version"] = get_config_value(provider, "api_version", **kwargs)
        common_params["azure_endpoint"] = common_params.pop("base_url", None)
        return AzureChatOpenAI(**common_params)
    else:
        raise ValueError(f"Unsupported provider: {provider}")

PROVIDER_CONFIGS = {
    "openai": {"default_model": "gpt-4o", "default_base_url": "https://api.openai.com/v1"},
    "azure_openai": {"default_model": "gpt-4o", "default_api_version": "2025-01-01-preview"},
    "anthropic": {"default_model": "claude-3-5-sonnet-20241022", "default_base_url": "https://api.anthropic.com"},
    "google": {"default_model": "gemini-2.0-flash"},
    "deepseek": {"default_model": "deepseek-chat", "default_base_url": "https://api.deepseek.com"},
    "mistral": {"default_model": "mistral-large-latest", "default_base_url": "https://api.mistral.ai/v1"},
    "alibaba": {"default_model": "qwen-plus", "default_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"},
    "moonshot": {"default_model": "moonshot-v1-32k-vision-preview", "default_base_url": "https://api.moonshot.cn/v1"},
    "ollama": {"default_model": "qwen2.5:7b", "default_base_url": "http://localhost:11434"}
}

# Predefined model names for common providers
model_names = {
    "anthropic": ["claude-3-5-sonnet-20241022", "claude-3-5-sonnet-20240620", "claude-3-opus-20240229"],
    "openai": ["gpt-4o", "gpt-4", "gpt-3.5-turbo", "o3-mini"],
    "deepseek": ["deepseek-chat", "deepseek-reasoner"],
    "google": ["gemini-2.0-flash", "gemini-2.0-flash-thinking-exp", "gemini-1.5-flash-latest",
               "gemini-1.5-flash-8b-latest", "gemini-2.0-flash-thinking-exp-01-21", "gemini-2.0-pro-exp-02-05"],
    "ollama": ["qwen2.5:7b", "qwen2.5:14b", "qwen2.5:32b", "qwen2.5-coder:14b", "qwen2.5-coder:32b", "llama2:7b",
               "deepseek-r1:14b", "deepseek-r1:32b"],
    "azure_openai": ["gpt-4o", "gpt-4", "gpt-3.5-turbo"],
    "mistral": ["pixtral-large-latest", "mistral-large-latest", "mistral-small-latest", "ministral-8b-latest"],
    "alibaba": ["qwen-plus", "qwen-max", "qwen-turbo", "qwen-long"],
    "moonshot": ["moonshot-v1-32k-vision-preview", "moonshot-v1-8k-vision-preview"],
}

def get_config_value(provider: str, key: str, **kwargs):
    """Retrieves a configuration value for a given provider and key."""
    config = PROVIDER_CONFIGS.get(provider, {})

    if key in kwargs and kwargs[key]:
        return kwargs[key]

    env_key_name = None
    if key == "api_key":
        env_key_name = f"{provider.upper()}_API_KEY"
    elif key == "base_url":
        env_key_name = f"{provider.upper()}_ENDPOINT"
    elif key == "api_version":
        env_key_name = f"{provider.upper()}_API_VERSION"

    if env_key_name:
        env_value = os.getenv(env_key_name)
        if env_value:
            return env_value

    return config.get(f"default_{key}")

# Callback to update the model name dropdown based on the selected provider
def update_model_dropdown(llm_provider, api_key=None, base_url=None):
    """
    Update the model name dropdown with predefined models for the selected provider.
    """
    import gradio as gr
    # Use API keys from .env if not provided
    if not api_key:
        api_key = get_config_value(llm_provider, "api_key")
    if not base_url:
        base_url = get_config_value(llm_provider, "base_url")

    # Use predefined models for the selected provider
    if llm_provider in model_names:
        return gr.Dropdown(choices=model_names[llm_provider], value=model_names[llm_provider][0], interactive=True)
    else:
        return gr.Dropdown(choices=[], value="", interactive=True, allow_custom_value=True)


class MissingAPIKeyError(Exception):
    """Custom exception for missing API key."""

    def __init__(self, provider: str, env_var: str):
        provider_display = PROVIDER_DISPLAY_NAMES.get(provider, provider.upper())
        super().__init__(f"💥 {provider_display} API key not found! 🔑 Please set the "
                         f"`{env_var}` environment variable or provide it in the UI.")


def encode_image(img_path):
    if not img_path:
        return None
    with open(img_path, "rb") as fin:
        image_data = base64.b64encode(fin.read()).decode("utf-8")
    return image_data


def get_latest_files(directory: str, file_types: list = ['.webm', '.zip']) -> Dict[str, Optional[str]]:
    """Get the latest recording and trace files"""
    latest_files: Dict[str, Optional[str]] = {ext: None for ext in file_types}

    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
        return latest_files

    for file_type in file_types:
        try:
            matches = list(Path(directory).rglob(f"*{file_type}"))
            if matches:
                latest = max(matches, key=lambda p: p.stat().st_mtime)
                # Only return files that are complete (not being written)
                if time.time() - latest.stat().st_mtime > 1.0:
                    latest_files[file_type] = str(latest)
        except Exception as e:
            print(f"Error getting latest {file_type} file: {e}")

    return latest_files


async def capture_screenshot(browser_context):
    """Capture and encode a screenshot"""
    # Extract the Playwright browser instance
    playwright_browser = browser_context.browser.playwright_browser  # Ensure this is correct.

    # Check if the browser instance is valid and if an existing context can be reused
    if playwright_browser and playwright_browser.contexts:
        playwright_context = playwright_browser.contexts[0]
    else:
        return None

    # Access pages in the context
    pages = None
    if playwright_context:
        pages = playwright_context.pages

    # Use an existing page or create a new one if none exist
    if pages:
        active_page = pages[0]
        for page in pages:
            if page.url != "about:blank":
                active_page = page
    else:
        return None

    # Take screenshot
    try:
        screenshot = await active_page.screenshot(
            type='jpeg',
            quality=75,
            scale="css"
        )
        encoded = base64.b64encode(screenshot).decode('utf-8')
        return encoded
    except Exception as e:
        return None


class ConfigManager:
    def __init__(self):
        self.components = {}
        self.component_order = []

    def register_component(self, name: str, component):
        """Register a gradio component for config management."""
        self.components[name] = component
        if name not in self.component_order:
            self.component_order.append(name)
        return component

    def save_current_config(self):
        """Save the current configuration of all registered components."""
        current_config = {}
        for name in self.component_order:
            component = self.components[name]
            # Get the current value from the component
            current_config[name] = getattr(component, "value", None)

        return save_config_to_file(current_config)

    def update_ui_from_config(self, config_file):
        """Update UI components from a loaded configuration file."""
        if config_file is None:
            return [gr.update() for _ in self.component_order] + ["No file selected."]

        loaded_config = load_config_from_file(config_file.name)

        if not isinstance(loaded_config, dict):
            return [gr.update() for _ in self.component_order] + ["Error: Invalid configuration file."]

        # Prepare updates for all components
        updates = []
        for name in self.component_order:
            if name in loaded_config:
                updates.append(gr.update(value=loaded_config[name]))
            else:
                updates.append(gr.update())

        updates.append("Configuration loaded successfully.")
        return updates

    def get_all_components(self):
        """Return all registered components in the order they were registered."""
        return [self.components[name] for name in self.component_order]


def load_config_from_file(config_file):
    """Load settings from a config file (JSON format)."""
    try:
        with open(config_file, 'r') as f:
            settings = json.load(f)
        return settings
    except Exception as e:
        return f"Error loading configuration: {str(e)}"


def save_config_to_file(settings, save_dir="./tmp/webui_settings"):
    """Save the current settings to a UUID.json file with a UUID name."""
    os.makedirs(save_dir, exist_ok=True)
    config_file = os.path.join(save_dir, f"{uuid.uuid4()}.json")
    with open(config_file, 'w') as f:
        json.dump(settings, f, indent=2)
    return f"Configuration saved to {config_file}"
