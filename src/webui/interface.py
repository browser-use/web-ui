import gradio as gr

from src.webui.webui_manager import WebuiManager
from src.webui.components.agent_settings_tab import create_agent_settings_tab
from src.webui.components.browser_settings_tab import create_browser_settings_tab
from src.webui.components.browser_use_agent_tab import create_browser_use_agent_tab
from src.webui.components.deep_research_agent_tab import create_deep_research_agent_tab
from src.webui.components.load_save_config_tab import create_load_save_config_tab

theme_map = {
    "Default": gr.themes.Default(),
    "Soft": gr.themes.Soft(),
    "Monochrome": gr.themes.Monochrome(),
    "Glass": gr.themes.Glass(),
    "Origin": gr.themes.Origin(),
    "Citrus": gr.themes.Citrus(),
    "Ocean": gr.themes.Ocean(),
    "Base": gr.themes.Base()
}

js_speech_function = """
    () => {
        // --- THIS IS THE UPDATED PART ---
        // We will try multiple ways to find the elements, just in case
        // Gradio has rendered them differently.

        // Try to find the button:
        // 1. A <button> element *inside* an element with id="speech_btn"
        // 2. A <button> element *with* the id="speech_btn"
        const btn = document.querySelector("#speech_btn button") || 
                    document.querySelector("button#speech_btn");

        // Try to find the textbox:
        // 1. A <textarea> *inside* an element with id="user_input"
        // 2. A <textarea> *with* the id="user_input"
        const textarea = document.querySelector("#user_input textarea") || 
                         document.querySelector("textarea#user_input");

        if (!textarea || !btn) {
            alert("Error: Could not find UI elements for speech recognition.");
            return;
        }

        // 1. Check for browser support
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            alert("Your browser does not support the Web Speech API. Try Chrome or Edge.");
            return;
        }

        const recognition = new SpeechRecognition();
        recognition.interimResults = false;
        recognition.lang = 'en-US'; // You can change this (e.g., 'es-ES')

        // 2. Update UI during recognition
        recognition.onstart = () => {
            btn.textContent = "🎙️ Listening...";
            btn.disabled = true;
            textarea.placeholder = "Listening...";
        };

        recognition.onend = () => {
            btn.textContent = "🎙️";
            btn.disabled = false;
            textarea.placeholder = "Enter your task, or click 'Speak' to use voice.";
        };

        recognition.onerror = (event) => {
            btn.textContent = "🎙️";
            btn.disabled = false;
            textarea.placeholder = "Error: " + event.error;
            console.error("Speech recognition error:", event.error);
        };

        // 3. Handle the result
        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            textarea.value = transcript; // Set the visual value
            
            // This is the "magic" part:
            // We must simulate a user "input" event to make Gradio's
            // backend state (components dictionary) update.
            const inputEvent = new Event('input', { bubbles: true });
            textarea.dispatchEvent(inputEvent);
        };

        // 4. Start recognition
        recognition.start();
    }
    """
def create_ui(theme_name="Ocean"):
    css = """
    .gradio-container {
        width: 70vw !important; 
        max-width: 70% !important; 
        margin-left: auto !important;
        margin-right: auto !important;
        padding-top: 10px !important;
    }
    .header-text {
        text-align: center;
        margin-bottom: 20px;
    }
    .tab-header-text {
        text-align: center;
    }
    .theme-section {
        margin-bottom: 10px;
        padding: 15px;
        border-radius: 10px;
    }
    """

    # dark mode in default
    js_func = """
    function refresh() {
        const url = new URL(window.location);

        if (url.searchParams.get('__theme') !== 'dark') {
            url.searchParams.set('__theme', 'dark');
            window.location.href = url.href;
        }
    }
    """

    ui_manager = WebuiManager()

    with gr.Blocks(
            title="Browser Use WebUI", theme=theme_map[theme_name], css=css, js=js_func,
    ) as demo:
        with gr.Row():
            gr.Markdown(
                """
                # 🌐 Browser Use WebUI
                ### Control your browser with AI assistance
                """,
                elem_classes=["header-text"],
            )

        with gr.Tabs() as tabs:
            with gr.TabItem("⚙️ Agent Settings"):
                create_agent_settings_tab(ui_manager)

            with gr.TabItem("🌐 Browser Settings"):
                create_browser_settings_tab(ui_manager)

            with gr.TabItem("🤖 Run Agent"):
                create_browser_use_agent_tab(ui_manager, js_speech_function)

            with gr.TabItem("🎁 Agent Marketplace"):
                gr.Markdown(
                    """
                    ### Agents built on Browser-Use
                    """,
                    elem_classes=["tab-header-text"],
                )
                with gr.Tabs():
                    with gr.TabItem("Deep Research"):
                        create_deep_research_agent_tab(ui_manager)

            with gr.TabItem("📁 Load & Save Config"):
                create_load_save_config_tab(ui_manager)

    return demo
