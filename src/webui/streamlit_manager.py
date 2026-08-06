import streamlit as st
import json
import os
import asyncio
import time
from datetime import datetime
from typing import Optional, Dict, List
import uuid

from browser_use.browser.browser import Browser
from browser_use.browser.context import BrowserContext
from browser_use.agent.service import Agent
from src.browser.custom_browser import CustomBrowser
from src.browser.custom_context import CustomBrowserContext
from src.controller.custom_controller import CustomController
from src.agent.deep_research.deep_research_agent import DeepResearchAgent


class StreamlitManager:
    """
    Streamlit-specific manager that handles session state and agent management
    Adapted from WebuiManager to work with Streamlit's session state system
    """
    
    def __init__(self, settings_save_dir: str = "./tmp/webui_settings"):
        self.settings_save_dir = settings_save_dir
        os.makedirs(self.settings_save_dir, exist_ok=True)
        
        # Initialize session state for browser use agent
        self._init_browser_use_agent_state()
        
        # Initialize session state for deep research agent
        self._init_deep_research_agent_state()
        
        # Initialize session state for general settings
        self._init_general_state()

    def _init_browser_use_agent_state(self):
        """Initialize browser use agent session state"""
        if 'bu_agent' not in st.session_state:
            st.session_state.bu_agent = None
        if 'bu_browser' not in st.session_state:
            st.session_state.bu_browser = None
        if 'bu_browser_context' not in st.session_state:
            st.session_state.bu_browser_context = None
        if 'bu_controller' not in st.session_state:
            st.session_state.bu_controller = None
        if 'bu_chat_history' not in st.session_state:
            st.session_state.bu_chat_history = []
        if 'bu_response_event' not in st.session_state:
            st.session_state.bu_response_event = None
        if 'bu_user_help_response' not in st.session_state:
            st.session_state.bu_user_help_response = None
        if 'bu_current_task' not in st.session_state:
            st.session_state.bu_current_task = None
        if 'bu_agent_task_id' not in st.session_state:
            st.session_state.bu_agent_task_id = None

    def _init_deep_research_agent_state(self):
        """Initialize deep research agent session state"""
        if 'dr_agent' not in st.session_state:
            st.session_state.dr_agent = None
        if 'dr_browser' not in st.session_state:
            st.session_state.dr_browser = None
        if 'dr_browser_context' not in st.session_state:
            st.session_state.dr_browser_context = None
        if 'dr_controller' not in st.session_state:
            st.session_state.dr_controller = None
        if 'dr_chat_history' not in st.session_state:
            st.session_state.dr_chat_history = []
        if 'dr_response_event' not in st.session_state:
            st.session_state.dr_response_event = None
        if 'dr_user_help_response' not in st.session_state:
            st.session_state.dr_user_help_response = None
        if 'dr_current_task' not in st.session_state:
            st.session_state.dr_current_task = None
        if 'dr_agent_task_id' not in st.session_state:
            st.session_state.dr_agent_task_id = None

    def _init_general_state(self):
        """Initialize general application state"""
        if 'profile_data' not in st.session_state:
            st.session_state.profile_data = self.load_settings("profile.json")
        if 'browser_config' not in st.session_state:
            st.session_state.browser_config = {}
        if 'application_status' not in st.session_state:
            st.session_state.application_status = "idle"
        if 'job_search_url' not in st.session_state:
            st.session_state.job_search_url = ""
        if 'application_logs' not in st.session_state:
            st.session_state.application_logs = []

    # Browser Use Agent Properties
    @property
    def bu_agent(self) -> Optional[Agent]:
        return st.session_state.bu_agent
    
    @bu_agent.setter
    def bu_agent(self, value: Optional[Agent]):
        st.session_state.bu_agent = value

    @property
    def bu_browser(self) -> Optional[CustomBrowser]:
        return st.session_state.bu_browser
    
    @bu_browser.setter
    def bu_browser(self, value: Optional[CustomBrowser]):
        st.session_state.bu_browser = value

    @property
    def bu_browser_context(self) -> Optional[CustomBrowserContext]:
        return st.session_state.bu_browser_context
    
    @bu_browser_context.setter
    def bu_browser_context(self, value: Optional[CustomBrowserContext]):
        st.session_state.bu_browser_context = value

    @property
    def bu_controller(self) -> Optional[CustomController]:
        return st.session_state.bu_controller
    
    @bu_controller.setter
    def bu_controller(self, value: Optional[CustomController]):
        st.session_state.bu_controller = value

    @property
    def bu_chat_history(self) -> List[Dict[str, Optional[str]]]:
        return st.session_state.bu_chat_history
    
    @bu_chat_history.setter
    def bu_chat_history(self, value: List[Dict[str, Optional[str]]]):
        st.session_state.bu_chat_history = value

    # Deep Research Agent Properties
    @property
    def dr_agent(self) -> Optional[DeepResearchAgent]:
        return st.session_state.dr_agent
    
    @dr_agent.setter
    def dr_agent(self, value: Optional[DeepResearchAgent]):
        st.session_state.dr_agent = value

    # General Properties
    @property
    def profile_data(self) -> Dict:
        return st.session_state.profile_data
    
    @profile_data.setter
    def profile_data(self, value: Dict):
        st.session_state.profile_data = value

    @property
    def browser_config(self) -> Dict:
        return st.session_state.browser_config
    
    @browser_config.setter
    def browser_config(self, value: Dict):
        st.session_state.browser_config = value

    def save_settings(self, filename: str, data: Dict):
        """Save settings to file"""
        filepath = os.path.join(self.settings_save_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    def load_settings(self, filename: str) -> Dict:
        """Load settings from file"""
        filepath = os.path.join(self.settings_save_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
        return {}

    def add_chat_message(self, role: str, content: str, agent_type: str = "browser_use"):
        """Add a message to the chat history"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        if agent_type == "browser_use":
            self.bu_chat_history.append(message)
        elif agent_type == "deep_research":
            st.session_state.dr_chat_history.append(message)

    def clear_chat_history(self, agent_type: str = "browser_use"):
        """Clear chat history for specified agent"""
        if agent_type == "browser_use":
            self.bu_chat_history = []
        elif agent_type == "deep_research":
            st.session_state.dr_chat_history = []

    def cleanup_agents(self):
        """Cleanup all agents and browsers"""
        # Cleanup browser use agent
        if self.bu_browser:
            try:
                asyncio.create_task(self.bu_browser.close())
            except:
                pass
        
        # Reset all agent states
        self.bu_agent = None
        self.bu_browser = None
        self.bu_browser_context = None
        self.bu_controller = None
        self.dr_agent = None
        
        st.session_state.bu_current_task = None
        st.session_state.dr_current_task = None 