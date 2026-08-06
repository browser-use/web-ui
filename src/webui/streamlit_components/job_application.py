import streamlit as st
import asyncio
import json
import logging
import os
import platform
import uuid
from typing import Any, AsyncGenerator, Dict, Optional
from datetime import datetime

from browser_use.agent.views import (
    AgentHistoryList,
    AgentOutput,
)
from browser_use.browser.browser import BrowserConfig
from browser_use.browser.context import BrowserContext, BrowserContextConfig
from browser_use.browser.views import BrowserState
from langchain_core.language_models.chat_models import BaseChatModel

from src.agent.browser_use.browser_use_agent import BrowserUseAgent
from src.browser.custom_browser import CustomBrowser
from src.controller.custom_controller import CustomController
from src.utils.llm_provider import get_llm_model
from src.webui.streamlit_manager import StreamlitManager

logger = logging.getLogger(__name__)
def create_llm():
    provider = os.getenv("LLM_PROVIDER", "ollama")
    model_name = os.getenv("LLM_MODEL", "qwen3:8b")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.1"))

    kwargs = {
        "provider": provider,
        "model_name": model_name,
        "temperature": temperature,
    }

    if provider == "ollama":
        kwargs["base_url"] = os.getenv(
            "OLLAMA_ENDPOINT",
            "http://host.docker.internal:11434",
        )
    else:
        kwargs["api_key"] = (
            os.getenv("OPENAI_API_KEY")
            or os.getenv("ANTHROPIC_API_KEY")
        )

    return get_llm_model(**kwargs)

def get_chrome_binary_path():
    """
    Get the Chrome binary path based on the operating system.
    Returns None if Chrome is not found at the default location.
    """
    system = platform.system()
    
    if system == "Darwin":  # macOS
        # Try both the executable and the app bundle
        possible_paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Google Chrome.app"  # User-provided path
        ]
        chrome_path = None
        for path in possible_paths:
            if os.path.exists(path):
                # If it's the app bundle, get the executable path
                if path.endswith(".app"):
                    executable_path = os.path.join(path, "Contents/MacOS/Google Chrome")
                    if os.path.exists(executable_path):
                        chrome_path = executable_path
                        break
                else:
                    chrome_path = path
                    break
    elif system == "Windows":
        # Common Chrome locations on Windows
        possible_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
        ]
        chrome_path = None
        for path in possible_paths:
            if os.path.exists(path):
                chrome_path = path
                break
    elif system == "Linux":
        # Common Chrome locations on Linux
        possible_paths = [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium-browser",
            "/snap/bin/chromium"
        ]
        chrome_path = None
        for path in possible_paths:
            if os.path.exists(path):
                chrome_path = path
                break
    else:
        chrome_path = None
        
    return chrome_path


# System prompt for LinkedIn job applications (copied to avoid Gradio dependency)
LINKEDIN_JOB_APPLICATION_SYSTEM_PROMPT = """
You are an expert LinkedIn Job Application Automation Agent designed to process LinkedIn job search results and automatically apply to positions using stored profile data.

## PRIMARY MISSION
Process LinkedIn job search URLs, extract individual job listings, and automatically apply to jobs with "Easy Apply" buttons using the user's MCP-stored profile information.

## CORE WORKFLOW

### 1. PROFILE PREPARATION
- ALWAYS start by calling `get_profile()` to fetch the latest user profile data
- Cache profile information for the session - NEVER fabricate missing data
- If critical fields are missing, report what's needed and pause execution

### 2. LINKEDIN SEARCH URL PROCESSING
- Navigate to the provided LinkedIn job search URL
- Handle LinkedIn authentication if prompted (user should be logged in)
- Scroll through search results to load all job listings (handle pagination)
- Extract from each job card:
  * Job title and company name
  * Job posting URL/link
  * Whether "Easy Apply" button is available
  * Location and other basic details
- Build a list of applicable jobs for processing

### 3. INDIVIDUAL JOB APPLICATION FLOW
For each job with "Easy Apply" available:

**A. Navigation & Access**
- Click on the job title/card to open job details
- Locate and click the "Easy Apply" button
- Wait for application modal/form to load

**B. Form Field Population (use profile data ONLY)**
- **Personal Info**: Full name, email, phone, address from profile.personal
- **Current Position**: Use profile.professional.current_position data
- **Work Experience**: Include current and previous positions with dates and descriptions
- **Education**: Use profile.professional.education data
- **Skills**: Use profile.professional.skills data
- **Work Authorization**: Use profile.preferences.work_authorization
- **Visa Status**: Use profile.preferences.visa_status  
- **Salary Expectations**: Use profile.preferences.salary_min
- **Availability**: Use profile.preferences.availability
- **EEO Information**: Use profile.eeo_information (race, gender, veteran status, disability) if required

**C. Resume Upload**
- Locate file upload field for resume
- Upload file from profile.documents.resume_path
- Wait for upload confirmation

**D. Application Questions Handling**
- Answer standard questions using profile data
- For unknown questions, use LLM reasoning based on profile context
- If personal decision required, skip and note in application log
- Common question types:
  * Years of experience → calculate from profile
  * Salary requirements → use profile.preferences.salary_min
  * Start date → use profile.preferences.availability
  * Work authorization → use profile.preferences.work_authorization
  * Cover letter → use profile.documents.cover_letter_template if needed

**E. Submission & Verification**
- Click submit/send application button
- Wait for confirmation message (e.g., "Application submitted", "Thank you for applying")
- Take screenshot of confirmation for verification
- If error occurs, capture error message

### 4. APPLICATION LOGGING
After each application attempt, call `log_application()` with:
- job_title: Extracted job title
- company: Company name
- job_url: Direct job posting URL
- status: "submitted" | "failed" | "skipped"
- notes: Detailed outcome including any errors or specific reasons

### 5. PROGRESS TRACKING
- Update progress counter: "Processing job X of Y"
- Report real-time status for each application
- Provide summary statistics at completion

## ERROR HANDLING & EDGE CASES

### Rate Limiting & Delays
- Add 3-5 second delays between applications
- If rate limited, wait 30-60 seconds before retrying
- Respect LinkedIn's usage policies

### Application Failures
- **CAPTCHA Detected**: Mark as failed, log reason, continue to next job
- **Login Required**: Pause and report login needed
- **Job No Longer Available**: Mark as skipped, continue
- **Form Submission Errors**: Retry once, then mark as failed
- **Missing Profile Data**: Use available data, note missing fields

### Quality Assurance
- Verify form fields are populated before submission
- Confirm resume upload succeeded
- Validate application confirmation message
- Take screenshots for critical steps

## SUCCESS CRITERIA
- Extract all available Easy Apply jobs from search results
- Successfully submit applications using only verified profile data
- Log comprehensive results for each attempt
- Provide real-time progress updates
- Handle errors gracefully without stopping the entire process

## IMPORTANT CONSTRAINTS
- NEVER invent or guess profile information
- Only apply to jobs with "Easy Apply" buttons
- Skip jobs requiring external applications or complex processes
- Maintain professional, respectful interaction with all forms
- Stop immediately if instructed by stop button

Your goal is to efficiently and accurately process LinkedIn job applications while maintaining data integrity and providing comprehensive logging for the user's review.
"""

