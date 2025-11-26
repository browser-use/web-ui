"""
Help Modal Component

Provides Getting Started guide, keyboard shortcuts, and troubleshooting tips.
"""

import gradio as gr

from src.web_ui.webui.webui_manager import WebuiManager


def create_help_modal(webui_manager: WebuiManager):
    """
    Create a help modal with Getting Started guide and keyboard shortcuts.

    Args:
        webui_manager: WebUI manager instance

    Returns:
        dict: Modal components
    """
    modal_components = {}

    # Modal dialog (initially hidden)
    with gr.Group(visible=False, elem_classes=["help-modal-overlay"]) as help_modal:
        with gr.Column(elem_classes=["help-modal-content"]):
            gr.Markdown("# 🎓 Getting Started with Browser Use WebUI")

            with gr.Tabs():
                with gr.TabItem("📖 Quick Start"):
                    gr.Markdown(
                        """
                    ## Welcome!

                    Browser Use WebUI allows AI agents to control web browsers and perform tasks automatically.

                    ### First Time Setup:

                    1. **Configure Your LLM** (if not in .env)
                       - Click the ⚙️ Settings toggle on the right
                       - Expand "🤖 LLM Configuration"
                       - Select your provider (OpenAI, Anthropic, Google, etc.)
                       - Add your API key if needed

                    2. **Choose Your Mode**
                       - Use **Quick Presets** in the left sidebar for common scenarios
                       - OR manually configure in Settings panel

                    3. **Run Your First Task**
                       - Enter a task description in the main area
                       - Click "▶️ Run Agent"
                       - Watch the agent work!

                    ### Quick Presets:

                    - **🔬 Research Mode**: Claude Sonnet, high creativity, 150 max steps
                    - **🤖 Automation Mode**: GPT-4o, balanced, 100 max steps
                    - **🌐 Custom Browser**: Use your own Chrome profile for authenticated sites

                    ### Tips:

                    - **Vision Mode**: Enable to let the LLM see screenshots (better accuracy)
                    - **Custom Browser**: Access logged-in websites using your browser profile
                    - **MCP Servers**: Add filesystem, fetch, or brave-search for extended capabilities
                    - **Max Steps**: Increase for complex multi-step tasks
                    - **Save Configs**: Save your favorite setups via Settings panel
                    """
                    )

                with gr.TabItem("⌨️ Keyboard Shortcuts"):
                    gr.Markdown(
                        """
                    ## Keyboard Shortcuts

                    Speed up your workflow with these keyboard shortcuts:

                    | Shortcut | Action |
                    |----------|--------|
                    | `Ctrl + Enter` | Submit task (when in textarea) |
                    | `Esc` | Stop agent execution |
                    | `?` | Show/hide this help modal |

                    ### Agent Control:

                    During agent execution, you can:
                    - Press `Ctrl+C` in the terminal to pause the agent
                    - Type 'r' to resume
                    - Type 'q' to quit

                    *(Note: Terminal shortcuts only work when running via command line)*
                    """
                    )

                with gr.TabItem("🎯 Use Cases"):
                    gr.Markdown(
                        """
                    ## Common Use Cases

                    ### 🔍 Web Research
                    - **Agent**: Deep Research Agent (Agent Marketplace)
                    - **Settings**: Claude Sonnet or GPT-4, temperature 0.7-0.8
                    - **MCP**: Enable brave-search or fetch for web access
                    - **Example Task**: "Research the latest trends in AI safety"

                    ### 🤖 Browser Automation
                    - **Agent**: Browser Use Agent
                    - **Settings**: GPT-4o, temperature 0.5-0.6, vision enabled
                    - **Custom Browser**: Enable if accessing authenticated sites
                    - **Example Task**: "Fill out this form with my information"

                    ### 📊 Data Extraction
                    - **Agent**: Browser Use Agent
                    - **Settings**: Any vision-capable model, temperature 0.5
                    - **MCP**: Enable filesystem to save extracted data
                    - **Example Task**: "Extract all product prices from this website"

                    ### 🧪 Testing & QA
                    - **Agent**: Browser Use Agent
                    - **Settings**: GPT-4o-mini (cost-effective), vision enabled
                    - **Custom Browser**: Use if testing authenticated flows
                    - **Example Task**: "Test the login flow and report any issues"
                    """
                    )

                with gr.TabItem("🔧 Troubleshooting"):
                    gr.Markdown(
                        """
                    ## Common Issues & Solutions

                    ### "No API key configured"
                    **Solution**: Add your API key in Settings > LLM Configuration > API Credentials, or set environment variables in `.env` file.

                    ### "Browser failed to start"
                    **Solutions**:
                    - Ensure Playwright is installed: `playwright install chromium --with-deps`
                    - If using Custom Browser mode, close all Chrome windows first
                    - Check browser binary path is correct

                    ### "Agent gets stuck in a loop"
                    **Solutions**:
                    - Reduce `Max Steps` to limit iterations
                    - Lower `Temperature` for more deterministic behavior
                    - Try a different LLM model
                    - Click "Stop" and rephrase your task more specifically

                    ### "Vision/screenshots not working"
                    **Solutions**:
                    - Ensure "Enable Vision" is checked in Settings
                    - Verify your LLM model supports vision (e.g., GPT-4o, Claude Sonnet)
                    - Check that browser is not in headless mode if you need to see what's happening

                    ### "MCP tools not appearing"
                    **Solutions**:
                    - Verify `data/mcp.json` exists and is valid (use MCP Settings tab)
                    - Check that required environment variables (API keys) are set
                    - Use "Clear" button to restart the agent with new MCP configuration

                    ### "Custom browser mode not working"
                    **Solutions**:
                    - Close ALL Chrome/browser windows before starting
                    - Verify browser binary path is correct
                    - Ensure user data directory exists
                    - Open the WebUI in a different browser (Firefox/Edge)

                    ### Still having issues?
                    - Check the browser console (F12) for errors
                    - Review terminal logs for detailed error messages
                    - Consult CLAUDE.md in the project root for architecture details
                    """
                    )

                with gr.TabItem("📚 Resources"):
                    gr.Markdown(
                        """
                    ## Additional Resources

                    ### Documentation
                    - **Project README**: See `README.md` in project root
                    - **Claude Code Guide**: See `CLAUDE.md` for architecture details
                    - **MCP Documentation**: See `mcp.example.json` for server examples

                    ### Links
                    - **Browser Use Library**: [github.com/browser-use/browser-use](https://github.com/browser-use/browser-use)
                    - **Model Context Protocol**: [modelcontextprotocol.io](https://modelcontextprotocol.io)
                    - **LangChain Docs**: [python.langchain.com](https://python.langchain.com)

                    ### Community
                    - Report issues on GitHub
                    - Contribute improvements via Pull Requests
                    - Share your custom agents and MCP server configs

                    ### Environment Variables

                    Key environment variables in `.env`:
                    ```
                    DEFAULT_LLM=openai
                    OPENAI_API_KEY=sk-...
                    ANTHROPIC_API_KEY=sk-ant-...
                    GOOGLE_API_KEY=...

                    USE_OWN_BROWSER=false
                    KEEP_BROWSER_OPEN=true
                    BROWSER_USE_LOGGING_LEVEL=info
                    ```

                    See `.env.example` for full list.
                    """
                    )

            # Close button
            with gr.Row():
                close_help_button = gr.Button("Close", variant="primary", size="lg")

    modal_components.update(
        {
            "help_modal": help_modal,
            "close_help_button": close_help_button,
        }
    )

    webui_manager.add_components("help_modal", modal_components)

    # Close button handler
    def close_modal():
        """Hide the help modal."""
        return gr.update(visible=False)

    close_help_button.click(
        fn=close_modal,
        inputs=[],
        outputs=[help_modal],
    )

    return modal_components
