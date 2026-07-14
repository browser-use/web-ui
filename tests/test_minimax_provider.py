import httpx
import pytest

from src.utils import config, llm_provider


EXPECTED_MODELS = ["MiniMax-M3", "MiniMax-M2.7"]


@pytest.mark.parametrize("provider", config.MINIMAX_PROVIDER_CONFIGS)
def test_minimax_models_are_registered(provider):
    assert config.model_names[provider] == EXPECTED_MODELS


@pytest.mark.parametrize(
    ("provider", "expected_adapter", "expected_base_url"),
    [
        ("minimax", "openai", "https://api.minimax.io/v1"),
        ("minimax_cn", "openai", "https://api.minimaxi.com/v1"),
        ("minimax_anthropic", "anthropic", "https://api.minimax.io/anthropic"),
        ("minimax_anthropic_cn", "anthropic", "https://api.minimaxi.com/anthropic"),
    ],
)
def test_minimax_provider_uses_configured_adapter_and_endpoint(
    monkeypatch, provider, expected_adapter, expected_base_url
):
    created = {}

    def fake_openai(**kwargs):
        created.update(adapter="openai", kwargs=kwargs)
        return object()

    def fake_anthropic(**kwargs):
        created.update(adapter="anthropic", kwargs=kwargs)
        return object()

    provider_config = config.MINIMAX_PROVIDER_CONFIGS[provider]
    monkeypatch.setattr(llm_provider, "ChatOpenAI", fake_openai)
    monkeypatch.setattr(llm_provider, "ChatAnthropic", fake_anthropic)
    monkeypatch.setenv("MINIMAX_API_KEY", "unit-test-key")
    monkeypatch.delenv(provider_config["endpoint_env"], raising=False)

    llm_provider.get_llm_model(provider=provider, model_name=EXPECTED_MODELS[0])

    assert created["adapter"] == expected_adapter
    assert created["kwargs"]["model"] == EXPECTED_MODELS[0]
    assert created["kwargs"]["base_url"] == expected_base_url
    assert created["kwargs"]["api_key"] == "unit-test-key"


def test_minimax_clients_append_expected_request_paths(monkeypatch):
    captured_urls = []

    def fake_send(self, request, *args, **kwargs):
        captured_urls.append(str(request.url))
        if request.url.path.endswith("/chat/completions"):
            payload = {
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "created": 0,
                "model": EXPECTED_MODELS[0],
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "ok"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 1,
                    "completion_tokens": 1,
                    "total_tokens": 2,
                },
            }
        else:
            payload = {
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "model": EXPECTED_MODELS[0],
                "content": [{"type": "text", "text": "ok"}],
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {"input_tokens": 1, "output_tokens": 1},
            }
        return httpx.Response(200, json=payload, request=request)

    monkeypatch.setattr(httpx.Client, "send", fake_send)
    expected_urls = {
        "minimax": "https://api.minimax.io/v1/chat/completions",
        "minimax_cn": "https://api.minimaxi.com/v1/chat/completions",
        "minimax_anthropic": "https://api.minimax.io/anthropic/v1/messages",
        "minimax_anthropic_cn": "https://api.minimaxi.com/anthropic/v1/messages",
    }

    for provider, expected_url in expected_urls.items():
        captured_urls.clear()
        model = llm_provider.get_llm_model(
            provider=provider,
            model_name=EXPECTED_MODELS[0],
            api_key="unit-test-key",
            temperature=0.0,
        )

        model.invoke("hello")

        assert captured_urls == [expected_url]