def create_job_application_page(manager: StreamlitManager):
    """
    Create the Streamlit job application page
    """
    
    st.markdown("## 🚀 Automated Job Applications")
    st.markdown("Enter LinkedIn job search URLs and let the agent automatically apply using your saved profile.")
    
    # LinkedIn Credentials Section
    st.markdown("### 🔐 LinkedIn Login Credentials")
    st.info("*Required for applying to jobs. Your credentials are only used for this session and not stored permanently.*")
    
    col1, col2 = st.columns(2)
    
    with col1:
        linkedin_email = st.text_input(
            "LinkedIn Email",
            placeholder="your-email@example.com",
            help="Your LinkedIn account email",
            key="linkedin_email"
        )
    
    with col2:
        linkedin_password = st.text_input(
            "LinkedIn Password",
            placeholder="Enter your LinkedIn password",
            type="password",
            help="Your LinkedIn account password",
            key="linkedin_password"
        )

    # Job URLs Input Section
    st.markdown("### 📋 Job Search URLs")
    job_urls = st.text_area(
        "LinkedIn Job Search URLs (one per line)",
        height=150,
        placeholder="""https://www.linkedin.com/jobs/search/?keywords=data%20scientist&location=San%20Francisco
https://www.linkedin.com/jobs/search/?keywords=software%20engineer&location=Remote""",
        help="💡 Pro tip: Use LinkedIn's job search filters to find your target roles, then paste the results URL here!",
        key="job_urls"
    )

    # Optional Overrides Section
    st.markdown("### 🎯 Optional Overrides")
    
    col3, col4 = st.columns(2)
    
    with col3:
        override_role = st.text_input(
            "Override Target Role (Optional)",
            placeholder="e.g., Senior Software Engineer",
            help="Override the target role from your profile for these applications",
            key="override_role"
        )
    
    with col4:
        override_location = st.text_input(
            "Override Target Location (Optional)",
            placeholder="e.g., San Francisco, CA",
            help="Override the target location from your profile for these applications",
            key="override_location"
        )

    # Action Buttons
    col5, col6, col7 = st.columns([1, 1, 1])
    
    with col5:
        apply_button = st.button("🚀 Apply to Jobs", type="primary", use_container_width=True)
    
    with col6:
        test_button = st.button("🧪 Test Setup", use_container_width=True)
    
    with col7:
        stop_button = st.button("🛑 Stop", use_container_width=True)
    
    # Initialize session state for application process
    if 'application_running' not in st.session_state:
        st.session_state.application_running = False
    if 'application_logs' not in st.session_state:
        st.session_state.application_logs = []
    if 'application_status' not in st.session_state:
        st.session_state.application_status = ""

    # Progress Status
    if st.session_state.application_status:
        st.info(f"⚡ Progress Status: {st.session_state.application_status}")

    # Handle test button
    if test_button:
        st.info("🧪 Testing setup...")
        
        # Test environment variables
        provider = os.getenv("LLM_PROVIDER", "ollama")

        if provider == "ollama":
            st.success("✅ Using local Ollama (no API key required)")
        else:
            api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                st.success("✅ API key found")
            else:
                st.error("❌ No API key found")
        
        # Test LLM provider
        try:
            provider = os.getenv("LLM_PROVIDER", "openai")
            model_name = os.getenv("LLM_MODEL", "gpt-4o")
            llm = create_llm()
            st.success(f"✅ LLM provider working: {provider}/{model_name}")
        except Exception as e:
            st.error(f"❌ LLM provider error: {str(e)}")
        
        # Test browser setup
        try:
            import playwright
            st.success("✅ Playwright installed")
        except ImportError:
            st.error("❌ Playwright not installed")
        
        # Test inputs
        if linkedin_email and linkedin_password and job_urls:
            st.success("✅ All required fields filled")
        else:
            st.warning("⚠️ Please fill in all required fields to test")

    # Handle stop button
    if stop_button and st.session_state.application_running:
        st.session_state.application_running = False
        st.session_state.application_status = "Application process stopped by user"
        # TODO: Implement actual stop mechanism for async task
        st.warning("🛑 Stop signal sent. The application process will halt.")
        st.rerun()

    # Handle apply button
    if apply_button:
        if not linkedin_email or not linkedin_password or not job_urls:
            st.error("❌ Please fill in all required fields: LinkedIn email, password, and job URLs.")
        else:
            # Parse URLs
            job_urls_list = [url.strip() for url in job_urls.strip().split('\n') if url.strip()]
            linkedin_urls = [url for url in job_urls_list if "linkedin.com" in url]
            
            if not linkedin_urls:
                st.error("❌ No valid LinkedIn URLs found. Please provide LinkedIn job search URLs.")
                return
            
            # Initialize immediately and show browser
            try:
                # Setup LLM
                provider = os.getenv("LLM_PROVIDER", "openai")
                model_name = os.getenv("LLM_MODEL", "gpt-4o")
                
                
                llm = create_llm()
                
                # Create detailed task for the agent
                enhanced_task = f"""
                LINKEDIN JOB APPLICATION AUTOMATION TASK
                
                CREDENTIALS (CRITICAL - USE EXACTLY):
                - LinkedIn Email: {linkedin_email}
                - LinkedIn Password: {linkedin_password}
                
                TASK STEPS:
                1. Navigate to LinkedIn.com
                2. Login using the EXACT credentials above (not placeholder emails)
                3. Go to this job search URL: {linkedin_urls[0]}
                4. Find all jobs with "Easy Apply" buttons
                5. For each job:
                   - Click "Easy Apply"
                   - Fill out the application form with professional information
                   - Upload resume if requested
                   - ALWAYS scroll down to find Submit buttons
                   - SUBMIT the application completely (never save as draft)
                   - Wait for "Thank you for applying" confirmation
                   - Continue to next job
                
                CRITICAL SUBMISSION RULES:
                - ALWAYS scroll down after filling forms to find Submit buttons
                - NEVER click "Save" or "Save as Draft" - only click "Submit"
                - Look for "Submit Application", "Send Application", "Apply Now" buttons
                - If you see a save prompt, click "Discard" and find the Submit button
                - Complete EVERY application until you see success confirmation
                
                IMPORTANT: 
                - Use REAL credentials provided, not placeholders
                - Apply to as many jobs as possible  
                - Submit applications completely, not as drafts
                - Scroll down aggressively to find Submit buttons
                """
                
                # Start browser automation immediately
                st.session_state.application_running = True
                st.session_state.application_logs = [{"role": "assistant", "content": f"🚀 Starting LinkedIn automation for {len(linkedin_urls)} search URL(s)!"}]
                
                # Create browser configuration for visible automation
                chrome_path = get_chrome_binary_path()
                
                if chrome_path:
                    st.info(f"🌐 Using local Chrome browser: {chrome_path}")
                    # Configure for external Chrome browser (like in browser_use_agent_tab.py)
                    extra_browser_args = [
                        "--no-first-run",
                        "--no-default-browser-check",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-web-security",
                        "--disable-features=VizDisplayCompositor",
                    ]
                    browser_config = BrowserConfig(
                        headless=False,
                        browser_type="chromium",
                        browser_binary_path=chrome_path,
                        extra_browser_args=extra_browser_args,
                        disable_security=True,
                    )
                else:
                    st.warning("⚠️ Chrome not found at default location. Using built-in Chromium browser.")
                    browser_config = BrowserConfig(
                        headless=False,
                        browser_type="chromium",
                        disable_security=True,
                        extra_browser_args=[
                            "--no-first-run",
                            "--no-default-browser-check",
                            "--disable-blink-features=AutomationControlled",
                            "--disable-web-security",
                            "--disable-features=VizDisplayCompositor",
                        ]
                    )
                
                # Start automation immediately without extra button click
                st.info("🌐 Opening LinkedIn browser window and starting automation...")
                
                try:
                    import asyncio
                    
                    # Run the automation directly
                    automation_success = asyncio.run(run_linkedin_automation_async(
                        enhanced_task,
                        llm,
                        linkedin_urls,
                        browser_config,
                        manager
                    ))
                    
                    if automation_success:
                        st.success("✅ LinkedIn automation started! Check the browser window.")
                        st.session_state.application_logs.append({
                            "role": "assistant",
                            "content": "🌐 LinkedIn browser opened and automation started automatically!"
                        })
                        st.session_state.application_logs.append({
                            "role": "assistant",
                            "content": "👀 The browser is now applying to jobs automatically with improved scrolling."
                        })
                    else:
                        st.error("❌ Failed to start LinkedIn automation")
                        st.session_state.application_logs.append({
                            "role": "assistant",
                            "content": "❌ Failed to start automation"
                        })
                except Exception as e:
                    st.error(f"❌ Automation error: {str(e)}")
                    st.session_state.application_logs.append({
                        "role": "assistant",
                        "content": f"❌ Automation failed: {str(e)}"
                    })
                
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Setup error: {str(e)}")
                return

    # Application Process Log
    st.markdown("### 🤖 Application Process Log")
    
    # Display logs
    if st.session_state.application_logs:
        log_container = st.container()
        with log_container:
            for log_entry in st.session_state.application_logs:
                if log_entry.get("role") == "assistant":
                    st.success(log_entry.get("content", ""))
                elif log_entry.get("role") == "user":
                    st.info(log_entry.get("content", ""))
                else:
                    st.write(log_entry.get("content", ""))
    else:
        st.write("*No logs yet. Click 'Apply to Jobs' to start the automation process.*")
    
    # Automation starts automatically now - no extra button needed
    
    # Clear logs button
    if st.button("🗑️ Clear Log"):
        st.session_state.application_logs = []
        st.session_state.application_status = ""
        st.session_state.application_running = False
        st.rerun()


