import streamlit as st
import json
import os
from typing import Dict, Any
from src.webui.streamlit_manager import StreamlitManager

def create_profile_settings_page(manager: StreamlitManager):
    """Create the profile settings page in Streamlit"""
    
    st.markdown("## 👤 Profile Settings")
    st.markdown("Configure your professional profile for job applications.")
    
    # Load existing profile data
    profile_data = manager.profile_data
    
    # Personal Information Section
    st.markdown("### 📋 Personal Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        first_name = st.text_input(
            "First Name",
            value=profile_data.get("personal", {}).get("first_name", ""),
            key="profile_first_name"
        )
        
        email = st.text_input(
            "Email",
            value=profile_data.get("personal", {}).get("email", ""),
            key="profile_email"
        )
        
        city = st.text_input(
            "City",
            value=profile_data.get("personal", {}).get("city", ""),
            key="profile_city"
        )
    
    with col2:
        last_name = st.text_input(
            "Last Name",
            value=profile_data.get("personal", {}).get("last_name", ""),
            key="profile_last_name"
        )
        
        phone = st.text_input(
            "Phone",
            value=profile_data.get("personal", {}).get("phone", ""),
            key="profile_phone"
        )
        
        state = st.text_input(
            "State",
            value=profile_data.get("personal", {}).get("state", ""),
            key="profile_state"
        )
    
    # Add address fields
    col3, col4 = st.columns(2)
    
    with col3:
        address = st.text_input(
            "Street Address",
            value=profile_data.get("personal", {}).get("address", ""),
            key="profile_address"
        )
        
        zip_code = st.text_input(
            "ZIP Code",
            value=profile_data.get("personal", {}).get("zip_code", ""),
            key="profile_zip_code"
        )
    
    with col4:
        country = st.text_input(
            "Country",
            value=profile_data.get("personal", {}).get("country", ""),
            key="profile_country"
        )
        
        linkedin_profile = st.text_input(
            "LinkedIn Profile URL",
            value=profile_data.get("personal", {}).get("linkedin_profile", ""),
            key="profile_linkedin"
        )

    # Professional Information Section
    st.markdown("### 💼 Professional Information")
    
    current_position = st.text_input(
        "Current Position",
        value=profile_data.get("professional", {}).get("current_position", ""),
        key="profile_current_position"
    )
    
    col5, col6 = st.columns(2)
    
    with col5:
        current_company = st.text_input(
            "Current Company",
            value=profile_data.get("professional", {}).get("current_company", ""),
            key="profile_current_company"
        )
        
        experience_years = st.number_input(
            "Years of Experience",
            min_value=0,
            max_value=50,
            value=profile_data.get("professional", {}).get("experience_years", 0),
            key="profile_experience_years"
        )
    
    with col6:
        industry = st.text_input(
            "Industry",
            value=profile_data.get("professional", {}).get("industry", ""),
            key="profile_industry"
        )
        
        current_salary = st.number_input(
            "Current Salary ($)",
            min_value=0,
            value=profile_data.get("professional", {}).get("current_salary", 0),
            step=1000,
            key="profile_current_salary"
        )
    
    skills = st.text_area(
        "Skills (comma-separated)",
        value=", ".join(profile_data.get("professional", {}).get("skills", [])),
        height=100,
        key="profile_skills"
    )
    
    # Education Section
    st.markdown("### 🎓 Education")
    
    col7, col8 = st.columns(2)
    
    with col7:
        education_level = st.selectbox(
            "Highest Education Level",
            ["High School", "Associate's Degree", "Bachelor's Degree", "Master's Degree", "PhD", "Other"],
            index=0,
            key="profile_education_level"
        )
        
        degree_field = st.text_input(
            "Field of Study",
            value=profile_data.get("education", {}).get("degree_field", ""),
            key="profile_degree_field"
        )
    
    with col8:
        university = st.text_input(
            "University/School",
            value=profile_data.get("education", {}).get("university", ""),
            key="profile_university"
        )
        
        graduation_year = st.number_input(
            "Graduation Year",
            min_value=1950,
            max_value=2030,
            value=profile_data.get("education", {}).get("graduation_year", 2020),
            key="profile_graduation_year"
        )
    
    # Work Experience Section
    st.markdown("### 💼 Work Experience")
    
    work_experience = st.text_area(
        "Previous Work Experience (describe your key roles and achievements)",
        value=profile_data.get("professional", {}).get("work_experience", ""),
        height=150,
        key="profile_work_experience"
    )
    
    # Work Preferences Section
    st.markdown("### 🎯 Work Preferences")
    
    col3, col4 = st.columns(2)
    
    with col3:
        work_authorization = st.selectbox(
            "Work Authorization",
            ["US Citizen", "Green Card", "H1B", "F1 OPT", "Other"],
            index=0,
            key="profile_work_auth"
        )
        
        salary_min = st.number_input(
            "Minimum Salary ($)",
            min_value=0,
            value=profile_data.get("preferences", {}).get("salary_min", 0),
            step=1000,
            key="profile_salary_min"
        )
    
    with col4:
        availability = st.selectbox(
            "Availability",
            ["Immediately", "2 weeks", "1 month", "2 months", "3+ months"],
            key="profile_availability"
        )
        
        remote_preference = st.selectbox(
            "Remote Work Preference",
            ["Remote", "Hybrid", "On-site", "No preference"],
            key="profile_remote"
        )
    
    # Additional preferences
    col9, col10 = st.columns(2)
    
    with col9:
        willing_to_relocate = st.selectbox(
            "Willing to Relocate",
            ["Yes", "No", "Maybe"],
            key="profile_relocate"
        )
        
        security_clearance = st.selectbox(
            "Security Clearance",
            ["None", "Public Trust", "Secret", "Top Secret", "Other"],
            key="profile_clearance"
        )
    
    with col10:
        visa_sponsorship = st.selectbox(
            "Need Visa Sponsorship",
            ["No", "Yes", "In the future"],
            key="profile_visa"
        )
        
        notice_period = st.selectbox(
            "Notice Period",
            ["Immediately", "1 week", "2 weeks", "1 month", "2 months", "3+ months"],
            key="profile_notice"
        )
    
    # EEO Information Section (Optional)
    st.markdown("### 📊 EEO Information (Optional)")
    st.markdown("*This information is optional and used only for compliance reporting.*")
    
    col11, col12 = st.columns(2)
    
    with col11:
        gender = st.selectbox(
            "Gender",
            ["Prefer not to answer", "Male", "Female", "Non-binary", "Other"],
            key="profile_gender"
        )
        
        ethnicity = st.selectbox(
            "Ethnicity",
            ["Prefer not to answer", "White", "Black or African American", "Hispanic or Latino", 
             "Asian", "American Indian or Alaska Native", "Native Hawaiian or Pacific Islander", "Two or more races"],
            key="profile_ethnicity"
        )
    
    with col12:
        veteran_status = st.selectbox(
            "Veteran Status",
            ["Prefer not to answer", "Not a veteran", "Veteran", "Disabled veteran"],
            key="profile_veteran"
        )
        
        disability_status = st.selectbox(
            "Disability Status",
            ["Prefer not to answer", "No disability", "Yes, I have a disability"],
            key="profile_disability"
        )
    
    # Cover Letter Section
    st.markdown("### 📝 Cover Letter Template")
    
    cover_letter = st.text_area(
        "Cover Letter Template (use {company} and {position} as placeholders)",
        value=profile_data.get("documents", {}).get("cover_letter_template", ""),
        height=200,
        placeholder="Dear Hiring Manager,\n\nI am writing to express my interest in the {position} role at {company}...",
        key="profile_cover_letter"
    )
    
    # Resume Upload Section
    st.markdown("### 📄 Documents")
    
    uploaded_resume = st.file_uploader(
        "Upload Resume",
        type=['pdf', 'doc', 'docx'],
        help="Upload your resume file",
        key="profile_resume_upload"
    )
    
    if uploaded_resume:
        # Save uploaded file
        os.makedirs("data/documents", exist_ok=True)
        resume_path = f"data/documents/{uploaded_resume.name}"
        with open(resume_path, "wb") as f:
            f.write(uploaded_resume.getbuffer())
        st.success(f"✅ Resume uploaded successfully: {uploaded_resume.name}")
    
    # Save Profile Button
    if st.button("💾 Save Profile", type="primary"):
        # Compile profile data
        updated_profile = {
            "personal": {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "phone": phone,
                "city": city,
                "state": state,
                "address": address,
                "zip_code": zip_code,
                "country": country,
                "linkedin_profile": linkedin_profile
            },
            "professional": {
                "current_position": current_position,
                "current_company": current_company,
                "industry": industry,
                "current_salary": current_salary,
                "experience_years": experience_years,
                "work_experience": work_experience,
                "skills": [skill.strip() for skill in skills.split(",") if skill.strip()]
            },
            "education": {
                "education_level": education_level,
                "degree_field": degree_field,
                "university": university,
                "graduation_year": graduation_year
            },
            "preferences": {
                "work_authorization": work_authorization,
                "salary_min": salary_min,
                "availability": availability,
                "remote_preference": remote_preference,
                "willing_to_relocate": willing_to_relocate,
                "security_clearance": security_clearance,
                "visa_sponsorship": visa_sponsorship,
                "notice_period": notice_period
            },
            "eeo_information": {
                "gender": gender,
                "ethnicity": ethnicity,
                "veteran_status": veteran_status,
                "disability_status": disability_status
            }
        }
        
        # Always include documents section
        updated_profile["documents"] = {
            "cover_letter_template": cover_letter
        }
        
        if uploaded_resume:
            updated_profile["documents"].update({
                "resume_path": resume_path,
                "resume_name": uploaded_resume.name
            })
        
        # Save to manager
        manager.profile_data = updated_profile
        manager.save_settings("profile.json", updated_profile)
        # Save to file
        
        
        st.success("✅ Profile saved successfully!")
        st.rerun()
    
    # Display current profile summary
    if profile_data:
        st.markdown("### 📊 Current Profile Summary")
        with st.expander("View Profile Data"):
            st.json(profile_data) 