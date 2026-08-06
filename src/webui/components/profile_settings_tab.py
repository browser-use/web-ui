import os
import json
import logging
from datetime import datetime
import gradio as gr
from gradio.components import Component
from typing import Dict, Any

from src.webui.webui_manager import WebuiManager

logger = logging.getLogger(__name__)

PROFILE_FILE = "./data/profile/profile.json"

def load_profile():
    """Load the user's profile from file"""
    try:
        if os.path.exists(PROFILE_FILE):
            with open(PROFILE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # Return default empty profile structure
            return {
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
    except Exception as e:
        logger.error(f"Error loading profile: {e}")
        return {}

def save_profile(profile_data):
    """Save the user's profile to file"""
    try:
        os.makedirs(os.path.dirname(PROFILE_FILE), exist_ok=True)
        with open(PROFILE_FILE, 'w', encoding='utf-8') as f:
            json.dump(profile_data, f, indent=2, ensure_ascii=False)
        return True, "Profile saved successfully!"
    except Exception as e:
        logger.error(f"Error saving profile: {e}")
        return False, f"Error saving profile: {str(e)}"

async def save_profile_handler(
    full_name, email, phone, address, linkedin_url, portfolio_url,
    current_job_title, current_company, current_start_date, current_end_date, current_work_description,
    prev_job_1_title, prev_job_1_company, prev_job_1_start, prev_job_1_end, prev_job_1_description,
    prev_job_2_title, prev_job_2_company, prev_job_2_start, prev_job_2_end, prev_job_2_description,
    prev_job_3_title, prev_job_3_company, prev_job_3_start, prev_job_3_end, prev_job_3_description,
    years_experience, skills_text, education_text,
    target_roles_text, target_locations_text, salary_min, work_authorization, visa_status, 
    availability, remote_preference, race_ethnicity, gender, veteran_status, disability_status, 
    resume_file, cover_letter_template
):
    """Handle saving profile data from the UI"""
    try:
        # Parse skills, education, target roles and locations from text
        skills = [skill.strip() for skill in skills_text.split('\n') if skill.strip()]
        education = [edu.strip() for edu in education_text.split('\n') if edu.strip()]
        target_roles = [role.strip() for role in target_roles_text.split('\n') if role.strip()]
        target_locations = [loc.strip() for loc in target_locations_text.split('\n') if loc.strip()]
        
        # Build previous positions array (only include if title and company are provided)
        previous_positions = []
        
        # Previous Job 1
        if prev_job_1_title.strip() and prev_job_1_company.strip():
            previous_positions.append({
                "job_title": prev_job_1_title.strip(),
                "company": prev_job_1_company.strip(),
                "start_date": prev_job_1_start.strip(),
                "end_date": prev_job_1_end.strip(),
                "work_description": prev_job_1_description.strip()
            })
        
        # Previous Job 2
        if prev_job_2_title.strip() and prev_job_2_company.strip():
            previous_positions.append({
                "job_title": prev_job_2_title.strip(),
                "company": prev_job_2_company.strip(),
                "start_date": prev_job_2_start.strip(),
                "end_date": prev_job_2_end.strip(),
                "work_description": prev_job_2_description.strip()
            })
        
        # Previous Job 3
        if prev_job_3_title.strip() and prev_job_3_company.strip():
            previous_positions.append({
                "job_title": prev_job_3_title.strip(),
                "company": prev_job_3_company.strip(),
                "start_date": prev_job_3_start.strip(),
                "end_date": prev_job_3_end.strip(),
                "work_description": prev_job_3_description.strip()
            })

        # Handle resume file upload
        resume_path = ""
        if resume_file:
            resume_dir = "./data/profile/documents"
            os.makedirs(resume_dir, exist_ok=True)
            resume_filename = os.path.basename(resume_file.name)
            resume_path = os.path.join(resume_dir, resume_filename)
            
            # Copy the uploaded file
            import shutil
            shutil.copy2(resume_file.name, resume_path)

        profile_data = {
            "personal": {
                "full_name": full_name,
                "email": email,
                "phone": phone,
                "address": address,
                "linkedin_url": linkedin_url,
                "portfolio_url": portfolio_url
            },
            "professional": {
                "current_position": {
                    "job_title": current_job_title,
                    "company": current_company,
                    "start_date": current_start_date,
                    "end_date": current_end_date,
                    "work_description": current_work_description
                },
                "previous_positions": previous_positions,
                "years_experience": years_experience,
                "skills": skills,
                "education": education
            },
            "preferences": {
                "target_roles": target_roles,
                "target_locations": target_locations,
                "salary_min": salary_min,
                "work_authorization": work_authorization,
                "visa_status": visa_status,
                "availability": availability,
                "remote_preference": remote_preference
            },
            "eeo_information": {
                "race_ethnicity": race_ethnicity,
                "gender": gender,
                "veteran_status": veteran_status,
                "disability_status": disability_status,
                "voluntary_disclosure": True
            },
            "documents": {
                "resume_path": resume_path,
                "cover_letter_template": cover_letter_template
            },
            "last_updated": datetime.now().isoformat()
        }

        success, message = save_profile(profile_data)
        if success:
            return gr.update(value=message, visible=True)
        else:
            return gr.update(value=message, visible=True)

    except Exception as e:
        logger.error(f"Error in save_profile_handler: {e}")
        return gr.update(value=f"Error saving profile: {str(e)}", visible=True)

def create_profile_settings_tab(webui_manager: WebuiManager):
    """
    Creates a profile settings tab for job application management.
    """
    tab_components = {}
    
    # Load existing profile (will be empty after clearing demo data)
    profile = load_profile()
    personal = profile.get("personal", {})
    professional = profile.get("professional", {})
    current_position = professional.get("current_position", {})
    previous_positions = professional.get("previous_positions", [])
    preferences = profile.get("preferences", {})
    eeo_info = profile.get("eeo_information", {})
    documents = profile.get("documents", {})

    with gr.Column():
        gr.Markdown("## 👤 Personal Information")
        
        with gr.Row():
            full_name = gr.Textbox(
                label="Full Name",
                value=personal.get("full_name", ""),
                placeholder="Your full name as it appears on your resume"
            )
            email = gr.Textbox(
                label="Email",
                value=personal.get("email", ""),
                placeholder="your.email@example.com"
            )
        
        with gr.Row():
            phone = gr.Textbox(
                label="Phone Number",
                value=personal.get("phone", ""),
                placeholder="+1 (555) 123-4567"
            )
            address = gr.Textbox(
                label="Address",
                value=personal.get("address", ""),
                placeholder="City, State, Country"
            )
        
        with gr.Row():
            linkedin_url = gr.Textbox(
                label="LinkedIn URL",
                value=personal.get("linkedin_url", ""),
                placeholder="https://linkedin.com/in/yourprofile"
            )
            portfolio_url = gr.Textbox(
                label="Portfolio/Website URL",
                value=personal.get("portfolio_url", ""),
                placeholder="https://yourportfolio.com"
            )

        gr.Markdown("## 💼 Professional Information")
        
        # Current Position Section
        gr.Markdown("### Current Position")
        with gr.Row():
            current_job_title = gr.Textbox(
                label="Job Title",
                value=current_position.get("job_title", ""),
                placeholder="Software Engineer, Data Scientist, etc."
            )
            current_company = gr.Textbox(
                label="Company",
                value=current_position.get("company", ""),
                placeholder="Company Name"
            )
        
        with gr.Row():
            current_start_date = gr.Textbox(
                label="Start Date",
                value=current_position.get("start_date", ""),
                placeholder="January 2022"
            )
            current_end_date = gr.Textbox(
                label="End Date",
                value=current_position.get("end_date", "Present"),
                placeholder="Present or December 2023"
            )
        
        current_work_description = gr.Textbox(
            label="Work Description",
            lines=4,
            value=current_position.get("work_description", ""),
            placeholder="Describe your key responsibilities, achievements, and technologies used in this role..."
        )
        
        # Previous Positions Section
        gr.Markdown("### Previous Work Experience")
        
        # Get previous positions data (pad with empty dicts if needed)
        prev_positions = previous_positions + [{} for _ in range(3 - len(previous_positions))]
        
        # Previous Job 1
        gr.Markdown("#### Previous Position 1")
        with gr.Row():
            prev_job_1_title = gr.Textbox(
                label="Job Title",
                value=prev_positions[0].get("job_title", ""),
                placeholder="Previous job title"
            )
            prev_job_1_company = gr.Textbox(
                label="Company",
                value=prev_positions[0].get("company", ""),
                placeholder="Company Name"
            )
        
        with gr.Row():
            prev_job_1_start = gr.Textbox(
                label="Start Date",
                value=prev_positions[0].get("start_date", ""),
                placeholder="January 2020"
            )
            prev_job_1_end = gr.Textbox(
                label="End Date",
                value=prev_positions[0].get("end_date", ""),
                placeholder="December 2021"
            )
        
        prev_job_1_description = gr.Textbox(
            label="Work Description",
            lines=3,
            value=prev_positions[0].get("work_description", ""),
            placeholder="Describe your responsibilities and achievements in this role..."
        )
        
        # Previous Job 2
        gr.Markdown("#### Previous Position 2")
        with gr.Row():
            prev_job_2_title = gr.Textbox(
                label="Job Title",
                value=prev_positions[1].get("job_title", ""),
                placeholder="Previous job title"
            )
            prev_job_2_company = gr.Textbox(
                label="Company",
                value=prev_positions[1].get("company", ""),
                placeholder="Company Name"
            )
        
        with gr.Row():
            prev_job_2_start = gr.Textbox(
                label="Start Date",
                value=prev_positions[1].get("start_date", ""),
                placeholder="January 2018"
            )
            prev_job_2_end = gr.Textbox(
                label="End Date",
                value=prev_positions[1].get("end_date", ""),
                placeholder="December 2019"
            )
        
        prev_job_2_description = gr.Textbox(
            label="Work Description",
            lines=3,
            value=prev_positions[1].get("work_description", ""),
            placeholder="Describe your responsibilities and achievements in this role..."
        )
        
        # Previous Job 3
        gr.Markdown("#### Previous Position 3")
        with gr.Row():
            prev_job_3_title = gr.Textbox(
                label="Job Title",
                value=prev_positions[2].get("job_title", ""),
                placeholder="Previous job title"
            )
            prev_job_3_company = gr.Textbox(
                label="Company",
                value=prev_positions[2].get("company", ""),
                placeholder="Company Name"
            )
        
        with gr.Row():
            prev_job_3_start = gr.Textbox(
                label="Start Date",
                value=prev_positions[2].get("start_date", ""),
                placeholder="January 2016"
            )
            prev_job_3_end = gr.Textbox(
                label="End Date",
                value=prev_positions[2].get("end_date", ""),
                placeholder="December 2017"
            )
        
        prev_job_3_description = gr.Textbox(
            label="Work Description",
            lines=3,
            value=prev_positions[2].get("work_description", ""),
            placeholder="Describe your responsibilities and achievements in this role..."
        )
        
        # General Professional Information
        gr.Markdown("### General Professional Information")
        years_experience = gr.Number(
            label="Total Years of Experience",
            value=professional.get("years_experience", 0),
            minimum=0,
            maximum=50
        )
        
        skills_text = gr.Textbox(
            label="Skills (one per line)",
            lines=5,
            value='\n'.join(professional.get("skills", [])),
            placeholder="Python\nJavaScript\nReact\nMachine Learning\nProject Management"
        )
        
        education_text = gr.Textbox(
            label="Education (one per line)",
            lines=3,
            value='\n'.join(professional.get("education", [])),
            placeholder="Bachelor's in Computer Science - University Name (2020)\nMaster's in Data Science - University Name (2022)"
        )

        gr.Markdown("## 🎯 Job Preferences")
        
        target_roles_text = gr.Textbox(
            label="Target Job Roles (one per line)",
            lines=3,
            value='\n'.join(preferences.get("target_roles", [])),
            placeholder="Software Engineer\nFull Stack Developer\nData Scientist"
        )
        
        target_locations_text = gr.Textbox(
            label="Target Locations (one per line)",
            lines=3,
            value='\n'.join(preferences.get("target_locations", [])),
            placeholder="San Francisco, CA\nNew York, NY\nRemote"
        )
        
        with gr.Row():
            salary_min = gr.Number(
                label="Minimum Salary ($)",
                value=preferences.get("salary_min", 0),
                minimum=0
            )
            work_authorization = gr.Dropdown(
                label="Work Authorization",
                choices=["US Citizen", "Green Card", "H1B", "OPT", "CPT", "Need Sponsorship", "Other"],
                value=preferences.get("work_authorization", None),
                allow_custom_value=True
            )
        
        with gr.Row():
            visa_status = gr.Textbox(
                label="Visa Status/Notes",
                value=preferences.get("visa_status", ""),
                placeholder="Additional visa information if needed"
            )
            availability = gr.Textbox(
                label="Availability",
                value=preferences.get("availability", ""),
                placeholder="Immediately, 2 weeks notice, etc."
            )
        
        remote_preference = gr.Dropdown(
            label="Remote Work Preference",
            choices=["Remote", "Hybrid", "On-site", "No Preference"],
            value=preferences.get("remote_preference", None),
            allow_custom_value=True
        )

        # EEO Information Section
        gr.Markdown("## 📊 Equal Employment Opportunity Information")
        gr.Markdown("*This information is voluntary and used for compliance reporting. It will not affect hiring decisions.*")
        
        with gr.Row():
            race_ethnicity = gr.Dropdown(
                label="Race/Ethnicity (Optional)",
                choices=[
                    "Prefer not to answer",
                    "American Indian or Alaska Native", 
                    "Asian",
                    "Black or African American",
                    "Hispanic or Latino",
                    "Native Hawaiian or Other Pacific Islander",
                    "White",
                    "Two or More Races"
                ],
                value=eeo_info.get("race_ethnicity", "Prefer not to answer"),
                allow_custom_value=False
            )
            gender = gr.Dropdown(
                label="Gender (Optional)",
                choices=[
                    "Prefer not to answer",
                    "Male",
                    "Female", 
                    "Non-binary",
                    "Other"
                ],
                value=eeo_info.get("gender", "Prefer not to answer"),
                allow_custom_value=False
            )
        
        with gr.Row():
            veteran_status = gr.Dropdown(
                label="Veteran Status (Optional)",
                choices=[
                    "Prefer not to answer",
                    "I am not a protected veteran",
                    "I identify as one or more of the classifications of protected veteran",
                    "Recently separated veteran",
                    "Armed forces service medal veteran",
                    "Disabled veteran",
                    "Other protected veteran"
                ],
                value=eeo_info.get("veteran_status", "Prefer not to answer"),
                allow_custom_value=False
            )
            disability_status = gr.Dropdown(
                label="Disability Status (Optional)", 
                choices=[
                    "Prefer not to answer",
                    "No, I do not have a disability",
                    "Yes, I have a disability (or previously had a disability)",
                    "I don't wish to answer"
                ],
                value=eeo_info.get("disability_status", "Prefer not to answer"),
                allow_custom_value=False
            )

        gr.Markdown("## 📄 Documents")
        
        resume_file = gr.File(
            label="Upload Resume",
            file_types=[".pdf", ".doc", ".docx"],
            type="filepath"
        )
        
        if documents.get("resume_path"):
            gr.Markdown(f"**Current Resume:** `{documents.get('resume_path')}`")
        
        cover_letter_template = gr.Textbox(
            label="Cover Letter Template",
            lines=6,
            value=documents.get("cover_letter_template", ""),
            placeholder="Dear Hiring Manager,\n\nI am writing to express my interest in the [POSITION] role at [COMPANY]...\n\n[Your customizable cover letter template]"
        )

        # Save button and status
        with gr.Row():
            save_button = gr.Button("💾 Save Profile", variant="primary", scale=1)
            clear_button = gr.Button("🗑️ Clear All", variant="secondary", scale=1)
        
        status_message = gr.Textbox(
            label="Status",
            interactive=False,
            visible=False
        )

    # Store components
    tab_components.update({
        "full_name": full_name,
        "email": email,
        "phone": phone,
        "address": address,
        "linkedin_url": linkedin_url,
        "portfolio_url": portfolio_url,
        "current_job_title": current_job_title,
        "current_company": current_company,
        "current_start_date": current_start_date,
        "current_end_date": current_end_date,
        "current_work_description": current_work_description,
        "prev_job_1_title": prev_job_1_title,
        "prev_job_1_company": prev_job_1_company,
        "prev_job_1_start": prev_job_1_start,
        "prev_job_1_end": prev_job_1_end,
        "prev_job_1_description": prev_job_1_description,
        "prev_job_2_title": prev_job_2_title,
        "prev_job_2_company": prev_job_2_company,
        "prev_job_2_start": prev_job_2_start,
        "prev_job_2_end": prev_job_2_end,
        "prev_job_2_description": prev_job_2_description,
        "prev_job_3_title": prev_job_3_title,
        "prev_job_3_company": prev_job_3_company,
        "prev_job_3_start": prev_job_3_start,
        "prev_job_3_end": prev_job_3_end,
        "prev_job_3_description": prev_job_3_description,
        "years_experience": years_experience,
        "skills_text": skills_text,
        "education_text": education_text,
        "target_roles_text": target_roles_text,
        "target_locations_text": target_locations_text,
        "salary_min": salary_min,
        "work_authorization": work_authorization,
        "visa_status": visa_status,
        "availability": availability,
        "remote_preference": remote_preference,
        "race_ethnicity": race_ethnicity,
        "gender": gender,
        "veteran_status": veteran_status,
        "disability_status": disability_status,
        "resume_file": resume_file,
        "cover_letter_template": cover_letter_template,
        "save_button": save_button,
        "clear_button": clear_button,
        "status_message": status_message
    })

    webui_manager.add_components("profile_settings", tab_components)

    # Event handlers
    save_button.click(
        fn=save_profile_handler,
        inputs=[
            full_name, email, phone, address, linkedin_url, portfolio_url,
            current_job_title, current_company, current_start_date, current_end_date, current_work_description,
            prev_job_1_title, prev_job_1_company, prev_job_1_start, prev_job_1_end, prev_job_1_description,
            prev_job_2_title, prev_job_2_company, prev_job_2_start, prev_job_2_end, prev_job_2_description,
            prev_job_3_title, prev_job_3_company, prev_job_3_start, prev_job_3_end, prev_job_3_description,
            years_experience, skills_text, education_text,
            target_roles_text, target_locations_text, salary_min, work_authorization, visa_status, availability, remote_preference,
            race_ethnicity, gender, veteran_status, disability_status,
            resume_file, cover_letter_template
        ],
        outputs=[status_message]
    )

    def clear_all_fields():
        """Clear all form fields"""
        return [
            "",  # full_name
            "",  # email
            "",  # phone
            "",  # address
            "",  # linkedin_url
            "",  # portfolio_url
            "",  # current_job_title
            "",  # current_company
            "",  # current_start_date
            "Present",  # current_end_date
            "",  # current_work_description
            "",  # prev_job_1_title
            "",  # prev_job_1_company
            "",  # prev_job_1_start
            "",  # prev_job_1_end
            "",  # prev_job_1_description
            "",  # prev_job_2_title
            "",  # prev_job_2_company
            "",  # prev_job_2_start
            "",  # prev_job_2_end
            "",  # prev_job_2_description
            "",  # prev_job_3_title
            "",  # prev_job_3_company
            "",  # prev_job_3_start
            "",  # prev_job_3_end
            "",  # prev_job_3_description
            0,   # years_experience
            "",  # skills_text
            "",  # education_text
            "",  # target_roles_text
            "",  # target_locations_text
            0,   # salary_min
            None,  # work_authorization
            "",  # visa_status
            "",  # availability
            None,  # remote_preference
            "Prefer not to answer",  # race_ethnicity
            "Prefer not to answer",  # gender
            "Prefer not to answer",  # veteran_status
            "Prefer not to answer",  # disability_status
            None,  # resume_file
            "",  # cover_letter_template
            gr.update(value="All fields cleared", visible=True)  # status_message
        ]

    clear_button.click(
        fn=clear_all_fields,
        inputs=[],
        outputs=[
            full_name, email, phone, address, linkedin_url, portfolio_url,
            current_job_title, current_company, current_start_date, current_end_date, current_work_description,
            prev_job_1_title, prev_job_1_company, prev_job_1_start, prev_job_1_end, prev_job_1_description,
            prev_job_2_title, prev_job_2_company, prev_job_2_start, prev_job_2_end, prev_job_2_description,
            prev_job_3_title, prev_job_3_company, prev_job_3_start, prev_job_3_end, prev_job_3_description,
            years_experience, skills_text, education_text,
            target_roles_text, target_locations_text, salary_min, work_authorization, visa_status, availability, remote_preference,
            race_ethnicity, gender, veteran_status, disability_status,
            resume_file, cover_letter_template, status_message
        ]
    ) 