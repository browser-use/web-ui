import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime
from src.webui.streamlit_manager import StreamlitManager

def create_application_history_page(manager: StreamlitManager):
    """Create the application history page in Streamlit"""
    
    st.markdown("## 📋 Application History")
    st.markdown("View and manage your job application history.")
    
    # Load application history
    applications_file = "data/applications/applications.json"
    applications = []
    
    if os.path.exists(applications_file):
        try:
            with open(applications_file, 'r') as f:
                applications = json.load(f)
        except Exception as e:
            st.error(f"Error loading applications: {str(e)}")
    
    if not applications:
        st.info("📭 No job applications found yet. Start applying to jobs to see your history here!")
        return
    
    # Statistics
    st.markdown("### 📊 Application Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_apps = len(applications)
    successful_apps = len([app for app in applications if app.get("status") == "submitted"])
    failed_apps = len([app for app in applications if app.get("status") == "failed"])
    pending_apps = len([app for app in applications if app.get("status") == "pending"])
    
    with col1:
        st.metric("Total Applications", total_apps)
    
    with col2:
        st.metric("Successful", successful_apps)
    
    with col3:
        st.metric("Failed", failed_apps)
    
    with col4:
        st.metric("Pending", pending_apps)
    
    # Filter options
    st.markdown("### 🔍 Filter Applications")
    
    col5, col6 = st.columns(2)
    
    with col5:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "submitted", "failed", "pending", "skipped"],
            key="status_filter"
        )
    
    with col6:
        company_filter = st.text_input(
            "Filter by Company",
            placeholder="Enter company name...",
            key="company_filter"
        )
    
    # Filter applications
    filtered_apps = applications
    
    if status_filter != "All":
        filtered_apps = [app for app in filtered_apps if app.get("status") == status_filter]
    
    if company_filter:
        filtered_apps = [app for app in filtered_apps if company_filter.lower() in app.get("company", "").lower()]
    
    # Display applications
    st.markdown("### 📋 Application List")
    
    if filtered_apps:
        # Convert to DataFrame for better display
        df_data = []
        for app in filtered_apps:
            df_data.append({
                "Date": app.get("applied_date", ""),
                "Job Title": app.get("job_title", ""),
                "Company": app.get("company", ""),
                "Status": app.get("status", ""),
                "Location": app.get("location", ""),
                "Notes": app.get("notes", "")[:100] + "..." if len(app.get("notes", "")) > 100 else app.get("notes", "")
            })
        
        df = pd.DataFrame(df_data)
        
        # Display as interactive table
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )
        
        # Show detailed view for selected application
        if len(df) > 0:
            st.markdown("### 📄 Application Details")
            
            # Select application to view
            app_index = st.selectbox(
                "Select application to view details",
                range(len(filtered_apps)),
                format_func=lambda x: f"{filtered_apps[x].get('job_title', 'Unknown')} at {filtered_apps[x].get('company', 'Unknown')}",
                key="app_detail_selector"
            )
            
            selected_app = filtered_apps[app_index]
            
            with st.expander("View Full Application Details", expanded=True):
                col7, col8 = st.columns(2)
                
                with col7:
                    st.write(f"**Job Title:** {selected_app.get('job_title', 'N/A')}")
                    st.write(f"**Company:** {selected_app.get('company', 'N/A')}")
                    st.write(f"**Status:** {selected_app.get('status', 'N/A')}")
                    st.write(f"**Applied Date:** {selected_app.get('applied_date', 'N/A')}")
                
                with col8:
                    st.write(f"**Location:** {selected_app.get('location', 'N/A')}")
                    st.write(f"**Job URL:** {selected_app.get('job_url', 'N/A')}")
                    if selected_app.get('salary_range'):
                        st.write(f"**Salary Range:** {selected_app.get('salary_range', 'N/A')}")
                
                if selected_app.get('notes'):
                    st.write("**Notes:**")
                    st.write(selected_app.get('notes', ''))
                
                if selected_app.get('application_data'):
                    st.write("**Application Data:**")
                    st.json(selected_app.get('application_data', {}))
    
    else:
        st.info("No applications match your current filters.")
    
    # Export functionality
    st.markdown("### 📤 Export Data")
    
    col9, col10 = st.columns(2)
    
    with col9:
        if st.button("📊 Export to CSV"):
            if applications:
                df_export = pd.DataFrame(applications)
                csv = df_export.to_csv(index=False)
                st.download_button(
                    label="💾 Download CSV",
                    data=csv,
                    file_name=f"job_applications_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No applications to export!")
    
    with col10:
        if st.button("🗑️ Clear All History"):
            if st.checkbox("⚠️ I understand this will delete all application history", key="confirm_delete"):
                if os.path.exists(applications_file):
                    os.remove(applications_file)
                    st.success("✅ Application history cleared!")
                    st.rerun()
                else:
                    st.warning("No application history file found.") 