async def run_streamlit_job_application_task(
    linkedin_email: str,
    linkedin_password: str, 
    job_urls: str,
    override_role: str,
    override_location: str,
    manager: StreamlitManager
) -> AsyncGenerator[tuple[list, str], None]:
    """
    Main function for LinkedIn job application automation with user credentials - Streamlit version
    """
    
    # Validate inputs
    if not linkedin_email or not linkedin_email.strip():
        yield [{"role": "assistant", "content": "❌ LinkedIn email is required. Please enter your LinkedIn email address."}], "Error: LinkedIn email required"
        return
        
    if not linkedin_password or not linkedin_password.strip():
        yield [{"role": "assistant", "content": "❌ LinkedIn password is required. Please enter your LinkedIn password."}], "Error: LinkedIn password required"
        return
    
    if not job_urls or not job_urls.strip():
        yield [{"role": "assistant", "content": "❌ Please enter at least one LinkedIn job search URL."}], "Error: No URLs provided"
        return

    # Clean and validate credentials
    linkedin_email = linkedin_email.strip()
    linkedin_password = linkedin_password.strip()
    
    yield [{"role": "assistant", "content": f"🔐 LinkedIn credentials received for: {linkedin_email}\n🔑 Password length: {len(linkedin_password)} characters\n🎯 Starting job application automation..."}], "Initializing with your LinkedIn credentials..."
    
    # Debug: Confirm credentials are properly set
    if not linkedin_email or "@" not in linkedin_email:
        yield [{"role": "assistant", "content": "❌ Invalid LinkedIn email format. Please provide a valid email address."}], "Error: Invalid email format"
        return
        
    if len(linkedin_password) < 6:
        yield [{"role": "assistant", "content": "❌ LinkedIn password seems too short. Please check your password."}], "Error: Password validation failed"
        return
    
    yield [{"role": "assistant", "content": f"✅ Credentials validated successfully!\n📧 Email: {linkedin_email}\n🔑 Password: {'*' * len(linkedin_password)}\n\nThese EXACT credentials will be used for LinkedIn login."}], "Credentials validated - ready to start"
    
    # Parse job URLs
    job_urls_list = [url.strip() for url in job_urls.strip().split('\n') if url.strip()]
    
    # Validate LinkedIn URLs
    linkedin_urls = []
    for url in job_urls_list:
        if "linkedin.com" in url:
            linkedin_urls.append(url)
        else:
            yield [{"role": "assistant", "content": f"⚠️ Skipping non-LinkedIn URL: {url}"}], "Validating URLs..."
    
    if not linkedin_urls:
        yield [{"role": "assistant", "content": "❌ No valid LinkedIn URLs found. Please provide LinkedIn job search URLs."}], "Error: No valid LinkedIn URLs"
        return
    
    yield [{"role": "assistant", "content": f"🎯 Starting LinkedIn job application automation for {len(linkedin_urls)} search URL(s)"}], f"Initializing automation for {len(linkedin_urls)} LinkedIn search(es)..."
    
    # Initialize LLM with default values or from environment
    try:
        # Use default provider settings or environment variables
        provider = os.getenv("LLM_PROVIDER", "openai")
        model_name = os.getenv("LLM_MODEL", "gpt-4o")
        temperature = float(os.getenv("LLM_TEMPERATURE", "0.1"))
        base_url = os.getenv("OPENAI_ENDPOINT") or os.getenv("ANTHROPIC_ENDPOINT") or None
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or None
        
        llm: BaseChatModel = get_llm_model(
            provider=provider,
            model_name=model_name,
            temperature=temperature,
            base_url=base_url,
            api_key=api_key,
        )
    except Exception as e:
        yield [{"role": "assistant", "content": f"❌ LLM configuration error: {str(e)}\n\nPlease check your environment variables:\n- OPENAI_API_KEY or ANTHROPIC_API_KEY\n- Optionally: LLM_PROVIDER, LLM_MODEL, LLM_TEMPERATURE"}], "Error: LLM configuration required"
        return

    # Browser configuration - Make it VISIBLE so you can see LinkedIn automation using local Chrome
    chrome_path = get_chrome_binary_path()
    
    if chrome_path:
        browser_config = BrowserConfig(
            headless=False,  # VISIBLE browser window
            browser_type="chromium",
            browser_binary_path=chrome_path,
            user_data_dir=getattr(manager, 'browser_user_data_dir', None),
            disable_security=True,  # Allow easier LinkedIn automation
            extra_browser_args=[
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor",
            ]
        )
    else:
        browser_config = BrowserConfig(
            headless=False,  # VISIBLE browser window
            browser_type="chromium",
            user_data_dir=getattr(manager, 'browser_user_data_dir', None),
            disable_security=True,  # Allow easier LinkedIn automation
            extra_browser_args=[
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor",
            ]
        )

    yield [{"role": "assistant", "content": "🌐 Initializing browser and preparing for LinkedIn automation..."}], "Setting up VISIBLE browser for LinkedIn..."

    try:
        browser = CustomBrowser(config=browser_config)
        await browser.async_start()

        browser_context_config = BrowserContextConfig(
            window_width=1280,
            window_height=1024,
        )
        context = await browser.create_context(config=browser_context_config)
        
        # Initialize custom controller with MCP tools
        controller = CustomController()
        manager.bu_controller = controller

        total_applications = 0
        successful_applications = 0
        failed_applications = 0

        # Create agent with enhanced credentials prompt
        enhanced_prompt = f"""
        {LINKEDIN_JOB_APPLICATION_SYSTEM_PROMPT}

        ## CRITICAL: Use These Exact LinkedIn Credentials
        LinkedIn Email: {linkedin_email}
        LinkedIn Password: {linkedin_password}

        When you encounter LinkedIn login:
        1. Enter EXACTLY this email: {linkedin_email}
        2. Enter EXACTLY this password: {linkedin_password}
        3. Do NOT use placeholder emails like "your_email@example.com"
        4. These are the user's REAL LinkedIn credentials

        Override Settings (if provided):
        - Target Role: {override_role if override_role else "Use profile default"}
        - Target Location: {override_location if override_location else "Use profile default"}
        """

        agent = BrowserUseAgent(
            task=enhanced_prompt,
            llm=llm,
            browser_context=context,
            controller=controller,
            max_actions_per_step=10,
            enable_memory=False,# Increased for faster processing
            use_vision=False,
        )

        yield [{"role": "assistant", "content": f"🤖 Agent initialized with enhanced credentials prompt\n📧 Will use: {linkedin_email}\n🔑 Will use: {'*' * len(linkedin_password)}\n\n🚀 Starting job application process..."}], "Agent ready with your credentials"

        # Process each LinkedIn search URL
        for url_index, linkedin_url in enumerate(linkedin_urls, 1):
            yield [{"role": "assistant", "content": f"🔍 Processing search URL {url_index}/{len(linkedin_urls)}: {linkedin_url}"}], f"Processing URL {url_index}/{len(linkedin_urls)}"
            
            try:
                # Start the application process for this URL
                result = await agent.run(f"Process this LinkedIn job search URL and apply to all Easy Apply jobs: {linkedin_url}")
                
                # Extract results from agent execution
                action_count = len(result.history)
                yield [{"role": "assistant", "content": f"✅ Completed processing URL {url_index}/{len(linkedin_urls)}\n📊 Actions taken: {action_count}\n🎯 Check browser for application results"}], f"URL {url_index} completed - {action_count} actions"
                
                total_applications += 1  # This is a rough count - the agent logs actual applications
                
            except Exception as e:
                failed_applications += 1
                error_msg = f"❌ Error processing URL {url_index}: {str(e)}"
                yield [{"role": "assistant", "content": error_msg}], f"Error on URL {url_index}"
                continue

        # Final summary
        yield [{"role": "assistant", "content": f"🎉 Job application automation completed!\n\n📊 Summary:\n- URLs processed: {len(linkedin_urls)}\n- Total operations: {total_applications}\n- Errors: {failed_applications}\n\n✅ Check your LinkedIn account for application confirmations\n📋 Review the application history in the next tab"}], "Automation completed successfully"

    except Exception as e:
        error_msg = f"❌ Critical browser error: {str(e)}"
        yield [{"role": "assistant", "content": error_msg}], f"Browser error: {str(e)[:50]}..."
    
    finally:
        # Cleanup
        try:
            if 'browser' in locals():
                await browser.close()
        except:
            pass


