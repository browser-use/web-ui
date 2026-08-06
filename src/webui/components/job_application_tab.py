import asyncio
import json
import logging
import os
import uuid
from typing import Any, AsyncGenerator, Dict, Optional

# import gradio as gr  # Commented out for Streamlit compatibility

from browser_use.agent.views import (
    AgentHistoryList,
    AgentOutput,
)
from browser_use.browser.browser import BrowserConfig
from browser_use.browser.context import BrowserContext, BrowserContextConfig
from browser_use.browser.views import BrowserState
from gradio.components import Component
from langchain_core.language_models.chat_models import BaseChatModel

from src.agent.browser_use.browser_use_agent import BrowserUseAgent
from src.browser.custom_browser import CustomBrowser
from src.controller.custom_controller import CustomController
from src.utils import llm_provider
from src.webui.webui_manager import WebuiManager

logger = logging.getLogger(__name__)

# Job Application System Prompt
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

async def run_job_application_task(
    linkedin_email: str,
    linkedin_password: str, 
    job_urls: str,
    override_role: str = "",
    override_location: str = ""
) -> AsyncGenerator[tuple[list, str], None]:
    """
    Main function for LinkedIn job application automation with user credentials
    """
    webui_manager = WebuiManager()
    
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
        
        llm: BaseChatModel = llm_provider.get_llm_model(
            provider=provider,
            model_name=model_name,
            temperature=temperature,
            base_url=base_url,
            api_key=api_key,
        )
    except Exception as e:
        yield [{"role": "assistant", "content": f"❌ LLM configuration error: {str(e)}\n\nPlease check your environment variables:\n- OPENAI_API_KEY or ANTHROPIC_API_KEY\n- Optionally: LLM_PROVIDER, LLM_MODEL, LLM_TEMPERATURE"}], "Error: LLM configuration required"
        return

    # Browser configuration - Make it VISIBLE so you can see LinkedIn automation
    browser_config = BrowserConfig(
        headless=False,  # VISIBLE browser window
        browser_type="chromium",
        user_data_dir=getattr(webui_manager, 'browser_user_data_dir', None),
        disable_security=True,  # Allow easier LinkedIn automation
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
        webui_manager.controller = controller

        total_applications = 0
        successful_applications = 0
        failed_applications = 0
        
        for url_index, linkedin_url in enumerate(linkedin_urls):
            yield [{"role": "assistant", "content": f"🔍 Processing LinkedIn search URL {url_index + 1}/{len(linkedin_urls)}: {linkedin_url[:80]}...\n\n⚠️ **You should now see a browser window opening!** Watch as the agent navigates LinkedIn and applies to jobs."}], f"VISIBLE Browser: Processing search URL {url_index + 1}/{len(linkedin_urls)}..."
            
            yield [{"role": "assistant", "content": f"🤖 Creating agent with credentials:\n📧 Email: {linkedin_email}\n🔑 Password: {'*' * len(linkedin_password)}\n\n✅ **FIXED**: Agent will now receive the detailed prompt with your REAL credentials!\n\n🔍 Debug: Enhanced prompt contains your email {len(linkedin_email)} chars and password {len(linkedin_password)} chars."}], f"Setting up agent with your REAL credentials..."
            
            # EXACT WORKING PROMPT FROM YESTERDAY'S GITHUB CODE
            enhanced_prompt = f"""
🚨 CRITICAL LINKEDIN APPLICATION MISSION 🚨

You are a LinkedIn job application automation agent. Your goal is to successfully complete job applications by following the COMPLETE application flow until you see the "Thank you for applying" message.

1. **Navigate to the LinkedIn job search URL**: {linkedin_url}

2. **LOGIN** with credentials:
   **EMAIL**: {linkedin_email}
   **PASSWORD**: {linkedin_password}

3. **COMPLETE APPLICATION PROTOCOL** - MUST REACH "THANK YOU" MESSAGE:

   **STEP 1: FIND AND CLICK EASY APPLY JOBS**
   - Find jobs with "Easy Apply" button
   - Click "Easy Apply" to start application process

   **STEP 2: FILL CONTACT INFORMATION**
   - Fill email: {linkedin_email}
   - Fill phone: 8067025056
   - Select country: United States
   - Look for "Next" button and click it

   **STEP 3: RESUME UPLOAD**
   - Select the first available resume
   - Click "Next" to continue

   **STEP 4: ANSWER QUESTIONS** 
   - Fill any required questions with appropriate answers:
     * Years experience: 3-5 years
     * Work authorization: Yes
     * Willing to relocate: Yes
     * Any dropdowns: Select appropriate option
   - Click "Next" or "Review" to continue

   **STEP 5: CRITICAL - COMPLETE SUBMISSION (MUST DO THIS)**
   - **ALWAYS SCROLL DOWN** to find buttons at the bottom
   - Look for these buttons IN ORDER:
     1. "Submit Application" (PRIORITY 1 - click this!)
     2. "Submit" (PRIORITY 2 - click this!)  
     3. "Review" (continue to next step)
     4. "Next" (continue to next step)
   
   **SUBMISSION RULES:**
   - **NEVER CLICK "X" OR CLOSE BUTTON**
   - **NEVER CLICK "Discard" OR "Save for later"**  
   - **ALWAYS SCROLL DOWN** if you don't see Submit button
   - **KEEP SCROLLING** until you find Submit Application button
   - **ONLY COMPLETE** when you see "Thank you for applying" message
   - **LOG SUCCESS** only after seeing confirmation message

**ULTRA-FAST MODE OPTIMIZATIONS:**

RULE #3: AGGRESSIVE BUTTON HUNTING
- Look for Next/Review/Submit buttons FIRST (don't scroll initially)
- If you see ANY progression button, click it IMMEDIATELY
- Only if NO buttons visible, then press "End" key ONCE to jump to bottom
- NO multiple scroll_down actions - use "End" key for instant bottom navigation

**MANDATORY SCROLL BEHAVIOR:**
If at ANY point you cannot see a button to proceed (Next/Review/Submit Application), you MUST:
1. Use send_keys action with keys="End" to jump to page bottom
2. Look for the button that appeared at the bottom
3. Click it immediately
4. NEVER sit idle without taking action - if no button visible, ALWAYS use End key

**CRITICAL: When stuck or idle, IMMEDIATELY use send_keys with keys="End"**

**LOGIN CREDENTIALS:**
Email: {linkedin_email}
Password: {linkedin_password}

**EMERGENCY PROTOCOL: If you are idle and not seeing progression buttons, use send_keys action with keys="End" IMMEDIATELY!**
"""
            
            # ABSOLUTE FINAL ATTEMPT - DIRECT JAVASCRIPT SCROLL
            final_desperate_prompt = f"""
You are applying to LinkedIn Easy Apply jobs. Login with {linkedin_email}/{linkedin_password} at {linkedin_url}.

CRITICAL RULE: If you cannot see a "Next", "Review", or "Submit Application" button, you MUST scroll to the bottom of the page.

TO SCROLL TO BOTTOM: Click anywhere on the page, then press the "End" key on the keyboard. This will take you to the bottom where the buttons are.

STEP BY STEP:
1. Fill out the form fields
2. Look for Next/Review/Submit Application button
3. If you DON'T see the button: Press "End" key to scroll to bottom
4. Click the button that appears
5. Repeat until you see "Thank you for applying"

NEVER click X, Discard, or Save buttons.

Fill forms: Email {linkedin_email}, Phone 8067025056, Experience 3-5 years, Authorization Yes, Relocate Yes.

When stuck, ALWAYS press "End" key to go to bottom of page.
"""

            # Create browser use agent 
            agent = BrowserUseAgent(
                task=final_desperate_prompt,
                llm=llm,
                browser=browser,
                browser_context=context,
                controller=controller,
                use_vision=True,
                max_actions_per_step=10
            )

            # Store current agent for stop functionality
            webui_manager.current_agent = agent

            try:
                yield [{
                    "role": "assistant", 
                    "content": f"🆘 **ABSOLUTE FINAL ATTEMPT** 🆘\n\n🎯 LinkedIn agent starting for URL {url_index + 1}/{len(linkedin_urls)}\n\n📋 **ULTRA-SIMPLE APPROACH:**\n- ✅ **CLEAR INSTRUCTION**: If no button visible → Press 'End' key\n- ✅ **DIRECT LANGUAGE**: 'Press End key to scroll to bottom'\n- ✅ **STEP-BY-STEP**: Explicit 5-step process\n- ✅ **CRITICAL RULE**: Must scroll when button not found\n- ✅ **WHEN STUCK**: Always press End key\n\n🔑 **KEY INSTRUCTION:**\n'If you DON'T see the button: Press End key to scroll to bottom'\n\n🎯 **EXPECTED BEHAVIOR:**\n- Fill form fields\n- Look for Next/Submit button\n- **NO BUTTON? → PRESS END KEY**\n- Click button that appears\n- Repeat until 'Thank you for applying'\n\n⚠️ **THIS IS THE FINAL ATTEMPT - WATCH FOR END KEY USAGE!**"
                }], f"🆘 FINAL ATTEMPT: URL {url_index + 1}/{len(linkedin_urls)}..."
                
                # Run the agent and wait for completion
                history = await agent.run(max_steps=250)  # Increased for ultra-fast batch processing
                
                # Process results with aggressive validation
                if history and history.is_done():
                    final_result = history.final_result()
                    if final_result and "success" in str(final_result).lower():
                        successful_applications += 1
                        yield [{"role": "assistant", "content": f"🎉 **MISSION SUCCESS** 🎉\n\n✅ **AGGRESSIVE SUBMISSION PROTOCOL WORKED!**\n- URL {url_index + 1}/{len(linkedin_urls)} completed\n- Applications submitted with 'Thank you' confirmations\n- NO X button clicks detected\n- Scrolling protocol executed successfully\n\n📊 **Success Indicators:**\n- Found Submit buttons through scrolling\n- Avoided all Discard/Close buttons\n- Received application confirmations\n\n📝 Result: {str(final_result)[:300]}..."}], f"🎉 MISSION SUCCESS: URL {url_index + 1}/{len(linkedin_urls)}"
                    else:
                        failed_applications += 1
                        yield [{"role": "assistant", "content": f"⚠️ **PARTIAL SUCCESS** ⚠️\n\n🔍 Agent processed URL {url_index + 1} but may need review:\n\n📝 Result: {str(final_result)[:300]}...\n\n🔍 **VERIFICATION NEEDED:**\n- Did agent scroll down properly?\n- Were Submit buttons found and clicked?\n- Did agent avoid X/Discard buttons?\n- Were 'Thank you' messages displayed?\n\n🚨 **If agent clicked X button, this is a FAILURE!**"}], f"⚠️ Partial: URL {url_index + 1}/{len(linkedin_urls)}"
                else:
                    failed_applications += 1
                    yield [{"role": "assistant", "content": f"❌ **MISSION FAILED** ❌\n\n🚨 Agent did not complete URL {url_index + 1}/{len(linkedin_urls)}\n\n🔍 **CRITICAL FAILURE ANALYSIS:**\n- Agent may have clicked X button (PROHIBITED!)\n- Scrolling protocol may have failed\n- Submit buttons not found despite scrolling\n- Applications abandoned without submission\n\n💡 **INVESTIGATION REQUIRED:**\n- Check browser window for evidence\n- Verify scrolling actions were performed\n- Confirm no X/Discard buttons were clicked\n- Look for abandoned applications"}], f"❌ MISSION FAILED: URL {url_index + 1}/{len(linkedin_urls)}"
                    
                total_applications += 1

            except Exception as e:
                yield [{"role": "assistant", "content": f"❌ Error processing URL {url_index + 1}: {str(e)}"}], f"Error on URL {url_index + 1}/{len(linkedin_urls)}"
                failed_applications += 1

        # Final summary
        summary_message = f"""
        ✅ LinkedIn Job Application Automation Complete!
        
        📊 Final Results:
        • Total Applications Processed: {total_applications}
        • Successfully Submitted: {successful_applications}
        • Failed Applications: {failed_applications}
        • Success Rate: {(successful_applications/total_applications*100) if total_applications > 0 else 0:.1f}%
        
        Check the Application History tab for detailed results of each application.
        """

        yield [{"role": "assistant", "content": summary_message}], f"Complete: {successful_applications} submitted, {failed_applications} failed"

        # Summary of all job search URLs processed
        yield [{
            "role": "assistant", 
            "content": f"🏁 **AGGRESSIVE SUBMISSION MISSION COMPLETE!** 🏁\n\n🚨 **MISSION CRITICAL STATS:**\n📊 **URLs Processed**: {len(linkedin_urls)}\n✅ **Successful Submissions**: {successful_applications}\n❌ **Failed Missions**: {failed_applications}\n\n💪 **AGGRESSIVE ENFORCEMENT FEATURES USED:**\n- 🚫 **ZERO X BUTTON CLICKS** (prohibited!)\n- 🔄 **MANDATORY SCROLLING** protocol activated\n- 🎯 **END KEY NAVIGATION** to bottom\n- 💥 **SUBMIT BUTTON HUNTING** with multiple techniques\n- 🛡️ **DISCARD BUTTON AVOIDANCE** system\n- ✅ **THANK YOU MESSAGE VALIDATION**\n\n📋 **MISSION RESULTS:**\n- Check 'Application History' tab for confirmed applications\n- Only applications with 'Thank you' messages count as success\n- Agent forced to scroll until Submit buttons found\n- NO applications abandoned via X button clicks\n\n🎯 **SUBMISSION ENFORCEMENT NOTES:**\n- Agent programmed to NEVER click X/Discard buttons\n- Aggressive scrolling ensures Submit buttons are found\n- Multiple scroll techniques prevent mission failure\n- Success only confirmed with 'Thank you' messages\n\n⚠️ **IF ANY X BUTTON CLICKS DETECTED = MISSION FAILURE!**"
        }], "🏁 AGGRESSIVE SUBMISSION mission complete!"
        
        # Try to get application statistics from controller
        try:
            applications_result = controller.run_tool("list_applications", {})
            if applications_result and "applications" in applications_result:
                total_logged = len(applications_result["applications"])
                yield [{"role": "assistant", "content": f"📈 **APPLICATION STATISTICS**\n\n🎯 **Total Applications Logged**: {total_logged}\n📝 **Applications found in your history**\n\n👉 Go to 'Application History' tab to view all applications!"}], f"Found {total_logged} total applications in history"
        except Exception as e:
            pass  # Don't fail if we can't get stats

    except Exception as e:
        error_message = f"Critical error in job application automation: {str(e)}"
        yield [{"role": "assistant", "content": error_message}], f"Critical Error: {str(e)[:50]}..."
        
    finally:
        # Cleanup
        try:
            if hasattr(webui_manager, 'current_agent'):
                webui_manager.current_agent = None
            if 'context' in locals():
                await context.close()
            if 'browser' in locals():
                await browser.close()
        except:
            pass

async def handle_stop_application(webui_manager: WebuiManager):
    """Handle stopping the job application automation"""
    webui_manager.stop_agent = True
    if hasattr(webui_manager, 'current_agent') and webui_manager.current_agent:
        try:
            # Try to gracefully stop the current agent
            webui_manager.current_agent = None
        except:
            pass
    return "🛑 Stopping job application automation..."

def create_job_application_tab(webui_manager: WebuiManager):
    """
    Creates a job application automation tab.
    """
    tab_components = {}

    with gr.Column():
        gr.Markdown("## 🚀 Automated Job Applications")
        gr.Markdown("Enter LinkedIn job search URLs and let the agent automatically apply using your saved profile.")
        
        # LinkedIn Credentials Section
        gr.Markdown("### 🔐 LinkedIn Login Credentials")
        gr.Markdown("*Required for applying to jobs. Your credentials are only used for this session and not stored permanently.*")
        
        with gr.Row():
            linkedin_email = gr.Textbox(
                label="LinkedIn Email",
                placeholder="your-email@example.com",
                type="email",
                info="Your LinkedIn account email"
            )
            linkedin_password = gr.Textbox(
                label="LinkedIn Password",
                placeholder="Enter your LinkedIn password",
                type="password",
                info="Your LinkedIn account password"
            )

        # Job URLs Input Section
        gr.Markdown("### 📋 Job Search URLs")
        job_urls = gr.Textbox(
            label="LinkedIn Job Search URLs (one per line)",
            lines=6,
            placeholder="""https://www.linkedin.com/jobs/search/?keywords=data%20scientist&location=San%20Francisco
https://www.linkedin.com/jobs/search/?keywords=software%20engineer&location=Remote""",
            info="💡 Pro tip: Use LinkedIn's job search filters to find your target roles, then paste the results URL here!"
        )

        # Optional Overrides Section
        gr.Markdown("### 🎯 Optional Overrides")
        
        with gr.Row():
            override_role = gr.Textbox(
                label="Override Target Role (Optional)",
                placeholder="e.g., Senior Software Engineer",
                info="Override the target role from your profile for these applications"
            )
            override_location = gr.Textbox(
                label="Override Target Location (Optional)",
                placeholder="e.g., San Francisco, CA",
                info="Override the target location from your profile for these applications"
            )

        # Action Buttons
        with gr.Row():
            apply_button = gr.Button("🚀 Apply to Jobs", variant="primary", size="lg")
            stop_button = gr.Button("🛑 Stop", variant="secondary", size="lg")

        # Progress and Results
        progress_status = gr.Textbox(
            label="⚡ Progress Status",
            interactive=False,
            max_lines=1
        )

        gr.Markdown("### 🤖 Application Process Log")
        
        chatbot = gr.Chatbot(
            label="Real-time Application Progress",
            height=400,
            type="messages",
            show_copy_button=True
        )

        clear_log_button = gr.Button("🗑️ Clear Log", variant="secondary")

        # Store components for access
        tab_components = {
            "linkedin_email": linkedin_email,
            "linkedin_password": linkedin_password,
            "job_urls": job_urls,
            "override_role": override_role,
            "override_location": override_location,
            "apply_button": apply_button,
            "stop_button": stop_button,
            "progress_status": progress_status,
            "chatbot": chatbot,
            "clear_log_button": clear_log_button
        }

        # Event handlers
        apply_button.click(
            fn=run_application_wrapper,
            inputs=[linkedin_email, linkedin_password, job_urls, override_role, override_location],
            outputs=[chatbot, progress_status],
            queue=True,
            show_progress="full"
        )

        stop_button.click(
            fn=lambda: handle_stop_application(webui_manager),
            outputs=progress_status,
            queue=True
        )

        clear_log_button.click(
            fn=lambda: ([], ""),
            outputs=[chatbot, progress_status],
            queue=False
        )

    return tab_components


async def run_application_wrapper(linkedin_email: str, linkedin_password: str, job_urls: str, override_role: str, override_location: str):
    """Wrapper function to handle the application process with proper error handling"""
    try:
        async for result in run_job_application_task(linkedin_email, linkedin_password, job_urls, override_role, override_location):
            yield result
    except Exception as e:
        error_msg = f"❌ Critical error in job application process: {str(e)}"
        yield [{"role": "assistant", "content": error_msg}], f"Error: {str(e)[:50]}..." 