import gradio as gr

from src.web_ui.webui.components.browser_use_agent_tab import (
    handle_clear,
    handle_pause_resume,
    handle_stop,
    handle_submit,
    run_agent_task,
)
from src.web_ui.webui.components.dashboard_main import create_dashboard_main
from src.web_ui.webui.components.dashboard_settings import create_dashboard_settings
from src.web_ui.webui.components.dashboard_sidebar import create_dashboard_sidebar
from src.web_ui.webui.components.deep_research_agent_tab import (
    run_deep_research,
    stop_deep_research,
)
from src.web_ui.webui.components.help_modal import create_help_modal
from src.web_ui.webui.components.mcp_settings_tab import create_mcp_settings_tab
from src.web_ui.webui.webui_manager import WebuiManager

theme_map = {
    "Default": gr.themes.Default(),
    "Soft": gr.themes.Soft(),
    "Monochrome": gr.themes.Monochrome(),
    "Glass": gr.themes.Glass(),
    "Origin": gr.themes.Origin(),
    "Citrus": gr.themes.Citrus(),
    "Ocean": gr.themes.Ocean(),
    "Base": gr.themes.Base(),
}


def create_ui(theme_name="Ocean"):
    css = """
    .gradio-container {
        width: 95vw !important;
        max-width: 95% !important;
        margin-left: auto !important;
        margin-right: auto !important;
        padding-top: 10px !important;
    }

    /* Header Styles */
    .header-container {
        text-align: center;
        padding: 20px;
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.12), rgba(168, 85, 247, 0.12));
        border-radius: 12px;
        margin-bottom: 16px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .header-left {
        flex: 1;
    }
    .header-center {
        flex: 2;
        text-align: center;
    }
    .header-right {
        flex: 1;
        text-align: right;
    }
    .header-title {
        margin: 0;
        font-size: 1.8em;
        font-weight: 700;
        background: linear-gradient(135deg, #6366f1, #a855f7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .header-tagline {
        font-size: 0.95em;
        opacity: 0.8;
        margin-top: 4px;
    }

    /* Dashboard Layout */
    .dashboard-container {
        display: flex;
        gap: 16px;
        min-height: calc(100vh - 250px);
    }

    .dashboard-sidebar {
        width: 250px;
        min-width: 250px;
        border-right: 1px solid rgba(128, 128, 128, 0.2);
        padding-right: 16px;
        overflow-y: auto;
    }

    .dashboard-main {
        flex: 1;
        overflow-y: auto;
        padding: 0 16px;
    }

    .dashboard-settings {
        width: 400px;
        min-width: 400px;
        max-width: 400px;
        overflow-y: auto;
        border-left: 1px solid rgba(128, 128, 128, 0.2);
        padding-left: 16px;
    }

    /* Status Cards */
    .status-card {
        background: rgba(99, 102, 241, 0.05);
        border: 1px solid rgba(99, 102, 241, 0.2);
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 12px;
    }
    .status-card h3 {
        margin-top: 0;
        font-size: 1.1em;
        margin-bottom: 12px;
    }

    /* Preset Buttons */
    .preset-button-group {
        display: flex;
        flex-direction: column;
        gap: 8px;
        margin-bottom: 16px;
    }
    .preset-button {
        width: 100%;
        text-align: left !important;
    }

    /* History List */
    .history-list {
        max-height: 200px;
        overflow-y: auto;
    }
    .history-item {
        padding: 8px;
        border-left: 2px solid rgba(99, 102, 241, 0.3);
        margin-bottom: 8px;
        font-size: 0.9em;
        cursor: pointer;
        background: rgba(255, 255, 255, 0.3);
        border-radius: 4px;
    }
    .history-item:hover {
        background: rgba(99, 102, 241, 0.1);
    }


    /* Help Modal */
    .help-modal-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
    }
    .help-modal-content {
        background: var(--body-background-fill);
        padding: 30px;
        border-radius: 12px;
        max-width: 800px;
        max-height: 80vh;
        overflow-y: auto;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
    }

    /* MCP Settings Modal */
    .mcp-modal-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 9999;
    }
    .mcp-modal-content {
        background: var(--body-background-fill);
        padding: 30px;
        border-radius: 12px;
        width: 90%;
        max-width: 1000px;
        max-height: 80vh;
        overflow-y: auto;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
    }

    /* Agent Selector */
    .agent-selector {
        margin-bottom: 16px;
    }

    /* Loading States */
    .loading-spinner {
        border: 4px solid rgba(99, 102, 241, 0.1);
        border-top: 4px solid #6366f1;
        border-radius: 50%;
        width: 40px;
        height: 40px;
        animation: spin 1s linear infinite;
    }
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    /* Notification System */
    #notification-container {
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        display: flex;
        flex-direction: column;
        gap: 10px;
        max-width: 400px;
    }
    .notification {
        display: flex;
        align-items: flex-start;
        gap: 12px;
        padding: 16px;
        background: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        animation: slideIn 0.3s forwards;
    }
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    /* Improved button styles */
    .gr-button {
        border-radius: 6px;
        font-weight: 500;
        transition: all 0.2s;
    }
    .gr-button-primary {
        background: linear-gradient(135deg, #6366f1, #a855f7) !important;
        border: none !important;
    }
    .gr-button-secondary {
        border: 1px solid rgba(99, 102, 241, 0.3) !important;
    }

    /* Desktop-first responsiveness */
    @media (max-width: 1400px) {
        .dashboard-settings {
            width: 350px;
            min-width: 350px;
            max-width: 350px;
        }
    }

    @media (max-width: 1200px) {
        .dashboard-sidebar {
            width: 220px;
            min-width: 220px;
        }
    }
    """

    # Enhanced JavaScript features
    js_func = """
    function refresh() {
        const url = new URL(window.location);
        if (url.searchParams.get('__theme') !== 'dark') {
            url.searchParams.set('__theme', 'dark');
            window.location.href = url.href;
        }
    }

    // Initialize features after Gradio is ready
    setTimeout(function() {
        // Keyboard shortcuts
        document.addEventListener('keydown', function(e) {
            // Ctrl/Cmd + Enter to submit
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && e.target.matches('textarea')) {
                const runButton = document.querySelector('button[id*="run"]');
                if (runButton) runButton.click();
            }

            // Escape to stop
            if (e.key === 'Escape' && !e.target.matches('input, textarea')) {
                const stopButton = document.querySelector('button[id*="stop"]');
                if (stopButton) stopButton.click();
            }

            // ? to show help
            if (e.key === '?' && !e.target.matches('input, textarea')) {
                const helpButton = document.querySelector('button[id*="help"]');
                if (helpButton) helpButton.click();
            }
        });

        // Notification system
        window.showNotification = function(type, title, message, duration) {
            duration = duration || 5000;
            let container = document.getElementById('notification-container');
            if (!container) {
                container = document.createElement('div');
                container.id = 'notification-container';
                document.body.appendChild(container);
            }

            const icons = {
                success: '✓',
                info: 'ℹ',
                warning: '⚠',
                error: '✕'
            };

            const notification = document.createElement('div');
            notification.className = 'notification notification-' + type;
            notification.innerHTML = `
                <div style="font-size: 24px;">${icons[type] || 'ℹ'}</div>
                <div style="flex: 1;">
                    <strong>${title}</strong>
                    <p style="margin: 4px 0 0 0; font-size: 0.9em; opacity: 0.8;">${message}</p>
                </div>
                <button onclick="this.parentElement.remove()" style="background: none; border: none; font-size: 24px; cursor: pointer; opacity: 0.5;">×</button>
            `;
            container.appendChild(notification);

            setTimeout(function() {
                if (notification.parentNode) notification.remove();
            }, duration);
        };
    }, 100);
    """

    ui_manager = WebuiManager()

    with gr.Blocks(
        title="Browser Use WebUI",
        theme=theme_map[theme_name],
        css=css,
        js=js_func,
    ) as demo:
        # Header with Help button
        with gr.Row(elem_classes=["header-container"]):
            gr.HTML("<div class='header-left'></div>")
            gr.HTML(
                """
                <div class='header-center'>
                    <h1 class='header-title'>🌐 Browser Use WebUI</h1>
                    <p class='header-tagline'>AI-Powered Browser Automation Platform</p>
                </div>
                """
            )
            with gr.Column(elem_classes=["header-right"]):
                help_button = gr.Button("❓ Help", size="sm", variant="secondary")

        # Main Dashboard Layout
        with gr.Row(elem_classes=["dashboard-container"]):
            # Left Sidebar
            with gr.Column(elem_classes=["dashboard-sidebar"], scale=0):
                create_dashboard_sidebar(ui_manager)

            # Main Content Area
            with gr.Column(elem_classes=["dashboard-main"], scale=3):
                create_dashboard_main(ui_manager)

            # Settings Panel - Always visible
            with gr.Column(
                elem_classes=["dashboard-settings"],
                scale=0,
                visible=True,
            ):
                create_dashboard_settings(ui_manager)

        # Help Modal (overlay)
        create_help_modal(ui_manager)

        # MCP Settings Modal (overlay)
        with gr.Group(visible=False, elem_classes=["mcp-modal-overlay"]) as mcp_modal:
            with gr.Column(elem_classes=["mcp-modal-content"]):
                create_mcp_settings_tab(ui_manager)
                close_mcp_button = gr.Button("Close", variant="primary", size="lg")

        # Wire up Help Modal
        def show_help():
            """Show help modal."""
            _ = ui_manager.get_component_by_id("help_modal.help_modal")
            return gr.update(visible=True)

        def hide_help():
            """Hide help modal."""
            return gr.update(visible=False)

        help_button.click(
            fn=show_help,
            inputs=[],
            outputs=[ui_manager.get_component_by_id("help_modal.help_modal")],
        )

        # Wire up MCP Modal
        def show_mcp_modal():
            """Show MCP settings modal."""
            return gr.update(visible=True)

        def hide_mcp_modal():
            """Hide MCP settings modal."""
            return gr.update(visible=False)

        edit_mcp_btn = ui_manager.get_component_by_id("dashboard_settings.edit_mcp_button")
        edit_mcp_btn.click(  # type: ignore[attr-defined]
            fn=show_mcp_modal,
            inputs=[],
            outputs=[mcp_modal],
        )

        close_mcp_button.click(
            fn=hide_mcp_modal,
            inputs=[],
            outputs=[mcp_modal],
        )

        # Wire up Settings Panel Event Handlers AFTER all components are registered
        # This ensures Gradio's event system initializes properly
        from src.web_ui.webui.components.dashboard_settings import update_model_dropdown

        # Get component references
        llm_provider_comp = ui_manager.get_component_by_id("dashboard_settings.llm_provider")
        llm_model_comp = ui_manager.get_component_by_id("dashboard_settings.llm_model_name")
        ollama_ctx_comp = ui_manager.get_component_by_id("dashboard_settings.ollama_num_ctx")
        use_planner_comp = ui_manager.get_component_by_id("dashboard_settings.use_planner")
        planner_group_comp = ui_manager.get_component_by_id("dashboard_settings.planner_group")
        planner_llm_provider_comp = ui_manager.get_component_by_id(
            "dashboard_settings.planner_llm_provider"
        )
        planner_llm_model_comp = ui_manager.get_component_by_id(
            "dashboard_settings.planner_llm_model_name"
        )
        planner_ollama_ctx_comp = ui_manager.get_component_by_id(
            "dashboard_settings.planner_ollama_num_ctx"
        )
        use_own_browser_comp = ui_manager.get_component_by_id("dashboard_settings.use_own_browser")
        custom_browser_group_comp = ui_manager.get_component_by_id(
            "dashboard_settings.custom_browser_group"
        )
        headless_comp = ui_manager.get_component_by_id("dashboard_settings.headless")
        keep_browser_open_comp = ui_manager.get_component_by_id(
            "dashboard_settings.keep_browser_open"
        )
        disable_security_comp = ui_manager.get_component_by_id(
            "dashboard_settings.disable_security"
        )

        # LLM Provider change -> Update model dropdown and show/hide Ollama context
        def update_llm_settings(provider):
            """Update both model dropdown and Ollama context visibility."""
            print("="*60)
            print(f"[DEBUG] ⚡ update_llm_settings CALLED with provider: {provider}")
            print(f"[DEBUG] Provider type: {type(provider)}")
            print("="*60)
            
            models_update = update_model_dropdown(provider)
            ollama_visible = gr.update(visible=provider == "ollama")
            
            print(f"[DEBUG] ✅ Model update: {models_update}")
            print(f"[DEBUG] ✅ Ollama visible: {ollama_visible}")
            print(f"[DEBUG] Returning {len(models_update.get('choices', []))} model choices")
            print("="*60)
            
            return models_update, ollama_visible

        print("[SETUP] Attaching .change() handler to llm_provider_comp...")
        print(f"[SETUP] llm_provider_comp type: {type(llm_provider_comp)}")
        print(f"[SETUP] llm_provider_comp value: {getattr(llm_provider_comp, 'value', 'NO VALUE')}")
        
        change_event = llm_provider_comp.change(  # type: ignore[attr-defined]
            fn=update_llm_settings,
            inputs=[llm_provider_comp],
            outputs=[llm_model_comp, ollama_ctx_comp],
        )
        
        print(f"[SETUP] ✅ Change handler attached: {change_event}")
        print("[SETUP] Change handler should now fire when provider dropdown changes!")

        # Planner checkbox -> Show/hide planner group
        use_planner_comp.change(  # type: ignore[attr-defined]
            fn=lambda checked: gr.update(visible=checked),
            inputs=[use_planner_comp],
            outputs=[planner_group_comp],
        )

        # Planner provider change
        def update_planner_settings(provider):
            """Update both planner model dropdown and Ollama context visibility."""
            print(f"[DEBUG] ⚡ Planner provider changed to: {provider}")
            models_update = update_model_dropdown(provider)
            ollama_visible = gr.update(visible=provider == "ollama")
            print(f"[DEBUG] ✅ Planner model update complete")
            return models_update, ollama_visible

        planner_llm_provider_comp.change(  # type: ignore[attr-defined]
            fn=update_planner_settings,
            inputs=[planner_llm_provider_comp],
            outputs=[planner_llm_model_comp, planner_ollama_ctx_comp],
        )

        # Use Own Browser checkbox -> Show/hide custom browser fields
        use_own_browser_comp.change(  # type: ignore[attr-defined]
            fn=lambda checked: gr.update(visible=checked),
            inputs=[use_own_browser_comp],
            outputs=[custom_browser_group_comp],
        )

        # Browser config changes -> Close browser
        from src.web_ui.webui.components.dashboard_settings import close_browser

        async def close_wrapper():
            """Wrapper for closing browser."""
            await close_browser(ui_manager)

        headless_comp.change(close_wrapper)  # type: ignore[attr-defined]
        keep_browser_open_comp.change(close_wrapper)  # type: ignore[attr-defined]
        disable_security_comp.change(close_wrapper)  # type: ignore[attr-defined]
        use_own_browser_comp.change(close_wrapper)  # type: ignore[attr-defined]

        # Wire up Preset Buttons from Sidebar
        # These will update settings in the Settings panel
        research_btn = ui_manager.get_component_by_id("dashboard_sidebar.research_btn")
        automation_btn = ui_manager.get_component_by_id("dashboard_sidebar.automation_btn")
        custom_browser_btn = ui_manager.get_component_by_id("dashboard_sidebar.custom_browser_btn")

        def load_research_preset():
            """Load research preset configuration."""
            # Update model dropdown manually since .change() doesn't fire from .click() updates
            model_update = update_model_dropdown("anthropic")
            return [
                gr.update(value="anthropic"),  # llm_provider
                model_update,  # llm_model_name - updated based on provider
                gr.update(value=0.7),  # llm_temperature
                gr.update(value=True),  # use_vision
                gr.update(value=150),  # max_steps
                gr.update(value=10),  # max_actions
                gr.update(value=False),  # headless
                gr.update(value=True),  # keep_browser_open
            ]

        def load_automation_preset():
            """Load automation preset configuration."""
            # Update model dropdown manually since .change() doesn't fire from .click() updates
            model_update = update_model_dropdown("openai")
            return [
                gr.update(value="openai"),  # llm_provider
                model_update,  # llm_model_name - updated based on provider
                gr.update(value=0.6),
                gr.update(value=True),
                gr.update(value=100),
                gr.update(value=10),
                gr.update(value=False),
                gr.update(value=True),
            ]

        def load_custom_browser_preset():
            """Load custom browser preset configuration."""
            # Update model dropdown manually since .change() doesn't fire from .click() updates
            model_update = update_model_dropdown("openai")
            return [
                gr.update(value="openai"),  # llm_provider
                model_update,  # llm_model_name - updated based on provider
                gr.update(value=0.6),
                gr.update(value=True),
                gr.update(value=100),
                gr.update(value=10),
                gr.update(value=False),
                gr.update(value=True),
                gr.update(value=True),  # use_own_browser
            ]

        research_btn.click(  # type: ignore[attr-defined]
            fn=load_research_preset,
            inputs=[],
            outputs=[
                ui_manager.get_component_by_id("dashboard_settings.llm_provider"),
                ui_manager.get_component_by_id("dashboard_settings.llm_model_name"),
                ui_manager.get_component_by_id("dashboard_settings.llm_temperature"),
                ui_manager.get_component_by_id("dashboard_settings.use_vision"),
                ui_manager.get_component_by_id("dashboard_settings.max_steps"),
                ui_manager.get_component_by_id("dashboard_settings.max_actions"),
                ui_manager.get_component_by_id("dashboard_settings.headless"),
                ui_manager.get_component_by_id("dashboard_settings.keep_browser_open"),
            ],
        )

        automation_btn.click(  # type: ignore[attr-defined]
            fn=load_automation_preset,
            inputs=[],
            outputs=[
                ui_manager.get_component_by_id("dashboard_settings.llm_provider"),
                ui_manager.get_component_by_id("dashboard_settings.llm_model_name"),
                ui_manager.get_component_by_id("dashboard_settings.llm_temperature"),
                ui_manager.get_component_by_id("dashboard_settings.use_vision"),
                ui_manager.get_component_by_id("dashboard_settings.max_steps"),
                ui_manager.get_component_by_id("dashboard_settings.max_actions"),
                ui_manager.get_component_by_id("dashboard_settings.headless"),
                ui_manager.get_component_by_id("dashboard_settings.keep_browser_open"),
            ],
        )

        custom_browser_btn.click(  # type: ignore[attr-defined]
            fn=load_custom_browser_preset,
            inputs=[],
            outputs=[
                ui_manager.get_component_by_id("dashboard_settings.llm_provider"),
                ui_manager.get_component_by_id("dashboard_settings.llm_model_name"),
                ui_manager.get_component_by_id("dashboard_settings.llm_temperature"),
                ui_manager.get_component_by_id("dashboard_settings.use_vision"),
                ui_manager.get_component_by_id("dashboard_settings.max_steps"),
                ui_manager.get_component_by_id("dashboard_settings.max_actions"),
                ui_manager.get_component_by_id("dashboard_settings.headless"),
                ui_manager.get_component_by_id("dashboard_settings.keep_browser_open"),
                ui_manager.get_component_by_id("dashboard_settings.use_own_browser"),
            ],
        )

        # Wire up Save/Load Config
        save_config_btn = ui_manager.get_component_by_id("dashboard_settings.save_config_button")
        save_default_btn = ui_manager.get_component_by_id("dashboard_settings.save_default_button")
        load_config_btn = ui_manager.get_component_by_id("dashboard_settings.load_config_button")
        config_file = ui_manager.get_component_by_id("dashboard_settings.config_file")
        config_status = ui_manager.get_component_by_id("dashboard_settings.config_status")

        save_config_btn.click(  # type: ignore[attr-defined]
            fn=ui_manager.save_config,
            inputs=list(ui_manager.get_components()),
            outputs=[config_status],
        )

        def save_default_wrapper(*args):
            """Wrapper for save_as_default that returns status message."""
            file_path = ui_manager.save_as_default(*args)
            return gr.update(value=f"✅ Saved as default settings: {file_path}")

        save_default_btn.click(  # type: ignore[attr-defined]
            fn=save_default_wrapper,
            inputs=list(ui_manager.get_components()),
            outputs=[config_status],
        )

        load_config_btn.click(  # type: ignore[attr-defined]
            fn=lambda: gr.update(visible=True),
            inputs=[],
            outputs=[config_file],
        )

        config_file.change(  # type: ignore[attr-defined]
            fn=ui_manager.load_config,
            inputs=[config_file],
            outputs=ui_manager.get_components(),
        )

        # Initialize default settings and migrate old settings
        from src.web_ui.utils.config import DEFAULT_SETTINGS_FILE

        # Migrate old settings
        migrated_count = ui_manager.migrate_old_settings()
        if migrated_count > 0:
            print(f"✅ Migrated {migrated_count} settings files to data/saved_configs/")

        # Load default settings
        default_loaded = ui_manager.load_default_settings()
        if default_loaded:
            print(f"✅ Loaded default settings from {DEFAULT_SETTINGS_FILE}")
        else:
            print("ℹ️ No default settings found, using environment defaults")

        # Initialize Browser Use Agent
        ui_manager.init_browser_use_agent()

        # Wire up Browser Use Agent handlers
        run_button = ui_manager.get_component_by_id("browser_use_agent.run_button")
        stop_button = ui_manager.get_component_by_id("browser_use_agent.stop_button")
        pause_resume_button = ui_manager.get_component_by_id(
            "browser_use_agent.pause_resume_button"
        )
        clear_button = ui_manager.get_component_by_id("browser_use_agent.clear_button")
        submit_help_button = ui_manager.get_component_by_id("browser_use_agent.submit_help_button")
        chatbot = ui_manager.get_component_by_id("browser_use_agent.chatbot")

        # Wrapper functions to handle async generator functions
        async def run_agent_wrapper(*args):
            """Wrapper for run_agent_task that yields updates."""
            components_dict = dict(zip(ui_manager.get_components(), args, strict=True))
            async for update_dict in run_agent_task(ui_manager, components_dict):
                yield list(update_dict.values())

        async def stop_wrapper():
            """Wrapper for handle_stop."""
            await handle_stop(ui_manager)
            return []

        async def pause_resume_wrapper():
            """Wrapper for handle_pause_resume."""
            result = await handle_pause_resume(ui_manager)
            return [result]

        async def clear_wrapper():
            """Wrapper for handle_clear."""
            result = await handle_clear(ui_manager)
            return [result]

        async def submit_help_wrapper(*args):
            """Wrapper for handle_submit."""
            components_dict = dict(zip(ui_manager.get_components(), args, strict=True))
            async for update_dict in handle_submit(ui_manager, components_dict):
                yield list(update_dict.values())

        run_button.click(  # type: ignore[attr-defined]
            fn=run_agent_wrapper,
            inputs=ui_manager.get_components(),
            outputs=ui_manager.get_components(),
        )

        stop_button.click(  # type: ignore[attr-defined]
            fn=stop_wrapper,
            inputs=[],
            outputs=[],
        )

        pause_resume_button.click(  # type: ignore[attr-defined]
            fn=pause_resume_wrapper,
            inputs=[],
            outputs=[pause_resume_button],
        )

        clear_button.click(  # type: ignore[attr-defined]
            fn=clear_wrapper,
            inputs=[],
            outputs=[chatbot],
        )

        submit_help_button.click(  # type: ignore[attr-defined]
            fn=submit_help_wrapper,
            inputs=ui_manager.get_components(),
            outputs=ui_manager.get_components(),
        )

        # Initialize Deep Research Agent
        ui_manager.init_deep_research_agent()

        # Wire up Deep Research Agent handlers
        start_button = ui_manager.get_component_by_id("deep_research_agent.start_button")
        stop_button_dr = ui_manager.get_component_by_id("deep_research_agent.stop_button")
        clear_button_dr = ui_manager.get_component_by_id("deep_research_agent.clear_button")
        markdown_display = ui_manager.get_component_by_id("deep_research_agent.markdown_display")

        # Wrapper functions for Deep Research Agent
        async def run_research_wrapper(*args):
            """Wrapper for run_deep_research that yields updates."""
            components_dict = dict(zip(ui_manager.get_components(), args, strict=True))
            async for update_dict in run_deep_research(ui_manager, components_dict):
                yield list(update_dict.values())

        async def stop_research_wrapper():
            """Wrapper for stop_deep_research."""
            result = await stop_deep_research(ui_manager)
            return list(result.values()) if result else []

        start_button.click(  # type: ignore[attr-defined]
            fn=run_research_wrapper,
            inputs=ui_manager.get_components(),
            outputs=ui_manager.get_components(),
        )

        stop_button_dr.click(  # type: ignore[attr-defined]
            fn=stop_research_wrapper,
            inputs=[],
            outputs=[],
        )

        clear_button_dr.click(  # type: ignore[attr-defined]
            fn=lambda: gr.update(value="Ready to start new research..."),
            inputs=[],
            outputs=[markdown_display],
        )

    return demo
