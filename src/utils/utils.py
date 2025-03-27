import base64
import os
import time
from pathlib import Path
from typing import Dict, Optional
import requests

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
    "alibaba": "Alibaba",
    "moonshot": "MoonShot",
    "openrouter": "OpenRouter"
}


def get_llm_model(provider: str, **kwargs):
    """
    获取LLM 模型
    :param provider: 模型类型
    :param kwargs:
    :return:
    """
    if provider not in ["ollama"]:
        env_var = f"{provider.upper()}_API_KEY"
        api_key = kwargs.get("api_key", "") or os.getenv(env_var, "")
        if not api_key:
            raise MissingAPIKeyError(provider, env_var)
        kwargs["api_key"] = api_key

    if provider == "anthropic":
        if not kwargs.get("base_url", ""):
            base_url = "https://api.anthropic.com"
        else:
            base_url = kwargs.get("base_url")

        return ChatAnthropic(
            model=kwargs.get("model_name", "claude-3-5-sonnet-20241022"),
            temperature=kwargs.get("temperature", 0.0),
            base_url=base_url,
            api_key=api_key,
        )
    elif provider == 'mistral':
        if not kwargs.get("base_url", ""):
            base_url = os.getenv("MISTRAL_ENDPOINT", "https://api.mistral.ai/v1")
        else:
            base_url = kwargs.get("base_url")
        if not kwargs.get("api_key", ""):
            api_key = os.getenv("MISTRAL_API_KEY", "")
        else:
            api_key = kwargs.get("api_key")

        return ChatMistralAI(
            model=kwargs.get("model_name", "mistral-large-latest"),
            temperature=kwargs.get("temperature", 0.0),
            base_url=base_url,
            api_key=api_key,
        )
    elif provider == "openai":
        if not kwargs.get("base_url", ""):
            base_url = os.getenv("OPENAI_ENDPOINT", "https://api.openai.com/v1")
        else:
            base_url = kwargs.get("base_url")

        return ChatOpenAI(
            model=kwargs.get("model_name", "gpt-4o"),
            temperature=kwargs.get("temperature", 0.0),
            base_url=base_url,
            api_key=api_key,
        )
    elif provider == "deepseek":
        if not kwargs.get("base_url", ""):
            base_url = os.getenv("DEEPSEEK_ENDPOINT", "")
        else:
            base_url = kwargs.get("base_url")

        if kwargs.get("model_name", "deepseek-chat") == "deepseek-reasoner":
            return DeepSeekR1ChatOpenAI(
                model=kwargs.get("model_name", "deepseek-reasoner"),
                temperature=kwargs.get("temperature", 0.0),
                base_url=base_url,
                api_key=api_key,
            )
        else:
            return ChatOpenAI(
                model=kwargs.get("model_name", "deepseek-chat"),
                temperature=kwargs.get("temperature", 0.0),
                base_url=base_url,
                api_key=api_key,
            )
    elif provider == "google":
        return ChatGoogleGenerativeAI(
            model=kwargs.get("model_name", "gemini-2.0-flash-exp"),
            temperature=kwargs.get("temperature", 0.0),
            api_key=api_key,
        )
    elif provider == "ollama":
        if not kwargs.get("base_url", ""):
            base_url = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434")
        else:
            base_url = kwargs.get("base_url")

        if "deepseek-r1" in kwargs.get("model_name", "qwen2.5:7b"):
            return DeepSeekR1ChatOllama(
                model=kwargs.get("model_name", "deepseek-r1:14b"),
                temperature=kwargs.get("temperature", 0.0),
                num_ctx=kwargs.get("num_ctx", 32000),
                base_url=base_url,
            )
        else:
            return ChatOllama(
                model=kwargs.get("model_name", "qwen2.5:7b"),
                temperature=kwargs.get("temperature", 0.0),
                num_ctx=kwargs.get("num_ctx", 32000),
                num_predict=kwargs.get("num_predict", 1024),
                base_url=base_url,
            )
    elif provider == "azure_openai":
        if not kwargs.get("base_url", ""):
            base_url = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        else:
            base_url = kwargs.get("base_url")
        api_version = kwargs.get("api_version", "") or os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
        return AzureChatOpenAI(
            model=kwargs.get("model_name", "gpt-4o"),
            temperature=kwargs.get("temperature", 0.0),
            api_version=api_version,
            azure_endpoint=base_url,
            api_key=api_key,
        )
    elif provider == "alibaba":
        if not kwargs.get("base_url", ""):
            base_url = os.getenv("ALIBABA_ENDPOINT", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        else:
            base_url = kwargs.get("base_url")

        return ChatOpenAI(
            model=kwargs.get("model_name", "qwen-plus"),
            temperature=kwargs.get("temperature", 0.0),
            base_url=base_url,
            api_key=api_key,
        )

    elif provider == "moonshot":
        if not kwargs.get("base_url", ""):
            base_url = os.getenv("MOONSHOT_ENDPOINT", "https://api.moonshot.cn/v1")
        else:
            base_url = kwargs.get("base_url")

        return ChatOpenAI(
            model=kwargs.get("model_name", "moonshot-v1-32k-vision-preview"),
            temperature=kwargs.get("temperature", 0.0),
            base_url=base_url,
            api_key=api_key,
        )
    elif provider == "openrouter":
        if not kwargs.get("base_url", ""):
            base_url = os.getenv("OPENROUTER_ENDPOINT", "https://openrouter.ai/api/v1")
        else:
            base_url = kwargs.get("base_url")

        return ChatOpenAI(
            model=kwargs.get("model_name", "openrouter/auto"),
            temperature=kwargs.get("temperature", 0.0),
            base_url=base_url,
            api_key=api_key,
            default_headers={
                "HTTP-Referer": "https://github.com/browser-use/web-ui",
                "X-Title": "Browser-Use WebUI"
            }
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")


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
    "openrouter": [
        "mistralai/mistral-small-3.1-24b-instruct:free",
        "mistralai/mistral-small-3.1-24b-instruct",
        "open-r1/olympiccoder-7b:free",
        "open-r1/olympiccoder-32b:free",
        "steelskull/l3.3-electra-r1-70b",
        "allenai/olmo-2-0325-32b-instruct",
        "google/gemma-3-1b-it:free",
        "google/gemma-3-4b-it:free",
        "ai21/jamba-1.6-large",
        "ai21/jamba-1.6-mini",
        "google/gemma-3-12b-it:free",
        "cohere/command-a",
        "openai/gpt-4o-mini-search-preview",
        "openai/gpt-4o-search-preview",
        "tokyotech-llm/llama-3.1-swallow-70b-instruct-v0.3",
        "rekaai/reka-flash-3:free",
        "google/gemma-3-27b-it:free",
        "google/gemma-3-27b-it",
        "thedrummer/anubis-pro-105b-v1",
        "latitudegames/wayfarer-large-70b-llama-3.3",
        "thedrummer/skyfall-36b-v2",
        "microsoft/phi-4-multimodal-instruct",
        "perplexity/sonar-reasoning-pro",
        "perplexity/sonar-pro",
        "perplexity/sonar-deep-research",
        "deepseek/deepseek-r1-zero:free",
        "qwen/qwq-32b:free",
        "qwen/qwq-32b",
        "qwen/qwen2.5-32b-instruct",
        "moonshotai/moonlight-16b-a3b-instruct:free",
        "nousresearch/deephermes-3-llama-3-8b-preview:free",
        "openai/gpt-4.5-preview",
        "google/gemini-2.0-flash-lite-001",
        "anthropic/claude-3.7-sonnet:beta",
        "anthropic/claude-3.7-sonnet",
        "anthropic/claude-3.7-sonnet:thinking",
        "perplexity/r1-1776",
        "mistralai/mistral-saba",
        "cognitivecomputations/dolphin3.0-r1-mistral-24b:free",
        "cognitivecomputations/dolphin3.0-mistral-24b:free",
        "meta-llama/llama-guard-3-8b",
        "openai/o3-mini-high",
        "allenai/llama-3.1-tulu-3-405b",
        "deepseek/deepseek-r1-distill-llama-8b",
        "google/gemini-2.0-flash-001",
        "google/gemini-2.0-flash-lite-preview-02-05:free",
        "google/gemini-2.0-pro-exp-02-05:free",
        "qwen/qwen-vl-plus",
        "aion-labs/aion-1.0",
        "aion-labs/aion-1.0-mini",
        "aion-labs/aion-rp-llama-3.1-8b",
        "qwen/qwen-vl-max",
        "qwen/qwen-turbo",
        "qwen/qwen2.5-vl-72b-instruct:free",
        "qwen/qwen2.5-vl-72b-instruct",
        "qwen/qwen-plus",
        "qwen/qwen-max",
        "openai/o3-mini",
        "deepseek/deepseek-r1-distill-qwen-1.5b",
        "mistralai/mistral-small-24b-instruct-2501:free",
        "mistralai/mistral-small-24b-instruct-2501",
        "deepseek/deepseek-r1-distill-qwen-32b:free",
        "deepseek/deepseek-r1-distill-qwen-32b",
        "deepseek/deepseek-r1-distill-qwen-14b:free",
        "deepseek/deepseek-r1-distill-qwen-14b",
        "perplexity/sonar-reasoning",
        "perplexity/sonar",
        "liquid/lfm-7b",
        "liquid/lfm-3b",
        "deepseek/deepseek-r1-distill-llama-70b:free",
        "deepseek/deepseek-r1-distill-llama-70b",
        "google/gemini-2.0-flash-thinking-exp:free",
        "deepseek/deepseek-r1:free",
        "deepseek/deepseek-r1",
        "sophosympatheia/rogue-rose-103b-v0.2:free",
        "minimax/minimax-01",
        "mistralai/codestral-2501",
        "microsoft/phi-4",
        "sao10k/l3.1-70b-hanami-x1",
        "deepseek/deepseek-chat:free",
        "deepseek/deepseek-chat",
        "google/gemini-2.0-flash-thinking-exp-1219:free",
        "sao10k/l3.3-euryale-70b",
        "openai/o1",
        "eva-unit-01/eva-llama-3.33-70b",
        "x-ai/grok-2-vision-1212",
        "x-ai/grok-2-1212",
        "cohere/command-r7b-12-2024",
        "google/gemini-2.0-flash-exp:free",
        "google/gemini-exp-1206:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "meta-llama/llama-3.3-70b-instruct",
        "amazon/nova-lite-v1",
        "amazon/nova-micro-v1",
        "amazon/nova-pro-v1",
        "qwen/qwq-32b-preview:free",
        "qwen/qwq-32b-preview",
        "google/learnlm-1.5-pro-experimental:free",
        "eva-unit-01/eva-qwen-2.5-72b",
        "openai/gpt-4o-2024-11-20",
        "mistralai/mistral-large-2411",
        "mistralai/mistral-large-2407",
        "mistralai/pixtral-large-2411",
        "x-ai/grok-vision-beta",
        "infermatic/mn-inferor-12b",
        "qwen/qwen-2.5-coder-32b-instruct:free",
        "qwen/qwen-2.5-coder-32b-instruct",
        "raifle/sorcererlm-8x22b",
        "eva-unit-01/eva-qwen-2.5-32b",
        "thedrummer/unslopnemo-12b",
        "anthropic/claude-3.5-haiku-20241022:beta",
        "anthropic/claude-3.5-haiku-20241022",
        "anthropic/claude-3.5-haiku:beta",
        "anthropic/claude-3.5-haiku",
        "neversleep/llama-3.1-lumimaid-70b",
        "anthracite-org/magnum-v4-72b",
        "anthropic/claude-3.5-sonnet:beta",
        "anthropic/claude-3.5-sonnet",
        "x-ai/grok-beta",
        "mistralai/ministral-8b",
        "mistralai/ministral-3b",
        "qwen/qwen-2.5-7b-instruct",
        "nvidia/llama-3.1-nemotron-70b-instruct:free",
        "nvidia/llama-3.1-nemotron-70b-instruct",
        "inflection/inflection-3-pi",
        "inflection/inflection-3-productivity",
        "google/gemini-flash-1.5-8b",
        "anthracite-org/magnum-v2-72b",
        "liquid/lfm-40b",
        "thedrummer/rocinante-12b",
        "meta-llama/llama-3.2-3b-instruct:free",
        "meta-llama/llama-3.2-3b-instruct",
        "meta-llama/llama-3.2-1b-instruct:free",
        "meta-llama/llama-3.2-1b-instruct",
        "meta-llama/llama-3.2-90b-vision-instruct",
        "meta-llama/llama-3.2-11b-vision-instruct:free",
        "meta-llama/llama-3.2-11b-vision-instruct",
        "qwen/qwen-2.5-72b-instruct:free",
        "qwen/qwen-2.5-72b-instruct",
        "qwen/qwen-2.5-vl-72b-instruct",
        "neversleep/llama-3.1-lumimaid-8b",
        "openai/o1-mini-2024-09-12",
        "openai/o1-preview",
        "openai/o1-preview-2024-09-12",
        "openai/o1-mini",
        "mistralai/pixtral-12b",
        "cohere/command-r-08-2024",
        "cohere/command-r-plus-08-2024",
        "sao10k/l3.1-euryale-70b",
        "google/gemini-flash-1.5-8b-exp",
        "qwen/qwen-2.5-vl-7b-instruct",
        "ai21/jamba-1-5-large",
        "ai21/jamba-1-5-mini",
        "microsoft/phi-3.5-mini-128k-instruct",
        "nousresearch/hermes-3-llama-3.1-70b",
        "nousresearch/hermes-3-llama-3.1-405b",
        "openai/chatgpt-4o-latest",
        "sao10k/l3-lunaris-8b",
        "aetherwiing/mn-starcannon-12b",
        "openai/gpt-4o-2024-08-06",
        "meta-llama/llama-3.1-405b",
        "nothingiisreal/mn-celeste-12b",
        "perplexity/llama-3.1-sonar-small-128k-online",
        "perplexity/llama-3.1-sonar-large-128k-online",
        "meta-llama/llama-3.1-405b-instruct",
        "meta-llama/llama-3.1-8b-instruct:free",
        "meta-llama/llama-3.1-8b-instruct",
        "meta-llama/llama-3.1-70b-instruct",
        "mistralai/mistral-nemo:free",
        "mistralai/mistral-nemo",
        "mistralai/codestral-mamba",
        "openai/gpt-4o-mini",
        "openai/gpt-4o-mini-2024-07-18",
        "qwen/qwen-2-7b-instruct:free",
        "qwen/qwen-2-7b-instruct",
        "google/gemma-2-27b-it",
        "alpindale/magnum-72b",
        "google/gemma-2-9b-it:free",
        "google/gemma-2-9b-it",
        "01-ai/yi-large",
        "ai21/jamba-instruct",
        "anthropic/claude-3.5-sonnet-20240620:beta",
        "anthropic/claude-3.5-sonnet-20240620",
        "sao10k/l3-euryale-70b",
        "cognitivecomputations/dolphin-mixtral-8x22b",
        "qwen/qwen-2-72b-instruct",
        "mistralai/mistral-7b-instruct:free",
        "mistralai/mistral-7b-instruct",
        "mistralai/mistral-7b-instruct-v0.3",
        "nousresearch/hermes-2-pro-llama-3-8b",
        "microsoft/phi-3-mini-128k-instruct:free",
        "microsoft/phi-3-mini-128k-instruct",
        "microsoft/phi-3-medium-128k-instruct:free",
        "microsoft/phi-3-medium-128k-instruct",
        "neversleep/llama-3-lumimaid-70b",
        "google/gemini-flash-1.5",
        "openai/gpt-4o-2024-05-13",
        "meta-llama/llama-guard-2-8b",
        "openai/gpt-4o",
        "openai/gpt-4o:extended",
        "neversleep/llama-3-lumimaid-8b:extended",
        "neversleep/llama-3-lumimaid-8b",
        "sao10k/fimbulvetr-11b-v2",
        "meta-llama/llama-3-8b-instruct:free",
        "meta-llama/llama-3-8b-instruct",
        "meta-llama/llama-3-70b-instruct",
        "mistralai/mixtral-8x22b-instruct",
        "microsoft/wizardlm-2-8x22b",
        "microsoft/wizardlm-2-7b",
        "google/gemini-pro-1.5",
        "openai/gpt-4-turbo",
        "cohere/command-r-plus",
        "cohere/command-r-plus-04-2024",
        "sophosympatheia/midnight-rose-70b",
        "cohere/command",
        "cohere/command-r",
        "anthropic/claude-3-haiku:beta",
        "anthropic/claude-3-haiku",
        "anthropic/claude-3-opus:beta",
        "anthropic/claude-3-opus",
        "anthropic/claude-3-sonnet:beta",
        "anthropic/claude-3-sonnet",
        "cohere/command-r-03-2024",
        "mistralai/mistral-large",
        "google/gemma-7b-it",
        "openai/gpt-3.5-turbo-0613",
        "openai/gpt-4-turbo-preview",
        "nousresearch/nous-hermes-2-mixtral-8x7b-dpo",
        "mistralai/mistral-small",
        "mistralai/mistral-tiny",
        "mistralai/mistral-medium",
        "mistralai/mistral-7b-instruct-v0.2",
        "cognitivecomputations/dolphin-mixtral-8x7b",
        "google/gemini-pro-vision",
        "google/gemini-pro",
        "mistralai/mixtral-8x7b",
        "mistralai/mixtral-8x7b-instruct",
        "openchat/openchat-7b:free",
        "openchat/openchat-7b",
        "neversleep/noromaid-20b",
        "anthropic/claude-2:beta",
        "anthropic/claude-2",
        "anthropic/claude-2.1:beta",
        "anthropic/claude-2.1",
        "teknium/openhermes-2.5-mistral-7b",
        "undi95/toppy-m-7b:free",
        "undi95/toppy-m-7b",
        "alpindale/goliath-120b",
        "openrouter/auto",
        "openai/gpt-3.5-turbo-1106",
        "openai/gpt-4-1106-preview",
        "google/palm-2-chat-bison-32k",
        "google/palm-2-codechat-bison-32k",
        "jondurbin/airoboros-l2-70b",
        "xwin-lm/xwin-lm-70b",
        "openai/gpt-3.5-turbo-instruct",
        "mistralai/mistral-7b-instruct-v0.1",
        "pygmalionai/mythalion-13b",
        "openai/gpt-3.5-turbo-16k",
        "openai/gpt-4-32k",
        "openai/gpt-4-32k-0314",
        "nousresearch/nous-hermes-llama2-13b",
        "mancer/weaver",
        "huggingfaceh4/zephyr-7b-beta:free",
        "anthropic/claude-2.0:beta",
        "anthropic/claude-2.0",
        "undi95/remm-slerp-l2-13b",
        "google/palm-2-chat-bison",
        "google/palm-2-codechat-bison",
        "gryphe/mythomax-l2-13b:free",
        "gryphe/mythomax-l2-13b",
        "meta-llama/llama-2-13b-chat",
        "meta-llama/llama-2-70b-chat",
        "openai/gpt-3.5-turbo",
        "openai/gpt-3.5-turbo-0125",
        "openai/gpt-4",
        "openai/gpt-4-0314"
        ]
}


# Callback to update the model name dropdown based on the selected provider
def update_model_dropdown(llm_provider, api_key=None, base_url=None):
    """
    Update the model name dropdown with predefined models for the selected provider.
    """
    import gradio as gr
    # Use API keys from .env if not provided
    if not api_key:
        api_key = os.getenv(f"{llm_provider.upper()}_API_KEY", "")
    if not base_url:
        base_url = os.getenv(f"{llm_provider.upper()}_BASE_URL", "")

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
