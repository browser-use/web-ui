# Browser Use Web UI Development Guide

## Project Overview
Browser Use Web UI is a Gradio-based web interface for browser automation agents built on the browser-use library (https://github.com/browser-use/browser-use). The architecture follows a modular design with clear separation between browser control, agent logic, and UI components.

## Core Architecture

### Key Components
- **`src/agent/`**: Agent implementations (`BrowserUseAgent`, `DeepResearchAgent`)
- **`src/browser/`**: Custom browser and context wrappers extending browser-use
- **`src/controller/`**: Custom action controller with MCP tool integration
- **`src/webui/`**: Gradio interface with modular tab components
- **`src/utils/`**: Configuration, LLM providers, and utilities

### Critical Files
- `webui.py`: Main entry point with CLI args for IP/port/theme
- `src/webui/interface.py`: UI assembly with tab-based layout
- `src/controller/custom_controller.py`: Action registry with custom actions
- `src/utils/config.py`: LLM provider definitions and model mappings

## Development Patterns

### LLM Provider Integration
Follow the pattern in `src/utils/config.py` for new providers:
```python
PROVIDER_DISPLAY_NAMES = {"provider_key": "Display Name"}
model_names = {"provider_key": ["model1", "model2"]}
```

### Custom Actions
Register new browser actions in `CustomController._register_custom_actions()`:
```python
@self.registry.action("Description of when to use this action")
async def action_name(param: str, browser: BrowserContext):
    # Implementation
    return ActionResult(extracted_content=result, include_in_memory=True)
```

### UI Components
Create new tabs as separate files in `src/webui/components/` following the pattern:
```python
def create_tab_name_tab(ui_manager: WebuiManager):
    with gr.Column():
        # Gradio components
        pass
```

### Agent Implementations
Extend `BrowserUseAgent` or create new agents inheriting from browser-use's `Agent` class. Key patterns:
- Override `_set_tool_calling_method()` for model-specific configurations
- Use `@time_execution_async("--run (agent)")` for performance tracking
- Implement proper cleanup in `finally` blocks

## Configuration & Environment

### Environment Variables
- LLM API keys: `{PROVIDER}_API_KEY`, `{PROVIDER}_ENDPOINT`
- Browser: `BROWSER_PATH`, `BROWSER_USER_DATA`, `BROWSER_DEBUGGING_PORT`
- Logging: `BROWSER_USE_LOGGING_LEVEL`, `ANONYMIZED_TELEMETRY`

### Docker Development
- Uses supervisord for multi-service orchestration (VNC, noVNC, WebUI)
- VNC available at `:6080/vnc.html` for browser observation
- Playwright browsers installed to `/ms-browsers`

## Testing & Running

### Local Development
```bash
python webui.py --ip 127.0.0.1 --port 7788 --theme Ocean
```

### Test Structure
Tests in `tests/` demonstrate usage patterns:
- `test_agents.py`: Complete agent workflows with LLM/browser setup
- MCP server integration examples with desktop-commander

### Docker Deployment
```bash
docker compose up --build
# For ARM64: TARGETPLATFORM=linux/arm64 docker compose up --build
```

## MCP Integration
Model Context Protocol (MCP) tools are dynamically registered via `setup_mcp_client()`. Tools are prefixed with `mcp.{server_name}.{tool_name}` and integrated into the action registry.

## Browser Configuration
- Custom browser extends browser-use's Browser class
- Supports persistent sessions via `BROWSER_USER_DATA`
- Window dimensions configurable via `window_w`, `window_h` variables
- Use `use_own_browser=True` for existing Chrome profiles

## Key Dependencies
- `browser-use==0.1.48`: Core browser automation
- `gradio==5.27.0`: Web UI framework
- `langchain-*`: LLM provider adapters
- `playwright`: Browser automation backend