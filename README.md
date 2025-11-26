<img src="./assets/web-ui.png" alt="Browser Use Web UI" width="full"/>

<br/>

[![GitHub stars](https://img.shields.io/github/stars/browser-use/web-ui?style=social)](https://github.com/browser-use/web-ui/stargazers)
[![Discord](https://img.shields.io/discord/1303749220842340412?color=7289DA&label=Discord&logo=discord&logoColor=white)](https://link.browser-use.com/discord)
[![Documentation](https://img.shields.io/badge/Documentation-📕-blue)](https://docs.browser-use.com)
[![WarmShao](https://img.shields.io/twitter/follow/warmshao?style=social)](https://x.com/warmshao)

This project builds upon the foundation of the [browser-use](https://github.com/browser-use/browser-use), which is designed to make websites accessible for AI agents.

We would like to officially thank [WarmShao](https://github.com/warmshao) for his contribution to this project.

**WebUI:** is built on Gradio and supports most of `browser-use` functionalities. This UI is designed to be user-friendly and enables easy interaction with the browser agent.

**Expanded LLM Support:** We've integrated support for various Large Language Models (LLMs), including: Google, OpenAI, Azure OpenAI, Anthropic, DeepSeek, Ollama etc. And we plan to add support for even more models in the future.

**Custom Browser Support:** You can use your own browser with our tool, eliminating the need to re-login to sites or deal with other authentication challenges. This feature also supports high-definition screen recording.

**Persistent Browser Sessions:** You can choose to keep the browser window open between AI tasks, allowing you to see the complete history and state of AI interactions.

<video src="https://github.com/user-attachments/assets/56bc7080-f2e3-4367-af22-6bf2245ff6cb" controls="controls">Your browser does not support playing this video!</video>

## Installation Guide

### Option 1: Windows UV Installation (Recommended)

This guide focuses on Windows installation using UV package manager for optimal performance and modern Python development.

#### Prerequisites

- **Windows 10/11** (64-bit)
- **PowerShell 5.1+** or **PowerShell Core 7+**
- **Git** for Windows

#### Step 1: Install UV Package Manager

```powershell
# Install UV using winget (Windows Package Manager)
winget install astral-sh.uv

# Or download from: https://github.com/astral-sh/uv/releases
```

#### Step 2: Clone the Repository

```powershell
git clone https://github.com/browser-use/web-ui.git
cd web-ui
```

#### Step 3: Set Up Python Environment

```powershell
# Install Python 3.14t (free-threaded variant) for best performance
uv python install 3.14t

# Create virtual environment with Python 3.14t
uv venv --python 3.14t

# Activate the virtual environment
.\.venv\Scripts\Activate.ps1
```

> **Note:** Python 3.14t is the free-threaded variant that removes the Global Interpreter Lock (GIL) for better parallel performance. You can also use Python 3.11+ if preferred: `uv venv --python 3.11`

#### Step 4: Install Dependencies

```powershell
# Install all dependencies using UV (faster than pip)
uv sync

# Install Playwright browsers
playwright install --with-deps

# Or install specific browser
playwright install chromium --with-deps
```

#### Step 5: Configure Environment

```powershell
# Copy environment template
Copy-Item .env.example .env

# Edit .env with your API keys and settings
notepad .env
```

#### Step 6: Run the Application

```powershell
# Start the WebUI
python webui.py

# Or with custom settings
python webui.py --ip 0.0.0.0 --port 8080 --theme Ocean
```

### Option 2: Traditional pip Installation

If you prefer using pip instead of UV:

```powershell
# Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
playwright install --with-deps
```

#### Step 4: Configure Environment

1. Create a copy of the example environment file:

- Windows (Command Prompt):

```bash
copy .env.example .env
```

- macOS/Linux/Windows (PowerShell):

```bash
cp .env.example .env
```

2. Open `.env` in your preferred text editor and add your API keys and other settings

#### Step 5: Enjoy the web-ui

1. **Run the WebUI:**

    ```bash
    python webui.py --ip 127.0.0.1 --port 7788
    ```

2. **Access the WebUI:** Open your web browser and navigate to `http://127.0.0.1:7788`.
3. **Using Your Own Browser(Optional):**
    - Set `BROWSER_PATH` to the executable path of your browser and `BROWSER_USER_DATA` to the user data directory of your browser. Leave `BROWSER_USER_DATA` empty if you want to use local user data.
      - Windows

        ```env
         BROWSER_PATH="C:\Program Files\Google\Chrome\Application\chrome.exe"
         BROWSER_USER_DATA="C:\Users\YourUsername\AppData\Local\Google\Chrome\User Data"
        ```

        > Note: Replace `YourUsername` with your actual Windows username for Windows systems.
      - Mac

        ```env
         BROWSER_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
         BROWSER_USER_DATA="/Users/YourUsername/Library/Application Support/Google/Chrome"
        ```

    - Close all Chrome windows
    - Open the WebUI in a non-Chrome browser, such as Firefox or Edge. This is important because the persistent browser context will use the Chrome data when running the agent.
    - Check the "Use Own Browser" option within the Browser Settings.

### Option 3: Docker Installation (Alternative)

> **Note:** Docker installation is available but not recommended for Windows users. The UV installation above provides better performance and easier debugging on Windows.

#### Prerequisites

- Docker Desktop for Windows
- WSL2 enabled (recommended)

#### Quick Docker Setup

```powershell
# Clone repository
git clone https://github.com/browser-use/web-ui.git
cd web-ui

# Copy environment file
Copy-Item .env.example .env

# Build and run with Docker Compose
docker compose up --build
```

#### Access Points

- **Web-UI**: `http://localhost:7788`
- **VNC Viewer**: `http://localhost:6080/vnc.html` (password: "youvncpassword")

> **Windows Users**: For better performance and easier debugging, we recommend using the UV installation method above instead of Docker.

## Changelog

- [x] **2025/01/26:** Thanks to @vvincent1234. Now browser-use-webui can combine with DeepSeek-r1 to engage in deep thinking!
- [x] **2025/01/10:** Thanks to @casistack. Now we have Docker Setup option and also Support keep browser open between tasks.[Video tutorial demo](https://github.com/browser-use/web-ui/issues/1#issuecomment-2582511750).
- [x] **2025/01/06:** Thanks to @richard-devbot. A New and Well-Designed WebUI is released. [Video tutorial demo](https://github.com/warmshao/browser-use-webui/issues/1#issuecomment-2573393113).