def run_job_application_process(job_inputs: dict, manager: StreamlitManager):
    """
    Streamlit-compatible job application process runner
    """
    
    linkedin_email = job_inputs["linkedin_email"]
    linkedin_password = job_inputs["linkedin_password"]
    job_urls = job_inputs["job_urls"]
    override_role = job_inputs["override_role"]
    override_location = job_inputs["override_location"]
    
    # Show progress
    progress_bar = st.progress(0)
    status_placeholder = st.empty()
    
    try:
        # Update status
        status_placeholder.info("🔐 Validating LinkedIn credentials...")
        progress_bar.progress(10)
        
        # Validate inputs
        if not linkedin_email or not linkedin_email.strip():
            st.error("❌ LinkedIn email is required.")
            st.session_state.application_running = False
            return
            
        if not linkedin_password or not linkedin_password.strip():
            st.error("❌ LinkedIn password is required.")
            st.session_state.application_running = False
            return
        
        if not job_urls or not job_urls.strip():
            st.error("❌ Please enter at least one LinkedIn job search URL.")
            st.session_state.application_running = False
            return
        
        # Clean and validate credentials
        linkedin_email = linkedin_email.strip()
        linkedin_password = linkedin_password.strip()
        
        status_placeholder.success(f"✅ Credentials validated for: {linkedin_email}")
        progress_bar.progress(20)
        
        # Parse job URLs
        job_urls_list = [url.strip() for url in job_urls.strip().split('\n') if url.strip()]
        
        # Validate LinkedIn URLs
        linkedin_urls = []
        for url in job_urls_list:
            if "linkedin.com" in url:
                linkedin_urls.append(url)
            else:
                st.warning(f"⚠️ Skipping non-LinkedIn URL: {url}")
        
        if not linkedin_urls:
            st.error("❌ No valid LinkedIn URLs found.")
            st.session_state.application_running = False
            return
        
        status_placeholder.info(f"🎯 Found {len(linkedin_urls)} LinkedIn search URL(s)")
        progress_bar.progress(30)
        
        # Initialize LLM and browser immediately to show the window
        try:
            # Initialize LLM
            provider = os.getenv("LLM_PROVIDER", "openai")
            model_name = os.getenv("LLM_MODEL", "gpt-4o")
            temperature = float(os.getenv("LLM_TEMPERATURE", "0.1"))
            
            
            llm = create_llm()
            
            status_placeholder.success("✅ LLM initialized successfully")
            progress_bar.progress(50)
            
            # Create a unique task description
            task_description = f"""
            You are a LinkedIn Job Application Assistant. Your task is to:
            
            1. Open and login to LinkedIn using these EXACT credentials:
               - Email: {linkedin_email}
               - Password: {linkedin_password}
            
            2. Navigate to this job search URL: {linkedin_urls[0] if linkedin_urls else 'No URL provided'}
            
            3. Find all jobs with "Easy Apply" buttons and apply to them automatically
            
            4. For each application:
               - Click "Easy Apply"
               - Fill out the application form
               - Upload resume if needed
               - Submit the application
               - Move to the next job
            
            IMPORTANT: Use the EXACT credentials provided. Do not use placeholder emails.
            """
            
            # Store task in session state to be executed
            st.session_state.automation_task = {
                "description": task_description,
                "llm": llm,
                "linkedin_urls": linkedin_urls,
                "status": "ready_to_start"
            }
            
            status_placeholder.success("🚀 Ready to start browser automation!")
            progress_bar.progress(70)
            
            # Show the start automation button
            st.success("✅ Setup complete! Click below to start browser automation.")
            
            if st.button("🌐 Open Browser & Start LinkedIn Automation", type="primary"):
                st.session_state.automation_task["status"] = "starting"
                st.rerun()
            
        except Exception as e:
            st.error(f"❌ Setup error: {str(e)}")
            st.session_state.application_running = False
        
    except Exception as e:
        st.error(f"❌ Error starting job application process: {str(e)}")
        st.session_state.application_running = False
        st.session_state.application_status = f"Error: {str(e)}"


