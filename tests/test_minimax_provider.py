import asyncio
import json

import gradio as gr
import httpx
import pytest
from langchain_core.messages import HumanMessage

from src.utils import config, llm_provider
from src.webui.components import agent_settings_tab
from src.webui.components.browser_use_agent_tab import _initialize_llm as browser_llm
from src.webui.components.deep_research_agent_tab import _initialize_llm as research_llm
from src.webui.webui_manager import WebuiManager


EXPECTED_MODELS = ["MiniMax-M3.1-Flash", "MiniMax-M3"]
EXPLICIT_MODELS = EXPECTED_MODELS + ["MiniMax-M2.7", "custom-model"]
EXPECTED_URLS = {
    "minimax": "https://api.minimax.io/v1/chat/completions",
    "minimax_cn": "https://api.minimaxi.com/v1/chat/completions",
    "minimax_anthropic": "https://api.minimax.io/anthropic/v1/messages",
    "minimax_anthropic_cn": "https://api.minimaxi.com/anthropic/v1/messages",
}


@pytest.fixture
def captured_requests(monkeypatch):
    captured = []

    def respond(request):
        body = json.loads(request.content)
        captured.append((request, body))
        if request.url.path.endswith("/chat/completions"):
            payload = {
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "created": 0,
                "model": body["model"],
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": "ok"},
                    "finish_reason": "stop",
                }],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            }
        else:
            payload = {
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "model": body["model"],
                "content": [{"type": "text", "text": "ok"}],
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {"input_tokens": 1, "output_tokens": 1},
            }
        return httpx.Response(200, json=payload, request=request)

    def send(self, request, *args, **kwargs):
        return respond(request)

    async def async_send(self, request, *args, **kwargs):
        return respond(request)

    monkeypatch.setattr(httpx.Client, "send", send)
    monkeypatch.setattr(httpx.AsyncClient, "send", async_send)
    monkeypatch.setenv("MINIMAX_API_KEY", "unit-test-key")
    for settings in config.MINIMAX_PROVIDER_CONFIGS.values():
        monkeypatch.delenv(settings["endpoint_env"], raising=False)
    return captured


def assert_request(captured, provider, expected_model):
    assert len(captured) == 1
    request, body = captured[0]
    assert str(request.url) == EXPECTED_URLS[provider]
    assert body["model"] == expected_model
    assert body["messages"] == [{"role": "user", "content": "hello"}]
    # Leave reasoning to the model's API defaults; do not disable Flash thinking
    # or introduce unsupported effort/service-tier settings.
    for key in ("thinking", "reasoning_effort", "output_config", "service_tier", "reasoning_split"):
        assert key not in body
    if config.MINIMAX_PROVIDER_CONFIGS[provider]["protocol"] == "openai":
        assert request.headers["authorization"] == "Bearer unit-test-key"
    else:
        assert request.headers["x-api-key"] == "unit-test-key"


@pytest.mark.parametrize("provider", EXPECTED_URLS)
def test_minimax_models_and_factory_default(provider, captured_requests):
    assert config.model_names[provider] == EXPECTED_MODELS
    model = llm_provider.get_llm_model(provider=provider)
    assert model.invoke("hello").content == "ok"
    assert_request(captured_requests, provider, EXPECTED_MODELS[0])


@pytest.mark.parametrize("provider", EXPECTED_URLS)
@pytest.mark.parametrize("initialize", [browser_llm, research_llm])
@pytest.mark.parametrize("selection", [None] + EXPLICIT_MODELS)
def test_picker_to_async_request(provider, initialize, selection, captured_requests):
    dropdown = agent_settings_tab.update_model_dropdown(provider)
    assert dropdown.choices == [(name, name) for name in EXPECTED_MODELS]
    assert dropdown.allow_custom_value
    selected = dropdown.value if selection is None else dropdown.preprocess(selection)
    model = asyncio.run(initialize(provider, selected, 0.6, "", "", 16000))
    assert model is not None
    assert asyncio.run(model.ainvoke("hello")).content == "ok"
    assert_request(captured_requests, provider, selected)


