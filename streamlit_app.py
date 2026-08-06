import streamlit as st
from dotenv import load_dotenv
import asyncio
import os

# Load environment variables
load_dotenv()

# Configure Streamlit page
st.set_page_config(
    page_title="🤖 ApplyAgent.AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import Streamlit components
from src.webui.streamlit_components.profile_settings import create_profile_settings_page
from src.webui.streamlit_components.browser_settings import create_browser_settings_page
from src.webui.streamlit_components.job_application import create_job_application_page
from src.webui.streamlit_components.application_history import create_application_history_page
from src.webui.streamlit_components.config_manager import create_config_manager_page
from src.webui.streamlit_manager import StreamlitManager

# Fresh, Clean & Professional CSS
st.markdown("""
<style>
    /* Google Fonts Import */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* CSS Reset and Base Styling */
    * {
        box-sizing: border-box;
    }
    
    /* Clean background and base layout */
    .main > div {
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        min-height: 100vh;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
        padding: 0;
    }
    
    .main .block-container {
        background: transparent;
        padding: 2rem 1rem;
        max-width: 1200px;
        margin: 0 auto;
    }
    
    /* CUSTOM NAVIGATION - Clean button-based navigation */
    .stButton > button {
        width: 100% !important;
        margin: 0 !important;
    }
    
    /* COMPACT FORM INPUTS - Smaller size */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stNumberInput > div > div > input {
        border: 1px solid #e2e8f0 !important;
        border-radius: 8px !important;
        padding: 8px 12px !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 14px !important;
        color: #334155 !important;
        background: white !important;
        transition: all 0.2s ease !important;
        width: 100% !important;
        box-sizing: border-box !important;
        height: 36px !important;
        min-height: 36px !important;
        max-height: 36px !important;
    }
    
    /* Compact textarea */
    .stTextArea > div > div > textarea {
        height: 80px !important;
        min-height: 80px !important;
        max-height: 120px !important;
        resize: vertical !important;
    }
    
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus,
    .stNumberInput > div > div > input:focus {
        border-color: #2563eb !important;
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1) !important;
        outline: none !important;
    }
    
    .stTextInput > div > div > input::placeholder,
    .stTextArea > div > div > textarea::placeholder {
        color: #94a3b8 !important;
        font-family: 'Inter', sans-serif !important;
    }
    
    /* COMPACT SELECTBOXES - Smaller size */
    .stSelectbox > div > div > div {
        border: 1px solid #e2e8f0 !important;
        border-radius: 8px !important;
        background: white !important;
        font-family: 'Inter', sans-serif !important;
        transition: all 0.2s ease !important;
        min-height: 36px !important;
        height: 36px !important;
        padding: 0 !important;
    }
    
    .stSelectbox > div > div > div > div {
        padding: 8px 12px !important;
        min-height: 36px !important;
        height: 36px !important;
        font-size: 14px !important;
    }
    
    .stSelectbox > div > div > div:focus-within {
        border-color: #2563eb !important;
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1) !important;
    }
    
    /* COMPACT BUTTONS - Smaller size */
    .stButton > button {
        background: #2563eb !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 8px 16px !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 14px !important;
        font-weight: 600 !important;
        cursor: pointer !important;
        transition: all 0.2s ease !important;
        min-height: 36px !important;
        height: 36px !important;
    }
    
    .stButton > button:hover {
        background: #1d4ed8 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 6px rgba(37, 99, 235, 0.2) !important;
    }
    
    .stButton > button:active {
        transform: translateY(0) !important;
    }
    
    /* FORM LABELS */
    .stTextInput label,
    .stTextArea label,
    .stNumberInput label,
    .stSelectbox label {
        color: #334155 !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 500 !important;
        font-size: 14px !important;
        margin-bottom: 0.5rem !important;
    }
    
    /* TYPOGRAPHY */
    .stMarkdown {
        font-family: 'Inter', sans-serif !important;
    }
    
    .stMarkdown h1 {
        color: #0f172a !important;
        font-weight: 700 !important;
        font-size: 2rem !important;
        margin-bottom: 1rem !important;
    }
    
    .stMarkdown h2 {
        color: #1e293b !important;
        font-weight: 600 !important;
        font-size: 1.5rem !important;
        margin-bottom: 0.75rem !important;
    }
    
    .stMarkdown h3 {
        color: #334155 !important;
        font-weight: 600 !important;
        font-size: 1.25rem !important;
        margin-bottom: 0.5rem !important;
    }
    
    .stMarkdown p {
        color: #64748b !important;
        font-size: 14px !important;
        line-height: 1.6 !important;
        margin-bottom: 1rem !important;
    }
    
    /* CLEAN CONTAINERS */
    .element-container {
        background: transparent !important;
        margin-bottom: 1rem !important;
    }
    
    .stForm {
        background: transparent !important;
        border: none !important;
    }
    
    /* STATUS MESSAGES */
    .stSuccess {
        background: #f0fdf4 !important;
        border: 1px solid #bbf7d0 !important;
        color: #166534 !important;
        border-radius: 12px !important;
        padding: 1rem !important;
    }
    
    .stError {
        background: #fef2f2 !important;
        border: 1px solid #fecaca !important;
        color: #dc2626 !important;
        border-radius: 12px !important;
        padding: 1rem !important;
    }
    
    .stWarning {
        background: #fffbeb !important;
        border: 1px solid #fed7aa !important;
        color: #d97706 !important;
        border-radius: 12px !important;
        padding: 1rem !important;
    }
    
    .stInfo {
        background: #eff6ff !important;
        border: 1px solid #bfdbfe !important;
        color: #2563eb !important;
        border-radius: 12px !important;
        padding: 1rem !important;
    }
    
    /* EXPANDABLE SECTIONS */
    .streamlit-expanderHeader {
        background: white !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 12px !important;
        padding: 1rem !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 600 !important;
        color: #334155 !important;
    }
    
    .streamlit-expanderContent {
        background: white !important;
        border: 1px solid #e2e8f0 !important;
        border-top: none !important;
        border-radius: 0 0 12px 12px !important;
        padding: 1rem !important;
    }
    
    /* HIDE STREAMLIT BRANDING */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {visibility: hidden;}
    
    /* CUSTOM SCROLLBAR */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #f1f5f9;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #cbd5e1;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #94a3b8;
    }
    
    /* DATA FRAMES */
    .stDataFrame {
        border-radius: 12px !important;
        overflow: hidden !important;
        border: 1px solid #e2e8f0 !important;
    }
    
    /* ENSURE EVERYTHING IS INTERACTIVE */
    .stTextInput,
    .stTextArea,
    .stNumberInput,
    .stSelectbox,
    .stButton,
    .stCheckbox,
    .stRadio {
        position: relative !important;
        z-index: 1 !important;
        pointer-events: auto !important;
    }
    
    /* REMOVE ANY BLOCKING OVERLAYS */
    .element-container > div {
        position: relative !important;
        z-index: 1 !important;
    }
    
    .main-nav .stTabs [data-baseweb="tab"] div {
        background: none !important;
        position: static !important;
    }
</style>
""", unsafe_allow_html=True)

def main():
    """Main Streamlit application"""
    
    # Initialize session state manager
    if 'streamlit_manager' not in st.session_state:
        st.session_state.streamlit_manager = StreamlitManager()
    
    manager = st.session_state.streamlit_manager
    
    # Clean header layout
    # Main title centered at top
    st.markdown("""
    <div style="text-align: center; margin-bottom: 2rem;">
        <h1 style="font-size: 3.2rem; margin: 0; font-weight: 800; color: #2E86AB;">
            🤖 ApplyAgent.AI
        </h1>
        <p style="font-size: 1.2rem; margin: 0.5rem 0 0 0; color: #555;">
            Automatically applies to jobs based on your profile
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Subtitle on left side
    st.markdown("""
    <div style="text-align: left; margin-bottom: 2rem;">
        <h2 style="margin: 0; font-size: 1.8rem; font-weight: 700; color: #2E86AB;">
            🎯 Job Application Agent
        </h2>
        <p style="margin: 0.2rem 0 0 0; font-size: 0.9rem; color: #666;">
            Intelligent Automation System
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize current page state
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'profile'
    
    # Custom Navigation Buttons
    st.markdown("""
    <style>
    .nav-container {
        display: flex;
        gap: 8px;
        margin-bottom: 2rem;
        padding: 8px;
        background: white;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        border: 1px solid #e2e8f0;
    }
    .nav-button {
        flex: 1;
        text-align: center;
        padding: 10px 16px;
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.2s ease;
        font-weight: 500;
        font-size: 14px;
        border: none;
        background: transparent;
        color: #64748b;
    }
    .nav-button:hover {
        background: #f1f5f9;
        color: #334155;
    }
    .nav-button.active {
        background: #2563eb;
        color: white;
        font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Create navigation buttons
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        if st.button("👤 My Profile", key="nav_profile", use_container_width=True):
            st.session_state.current_page = 'profile'
    
    with col2:
        if st.button("🌐 Browser Setup", key="nav_browser", use_container_width=True):
            st.session_state.current_page = 'browser'
    
    with col3:
        if st.button("🚀 Start Applying", key="nav_apply", use_container_width=True):
            st.session_state.current_page = 'apply'
    
    with col4:
        if st.button("📊 Application History", key="nav_history", use_container_width=True):
            st.session_state.current_page = 'history'
    
    with col5:
        if st.button("⚙️ Configuration", key="nav_config", use_container_width=True):
            st.session_state.current_page = 'config'
    
    # Content area with white background
    st.markdown("""
    <div style="background: white; border-radius: 16px; padding: 2rem; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); border: 1px solid #e2e8f0; margin-top: 1rem;">
    """, unsafe_allow_html=True)
    
    # Display current page content
    if st.session_state.current_page == 'profile':
        create_profile_settings_page(manager)
    elif st.session_state.current_page == 'browser':
        create_browser_settings_page(manager)
    elif st.session_state.current_page == 'apply':
        create_job_application_page(manager)
    elif st.session_state.current_page == 'history':
        create_application_history_page(manager)
    elif st.session_state.current_page == 'config':
        create_config_manager_page(manager)
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Enhanced Footer
    st.markdown("""
    <div style="margin-top: 3rem; padding: 0 2rem;">
        <div style="height: 2px; background: linear-gradient(90deg, #667eea 0%, #764ba2 50%, #f093fb 100%); 
                    border-radius: 2px; margin-bottom: 2rem; opacity: 0.6;"></div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style="text-align: center; padding: 2.5rem 2rem; margin: 2rem 0; 
                background: rgba(255,255,255,0.9); border-radius: 25px;
                box-shadow: 0 15px 35px rgba(0,0,0,0.1); backdrop-filter: blur(20px);
                border: 1px solid rgba(255,255,255,0.3);">
        <div style="margin-bottom: 1rem;">
            <span style="font-size: 2rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                         -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                         background-clip: text; font-weight: 800;">🤖</span>
        </div>
        <p style="margin: 0; font-size: 1.1rem; font-weight: 600;
                  background: linear-gradient(135deg, #2E86AB 0%, #A23B72 100%);
                  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                  background-clip: text;">
            Made with ❤️ by <strong>ApplyAgent.AI</strong>
        </p>
        <p style="margin: 0.5rem 0 0 0; font-size: 0.95rem; color: #666; font-weight: 500;">
            🚀 Intelligent Job Application Automation Platform
        </p>
        <div style="margin-top: 1.5rem; display: flex; justify-content: center; gap: 1rem;">
            <span style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                         color: white; padding: 8px 16px; border-radius: 20px; 
                         font-size: 0.8rem; font-weight: 600; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);">
                AI Powered
            </span>
            <span style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                         color: white; padding: 8px 16px; border-radius: 20px; 
                         font-size: 0.8rem; font-weight: 600; box-shadow: 0 4px 15px rgba(240, 147, 251, 0.3);">
                Browser Automation
            </span>
            <span style="background: linear-gradient(135deg, #2E86AB 0%, #A23B72 100%);
                         color: white; padding: 8px 16px; border-radius: 20px; 
                         font-size: 0.8rem; font-weight: 600; box-shadow: 0 4px 15px rgba(46, 134, 171, 0.3);">
                Smart Application
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main() 