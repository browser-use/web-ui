# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is **Browser Use Web UI** - a fork of [browser-use/web-ui](https://github.com/browser-use/web-ui) enhanced with UV backend, Python 3.14t support, and modern dependency management. It provides a Gradio-based web interface for AI agents that can control web browsers using the [browser-use](https://github.com/browser-use/browser-use) library.

**Key Features:**

- Multi-LLM support (OpenAI, Anthropic, Google, DeepSeek, Ollama, Azure, IBM Watson, etc.)
- Custom browser integration (use your own Chrome/browser profile)
- Persistent browser sessions between AI tasks
- High-definition screen recording
- MCP (Model Context Protocol) client integration

## Development Commands

This project uses **UV** for Python package management and supports Python 3.11-3.14t (free-threaded variant).

### Environment Setup

```bash
# Install Python 3.14t (recommended) or 3.11+
uv python install 3.14t

# Create virtual environment
uv venv --python 3.14t

# Activate environment
# Windows CMD:
.venv\Scripts\activate
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
uv sync

# Install Playwright browsers
playwright install --with-deps
# Or specific browser:
playwright install chromium --with-deps
```

### Running the Application

```bash
# Basic run (default: 127.0.0.1:7788)
python webui.py

# With custom IP/port
python webui.py --ip 0.0.0.0 --port 8080

# With different theme
python webui.py --theme Ocean
# Available themes: Default, Soft, Monochrome, Glass, Origin, Citrus, Ocean, Base
```

### Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_agents.py

# Run with verbose output
pytest -v

# Run with async mode
pytest --asyncio-mode=auto
```

### Code Quality

```bash
# Format code
ruff format .

# Lint code
ruff check .

# Fix linting issues automatically
ruff check . --fix

# Type checking (using ty - Astral's Rust-based type checker)
# Note: ty is in alpha (0.0.1a23), expect potential bugs
ty check .
```

### Docker Development

```bash
# Build and run with Docker Compose
docker compose up --build

# For ARM64 systems (Apple Silicon)
TARGETPLATFORM=linux/arm64 docker compose up --build

