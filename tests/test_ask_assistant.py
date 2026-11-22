import asyncio
from types import SimpleNamespace

from src.webui.components.browser_use_agent_tab import (
    _ask_assistant_callback,
)


def test_ask_assistant_appends_help_request(monkeypatch):
    async def run_test():
        manager = SimpleNamespace(bu_chat_history=[])

        async def mock_wait_for(awaitable, timeout):
            awaitable.close()
            manager.bu_user_help_response = "Please proceed."
            return True

        monkeypatch.setattr(asyncio, "wait_for", mock_wait_for)

        result = await _ask_assistant_callback(
            manager,
            "Please help me complete this action.",
            None,
        )

        assert len(manager.bu_chat_history) == 2
        assert manager.bu_chat_history[0]["role"] == "assistant"
        assert "**Need Help:**" in manager.bu_chat_history[0]["content"]
        assert manager.bu_chat_history[1] == {
            "role": "user",
            "content": "Please proceed.",
        }
        assert result == {"response": "Please proceed."}

    asyncio.run(run_test())


def test_ask_assistant_returns_error_when_history_missing():
    async def run_test():
        manager = SimpleNamespace()

        result = await _ask_assistant_callback(
            manager,
            "Please help me.",
            None,
        )

        assert result == {
            "response": "Internal Error: Cannot display help request."
        }

    asyncio.run(run_test())