@pytest.mark.parametrize("provider", EXPECTED_URLS)
@pytest.mark.parametrize("explicit", [False, True])
def test_endpoint_and_key_overrides(provider, explicit, monkeypatch, captured_requests):
    settings = config.MINIMAX_PROVIDER_CONFIGS[provider]
    monkeypatch.setenv(settings["endpoint_env"], "https://env.example/api")
    kwargs = {"base_url": "https://custom.example/api", "api_key": "custom-test-key"} if explicit else {}
    model = llm_provider.get_llm_model(provider=provider, **kwargs)
    model.invoke("hello")
    request, body = captured_requests[0]
    root = "https://custom.example/api" if explicit else "https://env.example/api"
    suffix = "/chat/completions" if settings["protocol"] == "openai" else "/v1/messages"
    assert str(request.url) == root + suffix
    assert body["model"] == EXPECTED_MODELS[0]
    key = "custom-test-key" if explicit else "unit-test-key"
    header = "authorization" if settings["protocol"] == "openai" else "x-api-key"
    assert request.headers[header] == ("Bearer " + key if header == "authorization" else key)


@pytest.mark.parametrize("provider", EXPECTED_URLS)
@pytest.mark.parametrize("saved_model", ["MiniMax-M2.7", "custom-model"])
@pytest.mark.parametrize("same_provider", [False, True])
def test_saved_agent_and_planner_models_survive_loading(
    provider, saved_model, same_provider, monkeypatch, tmp_path, captured_requests
):
    initial_provider = provider if same_provider else "openai"
    monkeypatch.setenv("DEFAULT_LLM", initial_provider)
    manager = WebuiManager(settings_save_dir=str(tmp_path))
    with gr.Blocks() as blocks:
        agent_settings_tab.create_agent_settings_tab(manager)
        manager.add_components("load_save_config", {"config_status": gr.Textbox()})
    for prefix in ("", "planner_"):
        provider_component = manager.get_component_by_id(f"agent_settings.{prefix}llm_provider")
        model_component = manager.get_component_by_id(f"agent_settings.{prefix}llm_model_name")
        reset_events = [
            dependency for dependency in blocks.config["dependencies"]
            if model_component._id in dependency["outputs"]
        ]
        assert len(reset_events) == 1
        assert reset_events[0]["targets"] == [(provider_component._id, "input")]
        if not prefix:
            assert model_component.value == config.model_names[initial_provider][0]
        path = manager.save_config({provider_component: provider, model_component: saved_model})
        updates = list(manager.load_config(path))[-1]
        restored = updates[model_component].value
        assert restored == saved_model
        assert updates[model_component].choices == [(name, name) for name in EXPECTED_MODELS]
        assert updates[model_component].allow_custom_value
        model = asyncio.run(browser_llm(provider, restored, 0.6, "", "", 16000))
        captured_requests.clear()
        asyncio.run(model.ainvoke("hello"))
        assert_request(captured_requests, provider, saved_model)


@pytest.mark.parametrize("provider", ["openai"] + list(EXPECTED_URLS))
def test_existing_multimodal_payload_is_preserved(provider, captured_requests):
    content = [
        {"type": "text", "text": "describe this"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,dGVzdA=="}},
    ]
    model = llm_provider.get_llm_model(provider=provider, api_key="unit-test-key")
    model.invoke([HumanMessage(content=content)])
    body = captured_requests[0][1]
    assert body["model"] == ("gpt-4o" if provider == "openai" else EXPECTED_MODELS[0])
    if config.MINIMAX_PROVIDER_CONFIGS.get(provider, {}).get("protocol") == "anthropic":
        assert body["messages"][0]["content"] == [
            content[0],
            {"type": "image", "source": {
                "type": "base64", "media_type": "image/png", "data": "dGVzdA==",
            }},
        ]
    else:
        assert body["messages"][0]["content"] == content
