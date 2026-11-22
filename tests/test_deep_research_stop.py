import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, AsyncMock

from src.webui.components import deep_research_agent_tab as dr_tab
from src.webui.webui_manager import WebuiManager


def test_deep_research_agent_task_id_initialized():
    manager = WebuiManager()
    manager.init_deep_research_agent()

    assert hasattr(manager, "dr_agent_task_id")
    assert manager.dr_agent_task_id is None
    assert manager.dr_stop_requested is False
    assert manager.dr_initializing is False


def test_stop_during_llm_initialization_prevents_agent_start(monkeypatch):
    async def run_test():
        manager = SimpleNamespace(
            dr_agent=None,
            dr_current_task=None,
            dr_agent_task_id=None,
            dr_save_dir=None,
            dr_stop_requested=False,
            dr_initializing=False,
            id_to_component={},
            get_component_by_id=lambda component_id: component_id,
        )

        component_values = {
            "deep_research_agent.research_task": "Test research topic",
            "deep_research_agent.resume_task_id": "",
            "deep_research_agent.parallel_num": 1,
            "deep_research_agent.max_query": "./tmp/deep_research",
            "deep_research_agent.mcp_server_config": None,
            "agent_settings.llm_provider": "test",
            "agent_settings.llm_model_name": "test-model",
            "agent_settings.llm_temperature": 0.5,
        }

        manager.id_to_component = {
            key: key for key in component_values
            if key.startswith("agent_settings.")
        }

        initialization_started = asyncio.Event()
        allow_initialization = asyncio.Event()

        async def fake_initialize_llm(*args, **kwargs):
            initialization_started.set()
            await allow_initialization.wait()
            return object()

        monkeypatch.setattr(
            dr_tab, "_initialize_llm", fake_initialize_llm
        )

        agent_factory = MagicMock()
        monkeypatch.setattr(
            dr_tab, "DeepResearchAgent", agent_factory
        )

        generator = dr_tab.run_deep_research(
            manager, component_values
        )

        # Start the research and receive the initial UI update.
        await generator.__anext__()

        # Continue until LLM initialization is paused.
        initialization_task = asyncio.create_task(
            generator.__anext__()
        )
        await initialization_started.wait()

        # Simulate clicking Stop during initialization.
        await dr_tab.stop_deep_research(manager)

        assert manager.dr_stop_requested is True

        # Allow LLM initialization to finish.
        allow_initialization.set()

        cancelled_update = await initialization_task

        display_update = cancelled_update.get(
            "deep_research_agent.markdown_display", {}
        )

        assert "Research Cancelled" in display_update.get("value", "")
        assert manager.dr_agent is None
        agent_factory.assert_not_called()

        # Consume the generator's final cleanup update.
        async for _ in generator:
            pass

    asyncio.run(run_test())



def test_idle_stop_keeps_run_button_enabled():
    manager = SimpleNamespace(
        dr_agent=None,
        dr_current_task=None,
        dr_agent_task_id=None,
        dr_save_dir=None,
        dr_stop_requested=False,
        dr_initializing=False,
        get_component_by_id=lambda component_id: component_id,
    )

    result = asyncio.run(dr_tab.stop_deep_research(manager))

    assert result["deep_research_agent.start_button"]["interactive"] is True
    assert result["deep_research_agent.stop_button"]["interactive"] is False
    assert manager.dr_stop_requested is False

def test_stop_during_agent_startup_defers_stop_signal():
    async def run_test():
        agent_stop = AsyncMock()

        agent = SimpleNamespace(
            current_task_id=None,
            stop_event=None,
            stop=agent_stop,
        )

        task = asyncio.create_task(asyncio.sleep(10))

        manager = SimpleNamespace(
            dr_agent=agent,
            dr_current_task=task,
            dr_agent_task_id=None,
            dr_save_dir="./tmp/deep_research",
            dr_stop_requested=False,
            dr_initializing=True,
            get_component_by_id=lambda component_id: component_id,
        )

        try:
            result = await dr_tab.stop_deep_research(manager)

            assert manager.dr_stop_requested is True
            agent_stop.assert_not_awaited()

            assert result[
                "deep_research_agent.stop_button"
                ]["interactive"] is False

        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    asyncio.run(run_test())
