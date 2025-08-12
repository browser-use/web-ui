"""
Integration tests for custom skills with the browser-use agent.
"""
import asyncio
import json
import logging
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from browser_use.agent.views import AgentHistoryList
from browser_use.browser.browser import Browser
from browser_use.browser.context import BrowserContext, BrowserContextConfig

# Add the project root to the Python path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.agent.browser_use.browser_use_agent import BrowserUseAgent
from src.browser.custom_browser import CustomBrowser
from src.browser.skill_registry import SkillRegistry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.fixture
def mock_browser():
    """Create a mock browser instance."""
    browser = MagicMock(spec=Browser)
    browser.new_context.return_value = AsyncMock(spec=BrowserContext)
    return browser

@pytest.fixture
def mock_context():
    """Create a mock browser context."""
    context = AsyncMock(spec=BrowserContext)
    context.page = AsyncMock()
    context.page.locator.return_value = AsyncMock()
    context.page.wait_for_selector = AsyncMock()
    context.page.wait_for_url = AsyncMock()
    context.page.goto = AsyncMock()
    return context

@pytest.fixture
def mock_llm():
    """Create a mock LLM instance."""
    return AsyncMock()

@pytest.fixture
def agent_config():
    """Default agent configuration."""
    return {
        "task": "Test task",
        "use_vision": False,
        "max_actions_per_step": 10,
        "max_input_tokens": 128000,
    }

@pytest.mark.asyncio
async def test_skill_registration(mock_browser, mock_context, mock_llm, agent_config):
    """Test that custom skills are properly registered with the agent."""
    # Create a test agent
    agent = BrowserUseAgent(
        **agent_config,
        llm=mock_llm,
        browser=mock_browser,
        browser_context=mock_context,
    )
    
    # Verify the agent has the register_skill method
    assert hasattr(agent, 'register_skill'), "Agent must have register_skill method"
    
    # Register our custom skills
    SkillRegistry.register_skills(agent)
    
    # Verify the skills were registered
    from src.custom_skills import CUSTOM_SKILLS
    for skill_name in CUSTOM_SKILLS.keys():
        assert hasattr(agent, f'skill_{skill_name}'), f"Skill {skill_name} not registered"

@pytest.mark.asyncio
async def test_click_css_skill_execution(mock_browser, mock_context, mock_llm, agent_config):
    """Test execution of the clickCss skill."""
    # Create a test agent
    agent = BrowserUseAgent(
        **agent_config,
        llm=mock_llm,
        browser=mock_browser,
        browser_context=mock_context,
    )
    
    # Register our custom skills
    SkillRegistry.register_skills(agent)
    
    # Execute the clickCss skill
    selector = "button#test"
    x, y = 10, 10
    
    # Mock the page locator and element
    mock_element = AsyncMock()
    mock_context.page.locator.return_value = mock_element
    
    # Call the skill
    result = await agent.skill_clickCss(selector, x, y)
    
    # Verify the interactions
    mock_context.page.locator.assert_called_once_with(selector)
    mock_element.wait_for.assert_called_once_with(state='visible', timeout=5000)
    mock_context.page.mouse.move.assert_called_once_with(20, 20)
    mock_element.hover.assert_awaited_once()
    mock_element.click.assert_awaited_once_with(position={'x': x, 'y': y}, force=True)
    assert result["status"] == "success"

@pytest.mark.asyncio
async def test_goto_skill_execution(mock_browser, mock_context, mock_llm, agent_config):
    """Test execution of the goto skill."""
    # Create a test agent
    agent = BrowserUseAgent(
        **agent_config,
        llm=mock_llm,
        browser=mock_browser,
        browser_context=mock_context,
    )
    
    # Register our custom skills
    SkillRegistry.register_skills(agent)
    
    # Execute the goto skill
    url = "https://example.com"
    result = await agent.skill_goto(url)
    
    # Verify the interactions
    mock_context.page.goto.assert_awaited_once_with(url, timeout=30000)
    assert result["status"] == "success"

@pytest.mark.asyncio
async def test_wait_for_skill_execution(mock_browser, mock_context, mock_llm, agent_config):
    """Test execution of the waitFor skill."""
    # Create a test agent
    agent = BrowserUseAgent(
        **agent_config,
        llm=mock_llm,
        browser=mock_browser,
        browser_context=mock_context,
    )
    
    # Register our custom skills
    SkillRegistry.register_skills(agent)
    
    # Test waiting for an element to be attached
    selector = ".loading"
    state = "attached"
    timeout = 5000
    
    # Execute the waitFor skill
    result = await agent.skill_waitFor(selector, state, timeout)
    
    # Verify the interactions
    mock_context.page.wait_for_selector.assert_awaited_once_with(
        selector, state=state, timeout=timeout/1000
    )
    assert result["status"] == "success"

@pytest.mark.asyncio
async def test_wait_for_url_skill_execution(mock_browser, mock_context, mock_llm, agent_config):
    """Test execution of the waitForUrl skill."""
    # Create a test agent
    agent = BrowserUseAgent(
        **agent_config,
        llm=mock_llm,
        browser=mock_browser,
        browser_context=mock_context,
    )
    
    # Register our custom skills
    SkillRegistry.register_skills(agent)
    
    # Test waiting for URL
    url_fragment = "/test"
    timeout = 3000
    
    # Execute the waitForUrl skill
    result = await agent.skill_waitForUrl(url_fragment, timeout)
    
    # Verify the interactions
    mock_context.page.wait_for_url.assert_awaited_once_with(
        f"*{url_fragment}*",
        timeout=timeout/1000,
        wait_until="networkidle"
    )
    assert result["status"] == "success"

# This allows running the tests directly with: python -m pytest tests/test_skill_integration.py -v
if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main(["-v", __file__]))
