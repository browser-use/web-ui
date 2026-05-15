import os
import logging
from typing import Any, Optional

# Browser-use LLM imports
from browser_use.llm.openai.chat import ChatOpenAI
from browser_use.llm.anthropic.chat import ChatAnthropic
from browser_use.llm.google.chat import ChatGoogle
from browser_use.llm.groq.chat import ChatGroq
from browser_use.llm.ollama.chat import ChatOllama
from browser_use.llm.azure.chat import ChatAzureOpenAI
from browser_use.llm.deepseek.chat import ChatDeepSeek
from browser_use.llm import BaseChatModel, UserMessage, SystemMessage, AssistantMessage

from src.utils import config

logger = logging.getLogger(__name__)


# Custom DeepSeek reasoning model implementations are removed
# as they require specific reasoning content handling not available in browser-use


def get_llm_model(provider: str, **kwargs) -> BaseChatModel:
    """
    Get LLM model using browser-use LLM implementations
    :param provider: LLM provider name
    :param kwargs: Additional parameters
    :return: BaseChatModel instance
    """
    # Handle API key requirement for most providers
    if provider not in ["ollama"]:
        env_var = f"{provider.upper()}_API_KEY"
        api_key = kwargs.get("api_key", "") or os.getenv(env_var, "")
        if not api_key:
            provider_display = config.PROVIDER_DISPLAY_NAMES.get(provider, provider.upper())
            error_msg = f"💥 {provider_display} API key not found! 🔑 Please set the `{env_var}` environment variable or provide it in the UI."
            raise ValueError(error_msg)
        kwargs["api_key"] = api_key

    if provider == "anthropic":
        base_url = kwargs.get("base_url") or os.getenv("ANTHROPIC_ENDPOINT", "https://api.anthropic.com")
        return ChatAnthropic(
            model=kwargs.get("model_name", "claude-3-5-sonnet-20241022"),
            temperature=kwargs.get("temperature", 0.0),
            base_url=base_url,
            api_key=api_key,
        )
    
    elif provider == "openai":
        base_url = kwargs.get("base_url") or os.getenv("OPENAI_ENDPOINT", "https://api.openai.com/v1")
        return ChatOpenAI(
            model=kwargs.get("model_name", "gpt-4o"),
            temperature=kwargs.get("temperature", 0.2),
            base_url=base_url,
            api_key=api_key,
        )
    
    elif provider == "google":
        return ChatGoogle(
            model=kwargs.get("model_name", "gemini-2.0-flash-exp"),
            temperature=kwargs.get("temperature", 0.0),
            api_key=api_key,
        )
    
    elif provider == "groq":
        base_url = kwargs.get("base_url") or os.getenv("GROQ_ENDPOINT", "https://api.groq.com/openai/v1")
        return ChatGroq(
            model=kwargs.get("model_name", "llama-3.1-8b-instant"),
            temperature=kwargs.get("temperature", 0.0),
            base_url=base_url,
            api_key=api_key,
        )
    
    elif provider == "ollama":
        host = kwargs.get("base_url") or os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434")
        return ChatOllama(
            model=kwargs.get("model_name", "qwen2.5:7b"),
            host=host,
        )
    
    elif provider == "azure_openai":
        base_url = kwargs.get("base_url") or os.getenv("AZURE_OPENAI_ENDPOINT", "")
        if not base_url:
            raise ValueError("Azure OpenAI endpoint is required")
        return ChatAzureOpenAI(
            model=kwargs.get("model_name", "gpt-4o"),
            temperature=kwargs.get("temperature", 0.2),
            base_url=base_url,
            api_key=api_key,
        )
    
    elif provider == "deepseek":
        base_url = kwargs.get("base_url") or os.getenv("DEEPSEEK_ENDPOINT", "https://api.deepseek.com/v1")
        return ChatDeepSeek(
            model=kwargs.get("model_name", "deepseek-chat"),
            temperature=kwargs.get("temperature", 0.0),
            base_url=base_url,
            api_key=api_key,
        )
    
    # For providers not directly supported by browser-use, use OpenAI-compatible API
    elif provider in ["grok", "alibaba", "moonshot", "unbound", "siliconflow", "modelscope", "mistral", "ibm"]:
        base_url_map = {
            "grok": os.getenv("GROK_ENDPOINT", "https://api.x.ai/v1"),
            "alibaba": os.getenv("ALIBABA_ENDPOINT", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
            "moonshot": os.getenv("MOONSHOT_ENDPOINT"),
            "unbound": os.getenv("UNBOUND_ENDPOINT", "https://api.getunbound.ai"),
            "siliconflow": os.getenv("SILICONFLOW_ENDPOINT", ""),
            "modelscope": os.getenv("MODELSCOPE_ENDPOINT", ""),
            "mistral": os.getenv("MISTRAL_ENDPOINT", "https://api.mistral.ai/v1"),
            "ibm": os.getenv("IBM_ENDPOINT", "https://us-south.ml.cloud.ibm.com")
        }
        
        model_defaults = {
            "grok": "grok-3",
            "alibaba": "qwen-plus",
            "moonshot": "moonshot-v1-32k-vision-preview",
            "unbound": "gpt-4o-mini",
            "siliconflow": "Qwen/QwQ-32B",
            "modelscope": "Qwen/QwQ-32B",
            "mistral": "pixtral-large-latest",
            "ibm": "ibm/granite-vision-3.1-2b-preview"
        }
        
        base_url = kwargs.get("base_url") or base_url_map[provider]
        if not base_url:
            raise ValueError(f"{provider} endpoint is required")
        
        # Special handling for IBM which may require project_id in headers
        extra_headers = {}
        if provider == "ibm":
            project_id = kwargs.get("project_id") or os.getenv("IBM_PROJECT_ID")
            if project_id:
                extra_headers["X-Project-ID"] = project_id
            
        return ChatOpenAI(
            model=kwargs.get("model_name", model_defaults[provider]),
            temperature=kwargs.get("temperature", 0.2),
            base_url=base_url,
            api_key=api_key,
            extra_headers=extra_headers if extra_headers else None,
        )
    
    else:
        raise ValueError(f"Unsupported provider: {provider}. Supported providers: anthropic, openai, google, groq, ollama, azure_openai, deepseek, grok, alibaba, moonshot, unbound, siliconflow, modelscope, mistral, ibm")
