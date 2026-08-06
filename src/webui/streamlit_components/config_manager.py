import streamlit as st
import json
import os
from datetime import datetime
from src.webui.streamlit_manager import StreamlitManager

def create_config_manager_page(manager: StreamlitManager):
    """Create the config manager page in Streamlit"""
    
    st.markdown("## 📁 Settings & Configuration")
    st.markdown("Manage your application settings, import/export configurations, and view system information.")
    
    # LLM Configuration
    st.markdown("### 🤖 LLM Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        llm_provider = st.selectbox(
            "LLM Provider",
            ["openai", "anthropic", "azure", "ollama"],
            help="Choose your AI model provider",
            key="llm_provider"
        )
        
        model_name = st.text_input(
            "Model Name",
            value=os.getenv("LLM_MODEL", "gpt-4o"),
            help="Specify the model to use",
            key="llm_model"
        )
    
    with col2:
        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=2.0,
            value=float(os.getenv("LLM_TEMPERATURE", "0.1")),
            step=0.1,
            help="Control randomness in AI responses",
            key="llm_temperature"
        )
        
        max_tokens = st.number_input(
            "Max Tokens",
            min_value=100,
            max_value=8000,
            value=int(os.getenv("LLM_MAX_TOKENS", "2000")),
            help="Maximum tokens per response",
            key="llm_max_tokens"
        )
    
    # API Keys Section
    st.markdown("### 🔑 API Keys")
    st.info("⚠️ API keys are loaded from environment variables. Update your .env file to change them.")
    
    col3, col4 = st.columns(2)
    
    with col3:
        openai_key_status = "✅ Set" if os.getenv("OPENAI_API_KEY") else "❌ Not Set"
        st.write(f"**OpenAI API Key:** {openai_key_status}")
        
        if os.getenv("OPENAI_ENDPOINT"):
            st.write(f"**OpenAI Endpoint:** {os.getenv('OPENAI_ENDPOINT')[:50]}...")
    
    with col4:
        anthropic_key_status = "✅ Set" if os.getenv("ANTHROPIC_API_KEY") else "❌ Not Set"
        st.write(f"**Anthropic API Key:** {anthropic_key_status}")
        
        if os.getenv("ANTHROPIC_ENDPOINT"):
            st.write(f"**Anthropic Endpoint:** {os.getenv('ANTHROPIC_ENDPOINT')[:50]}...")
    
    # Configuration Export/Import
    st.markdown("### 📤 Configuration Management")
    
    col5, col6 = st.columns(2)
    
    with col5:
        st.markdown("#### Export Configuration")
        
        if st.button("📦 Export All Settings"):
            config_data = {
                "profile": manager.profile_data,
                "browser_config": manager.browser_config,
                "llm_config": {
                    "provider": llm_provider,
                    "model": model_name,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                },
                "export_timestamp": datetime.now().isoformat()
            }
            
            config_json = json.dumps(config_data, indent=2)
            
            st.download_button(
                label="💾 Download Configuration",
                data=config_json,
                file_name=f"job_agent_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    
    with col6:
        st.markdown("#### Import Configuration")
        
        uploaded_config = st.file_uploader(
            "Upload Configuration File",
            type=['json'],
            help="Upload a previously exported configuration file",
            key="config_upload"
        )
        
        if uploaded_config:
            try:
                config_data = json.load(uploaded_config)
                
                if st.button("🔄 Import Configuration"):
                    # Import profile data
                    if "profile" in config_data:
                        manager.profile_data = config_data["profile"]
                    
                    # Import browser config
                    if "browser_config" in config_data:
                        manager.browser_config = config_data["browser_config"]
                    
                    st.success("✅ Configuration imported successfully!")
                    st.rerun()
                
            except Exception as e:
                st.error(f"❌ Error importing configuration: {str(e)}")
    
    # System Information
    st.markdown("### 🖥️ System Information")
    
    with st.expander("View System Details"):
        col7, col8 = st.columns(2)
        
        with col7:
            st.write("**Environment Variables:**")
            env_vars = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "LLM_PROVIDER", "LLM_MODEL", "LLM_TEMPERATURE"]
            for var in env_vars:
                value = os.getenv(var, "Not Set")
                if "API_KEY" in var and value != "Not Set":
                    value = f"{'*' * 20}...{value[-4:]}" if len(value) > 10 else "Set"
                st.write(f"- {var}: {value}")
        
        with col8:
            st.write("**File System:**")
            directories = ["data/profile", "data/applications", "data/documents", "tmp/webui_settings"]
            for directory in directories:
                exists = "✅" if os.path.exists(directory) else "❌"
                st.write(f"- {directory}: {exists}")
    
    # Data Management
    st.markdown("### 🗂️ Data Management")
    
    col9, col10, col11 = st.columns(3)
    
    with col9:
        if st.button("🧹 Clear Browser Data"):
            # Clear browser cache and cookies
            browser_data_dir = "./tmp/browser_data"
            if os.path.exists(browser_data_dir):
                import shutil
                shutil.rmtree(browser_data_dir)
                st.success("✅ Browser data cleared!")
            else:
                st.info("No browser data to clear.")
    
    with col10:
        if st.button("🔄 Reset All Settings"):
            if st.checkbox("⚠️ I understand this will reset all settings", key="confirm_reset"):
                manager.profile_data = {}
                manager.browser_config = {}
                st.success("✅ All settings reset!")
                st.rerun()
    
    with col11:
        if st.button("📊 View Session State"):
            with st.expander("Current Session State"):
                st.json({
                    "profile_data": manager.profile_data,
                    "browser_config": manager.browser_config,
                    "application_status": st.session_state.get("application_status", ""),
                    "session_keys": list(st.session_state.keys())
                })
    
    # Application Version Info
    st.markdown("### ℹ️ Application Information")
    
    st.info("""
    **ApplyAgent.AI - Streamlit Version**
    
    🤖 **Features:**
    - Intelligent automated LinkedIn job applications
    - Smart profile management with MCP-style tools
    - Advanced browser automation with visual feedback
    - Comprehensive application history tracking
    - Easy configuration import/export
    
    📝 **Note:** This is the Streamlit version of ApplyAgent.AI. 
    Make sure your environment variables are properly configured in your `.env` file.
    """)
    
    # Quick Actions
    st.markdown("### ⚡ Quick Actions")
    
    col12, col13, col14 = st.columns(3)
    
    with col12:
        if st.button("🔍 Test LLM Connection"):
            try:
                from src.utils import llm_provider
                provider = os.getenv("LLM_PROVIDER", "openai")
                model = os.getenv("LLM_MODEL", "gpt-4o")
                
                llm = llm_provider.get_llm_model(
                    provider=provider,
                    model_name=model,
                    temperature=0.1
                )
                st.success(f"✅ LLM connection successful! Using {provider}/{model}")
            except Exception as e:
                st.error(f"❌ LLM connection failed: {str(e)}")
    
    with col13:
        if st.button("📁 Open Data Directory"):
            st.info("Data is stored in: ./data/")
            if os.path.exists("./data"):
                files = os.listdir("./data")
                st.write("**Files:**", files)
            else:
                st.warning("Data directory not found.")
    
    with col14:
        if st.button("🔐 Check Environment"):
            required_vars = ["OPENAI_API_KEY", "LLM_PROVIDER", "LLM_MODEL"]
            missing_vars = [var for var in required_vars if not os.getenv(var)]
            
            if missing_vars:
                st.warning(f"⚠️ Missing environment variables: {', '.join(missing_vars)}")
            else:
                st.success("✅ All required environment variables are set!") 