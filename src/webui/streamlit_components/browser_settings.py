import streamlit as st
from src.webui.streamlit_manager import StreamlitManager

def create_browser_settings_page(manager: StreamlitManager):
    """Create the browser settings page in Streamlit"""
    
    st.markdown("## 🌐 Browser Settings")
    st.markdown("Configure browser automation settings for job applications.")
    
    # Browser Configuration
    st.markdown("### 🔧 Browser Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        headless = st.checkbox(
            "Headless Mode",
            value=manager.browser_config.get("headless", False),
            help="Run browser in background (faster but not visible)",
            key="browser_headless"
        )
        
        browser_type = st.selectbox(
            "Browser Type",
            ["chromium", "firefox", "webkit"],
            index=0,
            help="Choose the browser engine",
            key="browser_type"
        )
    
    with col2:
        window_width = st.number_input(
            "Window Width",
            min_value=800,
            max_value=2560,
            value=manager.browser_config.get("window_width", 1280),
            step=100,
            key="browser_width"
        )
        
        window_height = st.number_input(
            "Window Height",
            min_value=600,
            max_value=1440,
            value=manager.browser_config.get("window_height", 1024),
            step=100,
            key="browser_height"
        )
    
    # Automation Settings
    st.markdown("### ⚡ Automation Settings")
    
    col3, col4 = st.columns(2)
    
    with col3:
        page_load_timeout = st.number_input(
            "Page Load Timeout (seconds)",
            min_value=5,
            max_value=60,
            value=manager.browser_config.get("page_load_timeout", 30),
            help="Maximum time to wait for pages to load",
            key="browser_timeout"
        )
        
        action_delay = st.number_input(
            "Action Delay (seconds)",
            min_value=0.5,
            max_value=5.0,
            value=manager.browser_config.get("action_delay", 1.0),
            step=0.5,
            help="Delay between browser actions",
            key="browser_delay"
        )
    
    with col4:
        max_retries = st.number_input(
            "Max Retries",
            min_value=1,
            max_value=10,
            value=manager.browser_config.get("max_retries", 3),
            help="Maximum number of retries for failed actions",
            key="browser_retries"
        )
        
        enable_screenshots = st.checkbox(
            "Enable Screenshots",
            value=manager.browser_config.get("enable_screenshots", True),
            help="Take screenshots during automation for debugging",
            key="browser_screenshots"
        )
    
    # Save Settings
    if st.button("💾 Save Browser Settings", type="primary"):
        browser_config = {
            "headless": headless,
            "browser_type": browser_type,
            "window_width": window_width,
            "window_height": window_height,
            "page_load_timeout": page_load_timeout,
            "action_delay": action_delay,
            "max_retries": max_retries,
            "enable_screenshots": enable_screenshots
        }
        
        manager.browser_config = browser_config
        manager.save_settings("browser_config.json", browser_config)
        
        st.success("✅ Browser settings saved successfully!")
        st.rerun()
    
    # Current Settings Display
    if manager.browser_config:
        st.markdown("### 📊 Current Browser Settings")
        with st.expander("View Current Settings"):
            st.json(manager.browser_config) 