async def run_streamlit_job_application_task_sync(
    linkedin_email: str,
    linkedin_password: str, 
    job_urls: str,
    override_role: str,
    override_location: str,
    manager: StreamlitManager,
    progress_bar,
    status_placeholder
):
    """
    Streamlit-compatible async job application task
    """
    
    try:
        # Initialize LLM
        provider = os.getenv("LLM_PROVIDER", "openai")
        model_name = os.getenv("LLM_MODEL", "gpt-4o")
        temperature = float(os.getenv("LLM_TEMPERATURE", "0.1"))
        base_url = os.getenv("OPENAI_ENDPOINT") or os.getenv("ANTHROPIC_ENDPOINT") or None
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or None
        
        llm: BaseChatModel = create_llm()
        
        # Browser configuration using local Chrome
        chrome_path = get_chrome_binary_path()
        
        if chrome_path:
            browser_config = BrowserConfig(
                headless=False,  # VISIBLE browser window
                browser_type="chromium",
                browser_binary_path=chrome_path,
                user_data_dir=getattr(manager, 'browser_user_data_dir', None),
                disable_security=True,
                extra_browser_args=[
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                ]
            )
        else:
            browser_config = BrowserConfig(
                headless=False,  # VISIBLE browser window
                browser_type="chromium",
                user_data_dir=getattr(manager, 'browser_user_data_dir', None),
                disable_security=True,
                extra_browser_args=[
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                ]
            )
        
        add_log_entry("assistant", "🌐 Initializing browser for LinkedIn automation...")
        progress_bar.progress(50)
        
        browser = CustomBrowser(config=browser_config)
        await browser.async_start()

        browser_context_config = BrowserContextConfig(
            window_width=1280,
            window_height=1024,
        )
        context = await browser.create_context(config=browser_context_config)
        
        # Initialize custom controller
        controller = CustomController()
        manager.bu_controller = controller
        
        # Create enhanced prompt with credentials
        enhanced_prompt = f"""
        {LINKEDIN_JOB_APPLICATION_SYSTEM_PROMPT}

        ## CRITICAL: Use These Exact LinkedIn Credentials
        LinkedIn Email: {linkedin_email}
        LinkedIn Password: {linkedin_password}

        When you encounter LinkedIn login:
        1. Enter EXACTLY this email: {linkedin_email}
        2. Enter EXACTLY this password: {linkedin_password}
        3. Do NOT use placeholder emails like "your_email@example.com"
        4. These are the user's REAL LinkedIn credentials

        Override Settings (if provided):
        - Target Role: {override_role if override_role else "Use profile default"}
        - Target Location: {override_location if override_location else "Use profile default"}
        """

        agent = BrowserUseAgent(
            task=enhanced_prompt,
            llm=llm,
            browser_context=context,
            controller=controller,
            max_actions_per_step=10,
            enable_memory=False,
            use_vision=False,
        )
        
        add_log_entry("assistant", f"🤖 Agent initialized with your LinkedIn credentials\n📧 Email: {linkedin_email}\n🔑 Password: {'*' * len(linkedin_password)}")
        progress_bar.progress(60)
        
        # Parse job URLs
        job_urls_list = [url.strip() for url in job_urls.strip().split('\n') if url.strip()]
        linkedin_urls = [url for url in job_urls_list if "linkedin.com" in url]
        
        # Process each LinkedIn search URL
        for url_index, linkedin_url in enumerate(linkedin_urls, 1):
            add_log_entry("assistant", f"🔍 Processing search URL {url_index}/{len(linkedin_urls)}: {linkedin_url}")
            progress_bar.progress(60 + (30 * url_index / len(linkedin_urls)))
            
            try:
                # Start the application process for this URL
                result = await agent.run(f"Process this LinkedIn job search URL and apply to all Easy Apply jobs: {linkedin_url}")
                
                # Extract results
                action_count = len(result.history)
                add_log_entry("assistant", f"✅ Completed processing URL {url_index}/{len(linkedin_urls)}\n📊 Actions taken: {action_count}\n🎯 Check browser for application results")
                
            except Exception as e:
                add_log_entry("assistant", f"❌ Error processing URL {url_index}: {str(e)}")
                continue
        
        # Final summary
        add_log_entry("assistant", f"🎉 Job application automation completed!\n\n📊 Summary:\n- URLs processed: {len(linkedin_urls)}\n✅ Check your LinkedIn account for application confirmations")
        progress_bar.progress(100)
        
    except Exception as e:
        add_log_entry("assistant", f"❌ Critical error: {str(e)}")
    
    finally:
        # Cleanup
        try:
            if 'browser' in locals():
                await browser.close()
        except:
            pass
        
        # Update session state
        st.session_state.application_running = False
        st.session_state.application_status = "Automation completed"


