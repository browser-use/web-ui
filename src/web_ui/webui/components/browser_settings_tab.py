import logging
import os

import gradio as gr

from src.web_ui.webui.webui_manager import WebuiManager


def strtobool(val):
    """Convert a string representation of truth to true (1) or false (0).

    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    """
    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return 1
    elif val in ("n", "no", "f", "false", "off", "0"):
        return 0
    else:
        raise ValueError(f"invalid truth value {val!r}")


logger = logging.getLogger(__name__)


async def close_browser(webui_manager: WebuiManager):
    """
    Close browser
    """
    if webui_manager.bu_current_task and not webui_manager.bu_current_task.done():
        webui_manager.bu_current_task.cancel()
        webui_manager.bu_current_task = None

    if webui_manager.bu_browser_context:
        logger.info("⚠️ Closing browser context when changing browser config.")
        await webui_manager.bu_browser_context.close()
        webui_manager.bu_browser_context = None

    if webui_manager.bu_browser:
        logger.info("⚠️ Closing browser when changing browser config.")
        await webui_manager.bu_browser.close()
        webui_manager.bu_browser = None


def create_browser_settings_tab(webui_manager: WebuiManager):
    """
    Creates a browser settings tab with improved organization.
    """
    tab_components = {}

    # Custom Browser Configuration
    with gr.Accordion("🌐 Custom Browser Configuration", open=False):
        gr.Markdown("""
        **Use your own Chrome/browser** instead of Playwright's default browser.

        ⚠️ Close all Chrome windows before enabling "Use Own Browser" mode.
        """)

        with gr.Row():
            use_own_browser = gr.Checkbox(
                label="Use Own Browser",
                value=bool(strtobool(os.getenv("USE_OWN_BROWSER", "false"))),
                info="Connect to your existing browser instance",
                interactive=True,
            )
            keep_browser_open = gr.Checkbox(
                label="Keep Browser Open",
                value=bool(strtobool(os.getenv("KEEP_BROWSER_OPEN", "true"))),
                info="Persist browser between tasks",
                interactive=True,
            )

        with gr.Row():
            browser_binary_path = gr.Textbox(
                label="Browser Binary Path",
                lines=1,
                interactive=True,
                placeholder="e.g. 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'",
                info="Path to Chrome/Chromium executable",
            )
            browser_user_data_dir = gr.Textbox(
                label="Browser User Data Directory",
                lines=1,
                interactive=True,
                placeholder="Leave empty for default profile",
                info="Custom profile directory",
            )

    # Browser Behavior Settings
    with gr.Accordion("⚙️ Browser Behavior", open=True):
        gr.Markdown("**Configure how the browser runs** and displays.")

        with gr.Row():
            headless = gr.Checkbox(
                label="Headless Mode",
                value=False,
                info="Run browser without visible GUI (faster but no visual feedback)",
                interactive=True,
            )
            disable_security = gr.Checkbox(
                label="Disable Security",
                value=False,
                info="⚠️ Disable browser security (use with caution)",
                interactive=True,
            )

        with gr.Row():
            window_w = gr.Number(
                label="Window Width",
                value=1280,
                info="Browser viewport width in pixels",
                interactive=True,
            )
            window_h = gr.Number(
                label="Window Height",
                value=1100,
                info="Browser viewport height in pixels",
                interactive=True,
            )

    # Remote Debugging Configuration
    with gr.Accordion("🔗 Remote Debugging (Advanced)", open=False):
        gr.Markdown("""
        **Connect to a remote browser** via Chrome DevTools Protocol or WebSocket.

        Use this for debugging or connecting to browsers running on different machines.
        """)

        with gr.Row():
            cdp_url = gr.Textbox(
                label="CDP URL",
                value=os.getenv("BROWSER_CDP", None),
                info="Chrome DevTools Protocol endpoint",
                placeholder="http://localhost:9222",
                interactive=True,
            )
            wss_url = gr.Textbox(
                label="WSS URL",
                info="WebSocket Secure URL for remote debugging",
                placeholder="wss://localhost:9222/devtools/browser/...",
                interactive=True,
            )

    # Storage Paths Configuration
    with gr.Accordion("💾 Storage Paths", open=False):
        gr.Markdown("**Configure where files are saved** by the agent and browser.")

        with gr.Row():
            save_recording_path = gr.Textbox(
                label="📹 Recording Path",
                placeholder="./tmp/record_videos",
                info="Browser screen recordings (GIF/MP4)",
                interactive=True,
            )

            save_trace_path = gr.Textbox(
                label="📊 Trace Path",
                placeholder="./tmp/traces",
                info="Agent execution traces for debugging",
                interactive=True,
            )

        with gr.Row():
            save_agent_history_path = gr.Textbox(
                label="📜 Agent History Path",
                value="./tmp/agent_history",
                info="Agent conversation and action history",
                interactive=True,
            )
            save_download_path = gr.Textbox(
                label="⬇️ Downloads Path",
                value="./tmp/downloads",
                info="Files downloaded by the browser",
                interactive=True,
            )
    tab_components.update(
        {
            "browser_binary_path": browser_binary_path,
            "browser_user_data_dir": browser_user_data_dir,
            "use_own_browser": use_own_browser,
            "keep_browser_open": keep_browser_open,
            "headless": headless,
            "disable_security": disable_security,
            "save_recording_path": save_recording_path,
            "save_trace_path": save_trace_path,
            "save_agent_history_path": save_agent_history_path,
            "save_download_path": save_download_path,
            "cdp_url": cdp_url,
            "wss_url": wss_url,
            "window_h": window_h,
            "window_w": window_w,
        }
    )
    webui_manager.add_components("browser_settings", tab_components)

    async def close_wrapper():
        """Wrapper for handle_clear."""
        await close_browser(webui_manager)

    headless.change(close_wrapper)
    keep_browser_open.change(close_wrapper)
    disable_security.change(close_wrapper)
    use_own_browser.change(close_wrapper)
