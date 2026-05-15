"""
Simple Gradio endpoint for browser-use agent.
Uses Anthropic claude-sonnet-4-5 with default settings.
Only accepts user input - everything else is default.
"""
from dotenv import load_dotenv
load_dotenv()

import asyncio
import os
import logging
import gradio as gr
from browser_use import Agent, Controller
from browser_use.browser import BrowserSession
from browser_use.browser.profile import BrowserProfile
from browser_use.llm.anthropic.chat import ChatAnthropic

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_MODEL = "claude-sonnet-4-5-20250929"
DEFAULT_TEMPERATURE = 0.6
DEFAULT_MAX_STEPS = 100
DEFAULT_MAX_ACTIONS_PER_STEP = 10


async def run_agent(task: str) -> str:
    """Run the browser agent with the given task."""
    if not task.strip():
        return "Please enter a task."

    # Get API key from environment
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return "Error: ANTHROPIC_API_KEY not found in environment variables."

    # Initialize LLM
    llm = ChatAnthropic(
        model=DEFAULT_MODEL,
        api_key=api_key,
        temperature=DEFAULT_TEMPERATURE,
    )

    # Initialize browser
    browser_profile = BrowserProfile(
        headless=True,
        viewport={'width': 1280, 'height': 1100},
        chrome_binary_path="/usr/bin/google-chrome"
    )

    browser = BrowserSession(browser_profile=browser_profile, is_local=True)
    controller = Controller()

    # Create agent
    agent = Agent(
        task=task,
        llm=llm,
        browser_session=browser,
        controller=controller,
        use_vision=True,
        max_actions_per_step=DEFAULT_MAX_ACTIONS_PER_STEP,
    )

    try:
        # Run agent
        logger.info(f"Starting agent with task: {task}")
        history = await agent.run(max_steps=DEFAULT_MAX_STEPS)

        # Get result
        result = history.final_result() if history else "No result"
        steps = len(history.history) if history and history.history else 0

        return f"Task completed in {steps} steps.\n\nResult:\n{result}"
    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)
        return f"Error: {str(e)}"
    finally:
        await browser.stop()


def run_agent_sync(task: str) -> str:
    """Synchronous wrapper for the async agent."""
    return asyncio.run(run_agent(task))


# Create Gradio interface
demo = gr.Interface(
    fn=run_agent_sync,
    inputs=gr.Textbox(
        label="Task",
        placeholder="Enter your task for the browser agent...",
        lines=3,
    ),
    outputs=gr.Textbox(label="Result", lines=10),
    title="Browser Agent",
    description=f"Simple browser agent using Anthropic {DEFAULT_MODEL}. Enter a task and the agent will execute it.",
    allow_flagging="never",
)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Simple Browser Agent Endpoint")
    parser.add_argument("--ip", type=str, default="127.0.0.1", help="IP address to bind to")
    parser.add_argument("--port", type=int, default=7789, help="Port to listen on")
    args = parser.parse_args()

    demo.launch(server_name=args.ip, server_port=args.port)