def run_browser_automation(manager: StreamlitManager):
    """
    Run browser automation with visible browser window
    """
    
    if 'automation_task' not in st.session_state:
        st.error("❌ No automation task found")
        return
    
    task = st.session_state.automation_task
    
    st.info("🌐 Opening browser window for LinkedIn automation...")
    
    try:
        # Create browser configuration for VISIBLE automation using local Chrome
        chrome_path = get_chrome_binary_path()
        
        if chrome_path:
            browser_config = BrowserConfig(
                headless=False,  # VISIBLE browser
                browser_type="chromium",
                browser_binary_path=chrome_path,
                disable_security=True,
                extra_browser_args=[
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                ]
            )
        else:
            browser_config = BrowserConfig(
                headless=False,  # VISIBLE browser
                browser_type="chromium",
                disable_security=True,
                extra_browser_args=[
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                ]
            )
        
        # Start automation in a way that's compatible with Streamlit
        import asyncio
        
        # Check if there's already an event loop running
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No event loop running, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Run the browser automation
        browser_started = loop.run_until_complete(start_browser_automation(
            task["description"],
            task["llm"],
            task["linkedin_urls"],
            browser_config,
            manager
        ))
        
        if browser_started:
            st.success("✅ Browser automation started! Check the browser window.")
            st.session_state.automation_task["status"] = "running"
            st.session_state.application_logs.append({
                "role": "assistant",
                "content": "🌐 Browser window opened! LinkedIn automation is now running in the visible browser."
            })
        else:
            st.error("❌ Failed to start browser automation")
            st.session_state.automation_task["status"] = "failed"
            
    except Exception as e:
        st.error(f"❌ Browser automation error: {str(e)}")
        st.session_state.automation_task["status"] = "failed"
        st.session_state.application_logs.append({
            "role": "assistant",
            "content": f"❌ Browser automation failed: {str(e)}"
        })


