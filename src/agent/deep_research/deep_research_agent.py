import asyncio
import json
import logging
import os
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from browser_use.browser.profile import BrowserProfile
from browser_use.llm import BaseChatModel, UserMessage, SystemMessage, AssistantMessage
from pydantic import BaseModel, Field

# Using browser_use.Agent directly
from browser_use import Controller

logger = logging.getLogger(__name__)

# Constants
REPORT_FILENAME = "report.md"
PLAN_FILENAME = "research_plan.md"
SEARCH_INFO_FILENAME = "search_info.json"

# Global state management
_AGENT_STOP_FLAGS = {}
_BROWSER_AGENT_INSTANCES = {}

# Simple file operations to replace langchain tools
def read_file_content(file_path: str) -> str:
    """Read content from a file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

def write_file_content(file_path: str, content: str) -> str:
    """Write content to a file"""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote to {file_path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"

def list_directory_contents(directory_path: str) -> str:
    """List contents of a directory"""
    try:
        contents = os.listdir(directory_path)
        return "\n".join(contents)
    except Exception as e:
        return f"Error listing directory: {str(e)}"


async def run_single_browser_task(
        task_query: str,
        task_id: str,
        llm: BaseChatModel,
        browser_config: Dict[str, Any],
        stop_event: threading.Event,
        use_vision: bool = False,
) -> Dict[str, Any]:
    """
    Simplified browser task runner using browser-use Agent
    """
    try:
        logger.info(f"Running browser task: {task_query}")
        
        # Create browser profile  
        browser_profile = BrowserProfile(
            headless=browser_config.get("headless", True),
            window_width=browser_config.get("window_width", 1280),
            window_height=browser_config.get("window_height", 1100),
            browser_binary_path=browser_config.get("browser_binary_path"),
            user_data_dir=browser_config.get("user_data_dir"),
        )
        
        # Use browser-use Agent directly with browser profile
        controller = Controller()
        
        # Create browser agent using browser-use Agent class
        from browser_use import Agent
        browser_agent = Agent(
            task=task_query,
            llm=llm,
            browser_profile=browser_profile,
            controller=controller,
            use_vision=use_vision,
        )
        
        # Store instance for potential stop
        _BROWSER_AGENT_INSTANCES[task_id] = browser_agent
        
        if stop_event.is_set():
            return {"query": task_query, "result": None, "status": "cancelled"}
        
        # Run the browser agent
        result = await browser_agent.run()
        
        return {
            "query": task_query,
            "result": str(result),
            "status": "completed"
        }
        
    except Exception as e:
        logger.error(f"Browser task failed: {e}", exc_info=True)
        return {
            "query": task_query,
            "result": f"Error: {str(e)}",
            "status": "failed"
        }
    finally:
        # Cleanup
        if task_id in _BROWSER_AGENT_INSTANCES:
            del _BROWSER_AGENT_INSTANCES[task_id]


class DeepResearchAgent:
    def __init__(
            self,
            llm: BaseChatModel,
            browser_config: Dict[str, Any],
    ):
        """
        Simplified Deep Research Agent without langchain dependencies.

        Args:
            llm: Browser-use compatible language model instance.
            browser_config: Configuration dictionary for the BrowserUseAgent tool.
                            Example: {"headless": True, "window_width": 1280, ...}
        """
        self.llm = llm
        self.browser_config = browser_config
        self.stopped = False
        self.current_task_id: Optional[str] = None
        self.stop_event: Optional[threading.Event] = None
        self.runner: Optional[asyncio.Task] = None

    async def research(self, query: str, output_dir: str = "./research_output") -> str:
        """
        Simplified research method that conducts research and writes a report.
        
        Args:
            query: The research question or topic
            output_dir: Directory to save research output
            
        Returns:
            Path to the generated report
        """
        try:
            # Create output directory
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate task ID
            task_id = f"research_{uuid.uuid4().hex[:8]}"
            self.current_task_id = task_id
            
            logger.info(f"Starting research on: {query}")
            
            # Use browser agent to gather information
            browser_results = await self._conduct_browser_research(query, task_id)
            
            # Generate report using LLM
            report_content = await self._generate_report(query, browser_results)
            
            # Save report
            report_path = os.path.join(output_dir, REPORT_FILENAME)
            write_file_content(report_path, report_content)
            
            logger.info(f"Research complete. Report saved to: {report_path}")
            return report_path
            
        except Exception as e:
            logger.error(f"Research failed: {e}", exc_info=True)
            raise
        finally:
            self.current_task_id = None

    async def _conduct_browser_research(self, query: str, task_id: str) -> str:
        """Conduct research using browser agent"""
        try:
            self.stop_event = stop_event = threading.Event()
            result = await run_single_browser_task(
                task_query=f"Research and gather comprehensive information about: {query}",
                task_id=task_id,
                llm=self.llm,
                browser_config=self.browser_config,
                stop_event=stop_event,
                use_vision=False
            )
            return result.get("result", "No results found")
        except Exception as e:
            logger.error(f"Browser research failed: {e}")
            return f"Error conducting research: {str(e)}"

    async def _generate_report(self, query: str, research_data: str) -> str:
        """Generate a comprehensive research report"""
        try:
            prompt = f"""
You are a research analyst tasked with creating a comprehensive report.

Research Question: {query}

Research Data:
{research_data}

Please create a well-structured, comprehensive research report that includes:
1. Executive Summary
2. Key Findings
3. Detailed Analysis
4. Conclusions and Recommendations
5. Sources (if any were found)

Format the report in clear markdown with appropriate headings and structure.
"""
            
            messages = [
                SystemMessage(content="You are an expert research analyst who creates comprehensive, well-structured reports."),
                UserMessage(content=prompt)
            ]
            
            response = await self.llm.ainvoke(messages)
            # Handle different response types from browser-use LLMs
            if hasattr(response, 'content'):
                return response.content
            elif hasattr(response, 'text'):
                return response.text
            else:
                return str(response)
            
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return f"# Research Report\n\n## Error\nFailed to generate report: {str(e)}\n\n## Raw Data\n{research_data}"

    def stop(self):
        """Stop the research process"""
        self.stopped = True
        if self.current_task_id:
            _AGENT_STOP_FLAGS[self.current_task_id] = True
        if self.stop_event:
            self.stop_event.set()
