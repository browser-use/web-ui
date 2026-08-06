#!/usr/bin/env python3
"""
Simple runner script for ApplyAgent.AI (Streamlit Version)
"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    """Run the Streamlit application"""
    
    # Ensure we're in the project directory
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Check if .env file exists
    env_file = project_root / ".env"
    if not env_file.exists():
        print("⚠️  Warning: .env file not found!")
        print("📝 Please create a .env file with your configuration:")
        print("   OPENAI_API_KEY=your_openai_api_key_here")
        print("   LLM_PROVIDER=openai")
        print("   LLM_MODEL=gpt-4o")
        print("   LLM_TEMPERATURE=0.1")
        print()
    
    # Run Streamlit
    print("🚀 Starting ApplyAgent.AI (Streamlit)...")
    print("🌐 The application will open in your browser at http://localhost:8501")
    print("🛑 Press Ctrl+C to stop the application")
    print()
    
    try:
        subprocess.run([
            sys.executable, 
            "-m", 
            "streamlit", 
            "run", 
            "streamlit_app.py",
            "--server.port=8501",
            "--server.headless=false",
            "--browser.gatherUsageStats=false"
        ], check=True)
    except KeyboardInterrupt:
        print("\n🛑 Application stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running Streamlit: {e}")
        print("💡 Make sure Streamlit is installed: pip install streamlit")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main() 