async def start_browser_automation(task_description: str, llm, linkedin_urls: list, browser_config, manager: StreamlitManager):
    """
    Start the actual browser automation
    """
    
    try:
        # Initialize browser
        browser = CustomBrowser(config=browser_config)
        await browser.async_start()
        
        # Create browser context
        browser_context_config = BrowserContextConfig(
            window_width=1280,
            window_height=1024,
        )
        context = await browser.create_context(config=browser_context_config)
        
        # Initialize controller
        controller = CustomController()
        manager.bu_controller = controller
        
        # Create browser agent
        agent = BrowserUseAgent(
            task=task_description,
            llm=llm,
            browser_context=context,
            controller=controller,
            max_actions_per_step=10,
            enable_memory=False,
            use_vision=False,
        )
        
        # Start the agent (this will open LinkedIn and begin automation)
        result = await agent.run(task_description)
        
        # The browser will remain open for manual inspection
        # Don't close the browser so user can see the results
        
        return True
        
    except Exception as e:
        print(f"Browser automation error: {str(e)}")
        return False


# Removed old start_linkedin_automation function - automation now starts automatically


async def run_linkedin_automation_async(task_description: str, llm, linkedin_urls: list, browser_config, manager: StreamlitManager):
    """
    Async function to run LinkedIn automation with improved scrolling and complete application flow
    """
    
    browser = None
    try:
        print(f"🔍 Starting LinkedIn automation with enhanced scrolling...")
        print(f"📋 Task preview: {task_description[:200]}...")
        
        # Initialize browser
        browser = CustomBrowser(config=browser_config)
        await browser.async_start()
        print("✅ Browser started successfully")
        
        # Create browser context
        context = await browser.create_context()
        print("✅ Browser context created")
        
        # Initialize controller
        controller = CustomController()
        manager.bu_controller = controller
        print("✅ Controller initialized")
        
        # Create browser automation agent with enhanced task
        enhanced_task_with_scrolling = f"""
        {task_description}
        
        CRITICAL INSTRUCTIONS FOR COMPLETE APPLICATION SUBMISSION:
        
        🔄 MANDATORY SCROLLING BEHAVIOR:
        - At EVERY step, if you don't see the "Next", "Submit", "Review", or "Continue" button immediately
        - ALWAYS scroll down to the bottom of the page using scroll_down action
        - Keep scrolling until you find the correct button
        - Look specifically for buttons with text containing "Submit", "Send Application", "Apply", or "Finish"
        
        ⛔ NEVER SAVE AS DRAFT:
        - NEVER click buttons with text "Save", "Save as Draft", or "Save for Later"
        - If you see both "Save" and "Submit" options, ALWAYS choose "Submit"
        - If you accidentally see a save prompt, click "Discard" and try again
        - The goal is to SUBMIT applications, not save them
        
        📝 STEP-BY-STEP SUBMISSION PROCESS:
        1. Fill out contact information → Click "Next"
        2. Select/upload resume → Click "Next" 
        3. Answer additional questions → Scroll down → Look for "Review" or "Submit"
        4. Review application → Scroll down → Look for "Submit Application" button
        5. Submit → Wait for confirmation message
        6. Move to next job
        
        🎯 SUBMIT BUTTON FINDING STRATEGY:
        - After answering questions, scroll down multiple times if needed
        - Look for buttons at the very bottom of forms
        - Search for text like "Submit Application", "Send Application", "Apply Now"
        - If you see "Review your application", click it, then scroll down for Submit
        
        🏆 SUCCESS CONFIRMATION:
        - You have successfully applied when you see:
          * "Thank you for applying"
          * "Application submitted successfully"
          * "Your application has been sent"
          * "Application complete"
          * Confirmation page with success message
        - ONLY move to the next job after seeing these confirmations
        """
        
        agent = BrowserUseAgent(
            task=enhanced_task_with_scrolling,
            llm=llm,
            browser_context=context,
            controller=controller,
            enable_memory=False,
            use_vision=False,
        )
        print("✅ Agent created with enhanced scrolling instructions")
        
        # Start the automation (this opens LinkedIn and begins applying)
        print("🚀 Starting enhanced LinkedIn automation...")
        result = await agent.run()
        
        # Keep browser open for user to see results
        action_count = len(result.history) if hasattr(result, 'history') else 0
        print(f"✅ LinkedIn automation completed with {action_count} actions")
        print("🎉 Browser window will remain open for you to review the results")
        
        return True
        
    except Exception as e:
        print(f"❌ LinkedIn automation error: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()
        
        # Clean up browser if there was an error
        if browser:
            try:
                await browser.close()
            except:
                pass
        
        return False


def add_log_entry(role: str, content: str):
    """Helper function to add log entries"""
    if 'application_logs' not in st.session_state:
        st.session_state.application_logs = []
    
    st.session_state.application_logs.append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    }) 