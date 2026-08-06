import pdb
import json
import os
from datetime import datetime
from pathlib import Path

import pyperclip
from typing import Optional, Type, Callable, Dict, Any, Union, Awaitable, TypeVar
from pydantic import BaseModel
from browser_use.agent.views import ActionResult
from browser_use.browser.context import BrowserContext
from browser_use.controller.service import Controller, DoneAction
from browser_use.controller.registry.service import Registry, RegisteredAction
from main_content_extractor import MainContentExtractor
from browser_use.controller.views import (
    ClickElementAction,
    DoneAction,
    ExtractPageContentAction,
    GoToUrlAction,
    InputTextAction,
    OpenTabAction,
    ScrollAction,
    SearchGoogleAction,
    SendKeysAction,
    SwitchTabAction,
)
import logging
import inspect
import asyncio
import os
from langchain_core.language_models.chat_models import BaseChatModel
from browser_use.agent.views import ActionModel, ActionResult

from src.utils.mcp_client import create_tool_param_model, setup_mcp_client_and_tools

from browser_use.utils import time_execution_sync

logger = logging.getLogger(__name__)

Context = TypeVar('Context')

# Profile and Application Storage Paths
PROFILE_DIR = "./data/profile"
APPLICATIONS_DIR = "./data/applications"
PROFILE_FILE = os.path.join(PROFILE_DIR, "profile.json")
APPLICATIONS_FILE = os.path.join(APPLICATIONS_DIR, "applications.json")