# Access web UI: http://localhost:7788
# Access VNC viewer: http://localhost:6080/vnc.html
```

## Architecture

The project follows a modular architecture under `src/web_ui/`:

### Core Modules

**`agent/`** - AI Agent implementations

- `browser_use/browser_use_agent.py` - Main browser agent with enhanced signal handling, Ctrl+C support, and tool calling method auto-detection
- `deep_research/deep_research_agent.py` - Specialized research agent from Agent Marketplace

**`browser/`** - Browser management

- `custom_browser.py` - Custom browser initialization with support for user's own Chrome/browser
- `custom_context.py` - Browser context management for persistent sessions

**`controller/`** - Action controllers

- `custom_controller.py` - Extended controller with custom actions and MCP integration
- Registers actions like clipboard operations, content extraction, and assistant callbacks

**`utils/`** - Shared utilities

- `llm_provider.py` - LLM provider factory supporting 15+ LLM providers (OpenAI, Anthropic, Google, Azure, DeepSeek, Ollama, Mistral, IBM Watson, AWS Bedrock, etc.)
- `mcp_client.py` - Model Context Protocol client setup and tool registration
- `mcp_config.py` - MCP configuration file loading, validation, and management
- `config.py` - Configuration management
- `utils.py` - Common utilities

**`webui/`** - Gradio UI components

- `interface.py` - Main UI creation and theming
- `webui_manager.py` - State management for UI
- `components/` - Individual tab components:
  - `agent_settings_tab.py` - LLM configuration UI
  - `browser_settings_tab.py` - Browser configuration UI
  - `mcp_settings_tab.py` - MCP server configuration UI
  - `browser_use_agent_tab.py` - Agent execution UI
  - `deep_research_agent_tab.py` - Research agent UI
  - `load_save_config_tab.py` - Config persistence UI

### Key Architectural Patterns

1. **Custom Agent Extension**: The project extends `browser_use.agent.service.Agent` with `BrowserUseAgent` to add:
   - Auto-detection of tool calling methods based on LLM provider
   - Signal handling for Ctrl+C pause/resume
   - Playwright script generation and GIF creation

2. **Controller Pattern**: Extends `browser_use.controller.service.Controller` with custom actions like clipboard operations and content extraction

3. **LLM Provider Abstraction**: Single factory function (`get_llm_model()`) returns LangChain chat model instances for any supported provider based on configuration

4. **MCP Integration**: Dynamic tool registration from MCP servers, converting MCP tools to LangChain-compatible tools

5. **Gradio Component Structure**: Each UI tab is a separate component function that accepts `WebuiManager` for state coordination

## Environment Configuration

Create `.env` from `.env.example`:

```bash
cp .env.example .env
```

**Critical Environment Variables:**

- `DEFAULT_LLM` - Default LLM provider (e.g., `openai`, `anthropic`, `google`)
- `{PROVIDER}_API_KEY` - API keys for each LLM provider
- `BROWSER_PATH` - Path to Chrome/browser executable (for custom browser mode)
- `BROWSER_USER_DATA` - Browser profile directory (for custom browser mode)
- `KEEP_BROWSER_OPEN` - Keep browser open between tasks (default: `true`)
- `BROWSER_USE_LOGGING_LEVEL` - Log level: `result`, `info`, or `debug`

## Important Notes

### LLM Provider Integration

- Tool calling method is auto-detected per provider in `BrowserUseAgent._set_tool_calling_method()`
- Some models don't support tool calling and fall back to `raw` mode
- Google Gemini uses native tool calling (returns `None` for auto-detection)
- OpenAI/Azure use `function_calling` mode

### Browser Management

- When `USE_OWN_BROWSER=true`, the app connects to your Chrome profile via debugging port
- Close all Chrome windows before enabling "Use Own Browser" mode
- Open the WebUI in a non-Chrome browser (Firefox/Edge) when using your Chrome profile

### MCP (Model Context Protocol)

**Model Context Protocol (MCP)** allows AI agents to use tools and capabilities from external servers. This project supports persistent MCP configuration via `data/mcp.json`.

#### Quick Start

1. **Create MCP Configuration:**

   ```bash
   # Option 1: Use the Web UI
   # Go to the "MCP Settings" tab and click "Load Example Config"

   # Option 2: Copy the example file
   cp mcp.example.json data/mcp.json
   ```

2. **Edit Configuration:**
   Edit `data/mcp.json` to enable the MCP servers you need:

   ```json
   {
     "mcpServers": {
       "filesystem": {
         "command": "npx",
         "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/directory"],
         "transport": "stdio"
       },
       "brave-search": {
         "command": "npx",
         "args": ["-y", "@modelcontextprotocol/server-brave-search"],
         "env": {
           "BRAVE_API_KEY": "your_api_key_here"
         },
         "transport": "stdio"
       }
     }
   }
   ```

   **Note:** As of `langchain-mcp-adapters 0.1.0+`, each server configuration **must include** a `"transport": "stdio"` key.

3. **Use the MCP Settings Tab:**
   - Navigate to the **🔌 MCP Settings** tab in the Web UI
   - Use the built-in editor to view, validate, and save your configuration
   - Click "Load Example Config" to see all available MCP servers
   - The configuration is automatically loaded when you start an agent

#### Configuration File Locations

- **Default:** `./data/mcp.json` (data directory)
- **Custom:** Set `MCP_CONFIG_PATH` environment variable
- **Example:** `./mcp.example.json` (reference, not loaded)

The `data/mcp.json` file is gitignored by default (user-specific configuration).

#### Popular MCP Servers

| Server | Description | Configuration |
|--------|-------------|---------------|
| **filesystem** | Access local files and directories | Requires path argument |
| **fetch** | Make HTTP requests to external APIs | No configuration needed |
| **brave-search** | Web search via Brave Search API | Requires `BRAVE_API_KEY` |
| **github** | GitHub repository operations | Requires `GITHUB_PERSONAL_ACCESS_TOKEN` |
| **postgres** | PostgreSQL database operations | Requires database URL |
| **sqlite** | SQLite database operations | Requires database path |
| **memory** | Persistent memory for agents | No configuration needed |
| **puppeteer** | Browser automation capabilities | No configuration needed |

See `mcp.example.json` for complete configuration examples.

#### How It Works

1. **Auto-Loading:** When an agent starts, it automatically loads `data/mcp.json` if it exists
2. **Tool Registration:** Tools from MCP servers are registered as `mcp.{server_name}.{tool_name}`
3. **Dynamic Usage:** Agents can discover and use MCP tools alongside built-in browser actions
4. **Hot Reload:** Use the "Clear" button in the Run Agent tab to reload agents with new MCP configuration

#### MCP Configuration Structure

```json
{
  "mcpServers": {
    "server-name": {
      "command": "npx",           // Command to run (e.g., "npx", "python", "node")
      "args": [                   // Command arguments
        "-y",
        "@org/package-name"
      ],
      "env": {                    // Optional environment variables
        "API_KEY": "value"
      },
      "transport": "stdio"        // Required: transport type (stdio, sse, websocket, streamable_http)
    }
  }
}
```

**⚠️ Breaking Change (langchain-mcp-adapters 0.1.0+):**
All MCP server configurations **must** include `"transport": "stdio"`. Most MCP servers use stdio transport for process-based communication.

#### Web UI Features

The **MCP Settings** tab provides:

- **Live Editor:** Edit `data/mcp.json` with syntax highlighting
- **Validation:** Real-time validation of configuration structure
- **Server Summary:** View configured servers and their details
- **Example Loading:** One-click loading of example configurations
- **Save/Load:** Persistent configuration management

#### Configuration Management

**Via Web UI:**

1. Go to the **MCP Settings** tab
2. Edit the JSON configuration
3. Click "Save Configuration"
4. Restart agents (use "Clear" button) to apply changes

**Via File System:**

1. Edit `data/mcp.json` directly in your editor
2. Restart the Web UI or use "Clear" + new agent task

**Via Environment:**

```bash
# Use custom config location
export MCP_CONFIG_PATH=/path/to/custom/data/mcp.json
python webui.py
```

#### Agent Settings Tab Integration

The **Agent Settings** tab shows:

- ✅ **Active Configuration:** Displays current `data/mcp.json` status
- 📊 **Server Summary:** Lists configured MCP servers
- 📁 **File Upload:** Temporary override via JSON file upload (if no `data/mcp.json` exists)

#### Implementation Files

- `src/web_ui/utils/mcp_config.py` - Configuration loading, validation, and management
- `src/web_ui/utils/mcp_client.py` - MCP client setup and tool registration
- `src/web_ui/controller/custom_controller.py` - Auto-loading and tool registration
- `src/web_ui/webui/components/mcp_settings_tab.py` - Web UI for editing configuration

#### Troubleshooting

**MCP tools not appearing:**

1. Verify `data/mcp.json` exists and is valid (use MCP Settings tab validator)
2. Check browser console/terminal for MCP client errors
3. Ensure required environment variables (API keys) are set
4. Use "Clear" button to restart the agent with new configuration

**Configuration not loading:**

1. Check file path: `./data/mcp.json` or `$MCP_CONFIG_PATH`
2. Validate JSON syntax (no trailing commas, proper quotes)
3. Review logs for "Loaded MCP configuration from..." message

**Server-specific issues:**

- **Filesystem:** Ensure the specified path exists and is accessible
- **API-based servers:** Verify API keys are correct and have proper permissions
- **npm packages:** Run `npx -y @package/name` manually to test installation

### Signal Handling

- Agents support Ctrl+C to pause execution
- Press Ctrl+C once to pause, type 'r' to resume, 'q' to quit
- Second Ctrl+C forces exit
- Implemented via `browser_use.utils.SignalHandler`

### Testing

- Test structure: `tests/` with test files prefixed `test_*`
- Uses `pytest` with `pytest-asyncio` for async tests
- Test coverage includes agents, controllers, LLM API, and Playwright integration

### Code Style

- Uses Ruff for formatting and linting (100 char line length)
- Target: Python 3.14
- Import sorting via isort (integrated in Ruff)
- Type checking via `ty` (alpha - handle with care)

### Docker Notes

- Includes VNC server for watching browser interactions
- Default VNC password: `youvncpassword` (change via `VNC_PASSWORD`)
- Uses `supervisord.conf` for process management