class CustomController(Controller):
    def __init__(self, exclude_actions: list[str] = [],
                 output_model: Optional[Type[BaseModel]] = None,
                 ask_assistant_callback: Optional[Union[Callable[[str, BrowserContext], Dict[str, Any]], Callable[
                     [str, BrowserContext], Awaitable[Dict[str, Any]]]]] = None,
                 ):
        super().__init__(exclude_actions=exclude_actions, output_model=output_model)
        self._register_custom_actions()
        self._register_job_application_tools()
        self.ask_assistant_callback = ask_assistant_callback
        self.mcp_client = None
        self.mcp_server_config = None
        self._ensure_data_directories()

    def _ensure_data_directories(self):
        """Ensure data directories exist"""
        os.makedirs(PROFILE_DIR, exist_ok=True)
        os.makedirs(APPLICATIONS_DIR, exist_ok=True)

    def _register_custom_actions(self):
        """Register all custom browser actions"""

        @self.registry.action(
            "When executing tasks, prioritize autonomous completion. However, if you encounter a definitive blocker "
            "that prevents you from proceeding independently – such as needing credentials you don't possess, "
            "requiring subjective human judgment, needing a physical action performed, encountering complex CAPTCHAs, "
            "or facing limitations in your capabilities – you must request human assistance."
        )
        async def ask_for_assistant(query: str, browser: BrowserContext):
            if self.ask_assistant_callback:
                if inspect.iscoroutinefunction(self.ask_assistant_callback):
                    user_response = await self.ask_assistant_callback(query, browser)
                else:
                    user_response = self.ask_assistant_callback(query, browser)
                msg = f"AI ask: {query}. User response: {user_response['response']}"
                logger.info(msg)
                return ActionResult(extracted_content=msg, include_in_memory=True)
            else:
                return ActionResult(extracted_content="Human cannot help you. Please try another way.",
                                    include_in_memory=True)

        @self.registry.action(
            'Upload file to interactive element with file path ',
        )
        async def upload_file(index: int, path: str, browser: BrowserContext, available_file_paths: list[str]):
            if path not in available_file_paths:
                return ActionResult(error=f'File path {path} is not available')

            if not os.path.exists(path):
                return ActionResult(error=f'File {path} does not exist')

            dom_el = await browser.get_dom_element_by_index(index)

            file_upload_dom_el = dom_el.get_file_upload_element()

            if file_upload_dom_el is None:
                msg = f'No file upload element found at index {index}'
                logger.info(msg)
                return ActionResult(error=msg)

            file_upload_el = await browser.get_locate_element(file_upload_dom_el)

            if file_upload_el is None:
                msg = f'No file upload element found at index {index}'
                logger.info(msg)
                return ActionResult(error=msg)

            try:
                await file_upload_el.set_input_files(path)
                msg = f'Successfully uploaded file to index {index}'
                logger.info(msg)
                return ActionResult(extracted_content=msg, include_in_memory=True)
            except Exception as e:
                msg = f'Failed to upload file to index {index}: {str(e)}'
                logger.info(msg)
                return ActionResult(error=msg)

    def _register_job_application_tools(self):
        """Register job application specific tools"""

        @self.registry.action(
            "Get the user's job application profile including personal details, experience, skills, and preferences"
        )
        async def get_profile() -> Dict[str, Any]:
            """Retrieve the user's job application profile"""
            try:
                if os.path.exists(PROFILE_FILE):
                    with open(PROFILE_FILE, 'r', encoding='utf-8') as f:
                        profile = json.load(f)
                    return ActionResult(
                        extracted_content=f"Profile retrieved successfully: {json.dumps(profile, indent=2)}",
                        include_in_memory=True
                    )
                else:
                    # Return default empty profile structure
                    default_profile = {
                        "personal": {
                            "full_name": "",
                            "email": "",
                            "phone": "",
                            "address": "",
                            "linkedin_url": "",
                            "portfolio_url": ""
                        },
                        "professional": {
                            "current_position": {
                                "job_title": "",
                                "company": "",
                                "start_date": "",
                                "end_date": "Present",
                                "work_description": ""
                            },
                            "previous_positions": [
                                # Each will be: {"job_title": "", "company": "", "start_date": "", "end_date": "", "work_description": ""}
                            ],
                            "years_experience": 0,
                            "skills": [],
                            "education": []
                        },
                        "preferences": {
                            "target_roles": [],
                            "target_locations": [],
                            "salary_min": 0,
                            "work_authorization": "",
                            "visa_status": "",
                            "availability": "",
                            "remote_preference": ""
                        },
                        "eeo_information": {
                            "race_ethnicity": "Prefer not to answer",
                            "gender": "Prefer not to answer",
                            "veteran_status": "Prefer not to answer",
                            "disability_status": "Prefer not to answer",
                            "voluntary_disclosure": True
                        },
                        "documents": {
                            "resume_path": "",
                            "cover_letter_template": ""
                        }
                    }
                    return ActionResult(
                        extracted_content=f"No profile found. Default profile structure: {json.dumps(default_profile, indent=2)}",
                        include_in_memory=True
                    )
            except Exception as e:
                logger.error(f"Error retrieving profile: {e}")
                return ActionResult(
                    extracted_content=f"Error retrieving profile: {str(e)}",
                    include_in_memory=True
                )

        @self.registry.action(
            "Update the user's job application profile with new information"
        )
        async def update_profile(profile_data: Dict[str, Any]) -> Dict[str, Any]:
            """Update the user's job application profile"""
            try:
                # Load existing profile or create new one
                existing_profile = {}
                if os.path.exists(PROFILE_FILE):
                    with open(PROFILE_FILE, 'r', encoding='utf-8') as f:
                        existing_profile = json.load(f)
                
                # Deep merge the new data with existing profile
                def deep_merge(existing, new):
                    for key, value in new.items():
                        if key in existing and isinstance(existing[key], dict) and isinstance(value, dict):
                            deep_merge(existing[key], value)
                        else:
                            existing[key] = value
                    return existing
                
                updated_profile = deep_merge(existing_profile, profile_data)
                updated_profile["last_updated"] = datetime.now().isoformat()
                
                # Save updated profile
                with open(PROFILE_FILE, 'w', encoding='utf-8') as f:
                    json.dump(updated_profile, f, indent=2, ensure_ascii=False)
                
                return ActionResult(
                    extracted_content=f"Profile updated successfully: {json.dumps(updated_profile, indent=2)}",
                    include_in_memory=True
                )
            except Exception as e:
                logger.error(f"Error updating profile: {e}")
                return ActionResult(
                    extracted_content=f"Error updating profile: {str(e)}",
                    include_in_memory=True
                )

        @self.registry.action(
            "Log a job application attempt with detailed results and metadata"
        )
        async def log_application(
            job_title: str,
            company: str,
            job_url: str,
            status: str,
            notes: str = "",
            application_method: str = "Easy Apply",
            job_location: str = "",
            salary_range: str = "",
            application_duration: float = 0.0
        ) -> Dict[str, Any]:
            """Log a job application attempt with comprehensive metadata"""
            try:
                # Load existing applications
                applications = []
                if os.path.exists(APPLICATIONS_FILE):
                    with open(APPLICATIONS_FILE, 'r', encoding='utf-8') as f:
                        applications = json.load(f)
                
                # Create new application entry with enhanced data
                application_entry = {
                    "id": len(applications) + 1,
                    "job_title": job_title,
                    "company": company,
                    "job_url": job_url,
                    "status": status,  # "submitted", "failed", "skipped"
                    "applied_date": datetime.now().isoformat(),
                    "notes": notes,
                    "application_method": application_method,
                    "job_location": job_location,
                    "salary_range": salary_range,
                    "application_duration_seconds": application_duration,
                    "platform": "LinkedIn" if "linkedin.com" in job_url else "Other"
                }
                
                applications.append(application_entry)
                
                # Save updated applications list
                with open(APPLICATIONS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(applications, f, indent=2, ensure_ascii=False)
                
                return ActionResult(
                    extracted_content=f"Application logged: {application_entry['company']} - {application_entry['job_title']} ({status})",
                    include_in_memory=True
                )
            except Exception as e:
                logger.error(f"Error logging application: {e}")
                return ActionResult(
                    extracted_content=f"Error logging application: {str(e)}",
                    include_in_memory=True
                )

        @self.registry.action(
            "Retrieve the list of all job applications with their status and analytics"
        )
        async def list_applications(limit: int = 50, status_filter: str = "all") -> Dict[str, Any]:
            """List all job applications with filtering and analytics"""
            try:
                if os.path.exists(APPLICATIONS_FILE):
                    with open(APPLICATIONS_FILE, 'r', encoding='utf-8') as f:
                        applications = json.load(f)
                    
                    # Filter applications if requested
                    if status_filter.lower() != "all":
                        applications = [app for app in applications if app.get('status', '').lower() == status_filter.lower()]
                    
                    # Sort by date (most recent first) and limit results
                    applications.sort(key=lambda x: x.get('applied_date', ''), reverse=True)
                    limited_applications = applications[:limit]
                    
                    # Calculate analytics
                    total_applications = len(applications)
                    platform_stats = {}
                    status_stats = {
                        "submitted": 0,
                        "failed": 0,
                        "skipped": 0
                    }
                    
                    for app in applications:
                        platform = app.get('platform', 'Other')
                        platform_stats[platform] = platform_stats.get(platform, 0) + 1
                        
                        status = app.get('status', 'unknown')
                        if status in status_stats:
                            status_stats[status] += 1
                    
                    summary = {
                        "total_applications": total_applications,
                        "recent_applications": limited_applications,
                        "stats": status_stats,
                        "platform_stats": platform_stats,
                        "success_rate": (status_stats["submitted"] / total_applications * 100) if total_applications > 0 else 0,
                        "filter_applied": status_filter,
                        "results_limited_to": limit
                    }
                    
                    return ActionResult(
                        extracted_content=f"Applications retrieved: {json.dumps(summary, indent=2)}",
                        include_in_memory=True
                    )
                else:
                    return ActionResult(
                        extracted_content="No applications found. Application history is empty.",
                        include_in_memory=True
                    )
            except Exception as e:
                logger.error(f"Error listing applications: {e}")
                return ActionResult(
                    extracted_content=f"Error listing applications: {str(e)}",
                    include_in_memory=True
                )

        @self.registry.action(
            "Extract job details from a LinkedIn job search results page"
        )
        async def extract_linkedin_jobs(page_url: str, max_jobs: int = 25) -> Dict[str, Any]:
            """Extract Easy Apply job listings from LinkedIn search results"""
            try:
                # This would be called by the browser automation agent
                # The actual extraction logic is handled in the browser automation
                return ActionResult(
                    extracted_content=f"LinkedIn job extraction initiated for: {page_url} (max {max_jobs} jobs)",
                    include_in_memory=True
                )
            except Exception as e:
                logger.error(f"Error in LinkedIn job extraction: {e}")
                return ActionResult(
                    extracted_content=f"Error extracting LinkedIn jobs: {str(e)}",
                    include_in_memory=True
                )

        @self.registry.action(
            "Check if a job application form field should be filled based on profile data"
        )
        async def get_field_value(field_name: str, field_type: str = "text", context: str = "") -> Dict[str, Any]:
            """Get the appropriate value for a job application form field from profile data"""
            try:
                # Load current profile
                profile = {}
                if os.path.exists(PROFILE_FILE):
                    with open(PROFILE_FILE, 'r', encoding='utf-8') as f:
                        profile = json.load(f)
                
                field_name_lower = field_name.lower()
                suggested_value = ""
                confidence = "high"
                
                # Personal information mapping
                if "first name" in field_name_lower or field_name_lower == "firstname":
                    full_name = profile.get("personal", {}).get("full_name", "")
                    suggested_value = full_name.split()[0] if full_name else ""
                elif "last name" in field_name_lower or field_name_lower == "lastname":
                    full_name = profile.get("personal", {}).get("full_name", "")
                    suggested_value = " ".join(full_name.split()[1:]) if full_name and len(full_name.split()) > 1 else ""
                elif "email" in field_name_lower:
                    suggested_value = profile.get("personal", {}).get("email", "")
                elif "phone" in field_name_lower:
                    suggested_value = profile.get("personal", {}).get("phone", "")
                elif "address" in field_name_lower or "location" in field_name_lower:
                    suggested_value = profile.get("personal", {}).get("address", "")
                elif "linkedin" in field_name_lower:
                    suggested_value = profile.get("personal", {}).get("linkedin_url", "")
                
                # Professional information mapping
                elif "current" in field_name_lower and "title" in field_name_lower:
                    suggested_value = profile.get("professional", {}).get("current_position", {}).get("job_title", "")
                elif "current" in field_name_lower and "company" in field_name_lower:
                    suggested_value = profile.get("professional", {}).get("current_position", {}).get("company", "")
                elif "experience" in field_name_lower and "years" in field_name_lower:
                    suggested_value = str(profile.get("professional", {}).get("years_experience", 0))
                
                # Preferences and requirements
                elif "salary" in field_name_lower:
                    suggested_value = str(profile.get("preferences", {}).get("salary_min", ""))
                elif "authorization" in field_name_lower or "visa" in field_name_lower:
                    suggested_value = profile.get("preferences", {}).get("work_authorization", "")
                elif "start date" in field_name_lower or "availability" in field_name_lower:
                    suggested_value = profile.get("preferences", {}).get("availability", "")
                elif "remote" in field_name_lower:
                    suggested_value = profile.get("preferences", {}).get("remote_preference", "")
                
                # EEO fields
                elif "race" in field_name_lower or "ethnicity" in field_name_lower:
                    suggested_value = profile.get("eeo_information", {}).get("race_ethnicity", "Prefer not to answer")
                elif "gender" in field_name_lower:
                    suggested_value = profile.get("eeo_information", {}).get("gender", "Prefer not to answer")
                elif "veteran" in field_name_lower:
                    suggested_value = profile.get("eeo_information", {}).get("veteran_status", "Prefer not to answer")
                elif "disability" in field_name_lower:
                    suggested_value = profile.get("eeo_information", {}).get("disability_status", "Prefer not to answer")
                
                else:
                    suggested_value = ""
                    confidence = "low"
                
                result = {
                    "field_name": field_name,
                    "suggested_value": suggested_value,
                    "confidence": confidence,
                    "field_type": field_type,
                    "context": context,
                    "found_in_profile": bool(suggested_value)
                }
                
                return ActionResult(
                    extracted_content=f"Field mapping result: {json.dumps(result, indent=2)}",
                    include_in_memory=True
                )
                
            except Exception as e:
                logger.error(f"Error getting field value: {e}")
                return ActionResult(
                    extracted_content=f"Error getting field value for {field_name}: {str(e)}",
                    include_in_memory=True
                )

        @self.registry.action(
            "Start application session tracking for progress monitoring"
        )
        async def start_application_session(session_name: str, total_expected_jobs: int = 0) -> Dict[str, Any]:
            """Start tracking an application session for progress monitoring"""
            try:
                session_data = {
                    "session_name": session_name,
                    "start_time": datetime.now().isoformat(),
                    "total_expected_jobs": total_expected_jobs,
                    "jobs_processed": 0,
                    "applications_submitted": 0,
                    "applications_failed": 0,
                    "status": "running"
                }
                
                # Store session data in a temporary location for real-time tracking
                session_file = f"./data/profile/current_session.json"
                with open(session_file, 'w', encoding='utf-8') as f:
                    json.dump(session_data, f, indent=2, ensure_ascii=False)
                
                return ActionResult(
                    extracted_content=f"Application session started: {session_name}",
                    include_in_memory=True
                )
                
            except Exception as e:
                logger.error(f"Error starting application session: {e}")
                return ActionResult(
                    extracted_content=f"Error starting session: {str(e)}",
                    include_in_memory=True
                )

    @time_execution_sync('--act')
    async def act(
            self,
            action: ActionModel,
            browser_context: Optional[BrowserContext] = None,
            #
            page_extraction_llm: Optional[BaseChatModel] = None,
            sensitive_data: Optional[Dict[str, str]] = None,
            available_file_paths: Optional[list[str]] = None,
            #
            context: Context | None = None,
    ) -> ActionResult:
        """Execute an action"""

        try:
            for action_name, params in action.model_dump(exclude_unset=True).items():
                if params is not None:
                    if action_name.startswith("mcp"):
                        # this is a mcp tool
                        logger.debug(f"Invoke MCP tool: {action_name}")
                        mcp_tool = self.registry.registry.actions.get(action_name).function
                        result = await mcp_tool.ainvoke(params)
                    else:
                        result = await self.registry.execute_action(
                            action_name,
                            params,
                            browser=browser_context,
                            page_extraction_llm=page_extraction_llm,
                            sensitive_data=sensitive_data,
                            available_file_paths=available_file_paths,
                            context=context,
                        )

                    if isinstance(result, str):
                        return ActionResult(extracted_content=result)
                    elif isinstance(result, ActionResult):
                        return result
                    elif result is None:
                        return ActionResult()
                    else:
                        raise ValueError(f'Invalid action result type: {type(result)} of {result}')
            return ActionResult()
        except Exception as e:
            raise e

    async def setup_mcp_client(self, mcp_server_config: Optional[Dict[str, Any]] = None):
        self.mcp_server_config = mcp_server_config
        if self.mcp_server_config:
            self.mcp_client = await setup_mcp_client_and_tools(self.mcp_server_config)
            self.register_mcp_tools()

    def register_mcp_tools(self):
        """
        Register the MCP tools used by this controller.
        """
        if self.mcp_client:
            for server_name in self.mcp_client.server_name_to_tools:
                for tool in self.mcp_client.server_name_to_tools[server_name]:
                    tool_name = f"mcp.{server_name}.{tool.name}"
                    self.registry.registry.actions[tool_name] = RegisteredAction(
                        name=tool_name,
                        description=tool.description,
                        function=tool,
                        param_model=create_tool_param_model(tool),
                    )
                    logger.info(f"Add mcp tool: {tool_name}")
                logger.debug(
                    f"Registered {len(self.mcp_client.server_name_to_tools[server_name])} mcp tools for {server_name}")
        else:
            logger.warning(f"MCP client not started.")

    async def close_mcp_client(self):
        if self.mcp_client:
            await self.mcp_client.__aexit__(None, None, None)
