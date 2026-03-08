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

    # dark mode in default + browser-side autosave backup for UI settings
    js_func = """
    function initializeWebUiClientState() {
        const url = new URL(window.location.href);
        if (url.searchParams.get('__theme') !== 'dark') {
            url.searchParams.set('__theme', 'dark');
            window.location.href = url.toString();
            return;
        }

        if (window.__webuiBackupInitDone) {
            return;
        }
        window.__webuiBackupInitDone = true;

        const DB_NAME = "webui-config-backup";
        const STORE_NAME = "settings";
        const RECORD_KEY = "ui-components-v1";
        const FALLBACK_STORAGE_KEY = "webui-config-backup-fallback";
        const SAVE_INTERVAL_MS = 60000;

        const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

        function isVisible(element) {
            return !!(element && (element.offsetParent !== null || element.getClientRects().length));
        }

        function firstVisible(elements) {
            return Array.from(elements).find((el) => isVisible(el) && !el.disabled && !el.readOnly);
        }

        function getPrimaryControl(componentRoot) {
            return (
                firstVisible(componentRoot.querySelectorAll("input[type='checkbox']")) ||
                firstVisible(componentRoot.querySelectorAll("textarea")) ||
                firstVisible(componentRoot.querySelectorAll("select")) ||
                firstVisible(componentRoot.querySelectorAll("input[type='range']")) ||
                firstVisible(componentRoot.querySelectorAll("input[type='number']")) ||
                firstVisible(
                    componentRoot.querySelectorAll(
                        "input:not([type='file']):not([type='button']):not([type='submit']):not([type='hidden'])"
                    )
                )
            );
        }

        function readControlValue(componentRoot) {
            const control = getPrimaryControl(componentRoot);
            if (!control) {
                return undefined;
            }
            if (control.type === "checkbox") {
                return !!control.checked;
            }
            return control.value;
        }

        function writeControlValue(componentRoot, value) {
            const control = getPrimaryControl(componentRoot);
            if (!control) {
                return;
            }
            if (control.type === "checkbox") {
                control.checked = !!value;
            } else {
                control.value = value == null ? "" : String(value);
            }
            ["input", "change", "blur"].forEach((eventName) => {
                control.dispatchEvent(new Event(eventName, { bubbles: true }));
            });
        }

        function collectUiState() {
            const state = {};
            document.querySelectorAll("[id^='webui-']").forEach((componentRoot) => {
                const value = readControlValue(componentRoot);
                if (value !== undefined) {
                    state[componentRoot.id] = value;
                }
            });
            return state;
        }

        function openBackupDb() {
            return new Promise((resolve, reject) => {
                const request = window.indexedDB.open(DB_NAME, 1);
                request.onupgradeneeded = () => {
                    const db = request.result;
                    if (!db.objectStoreNames.contains(STORE_NAME)) {
                        db.createObjectStore(STORE_NAME, { keyPath: "id" });
                    }
                };
                request.onsuccess = () => resolve(request.result);
                request.onerror = () => reject(request.error);
            });
        }

        async function loadBackupState() {
            try {
                const db = await openBackupDb();
                return await new Promise((resolve, reject) => {
                    const tx = db.transaction(STORE_NAME, "readonly");
                    const store = tx.objectStore(STORE_NAME);
                    const request = store.get(RECORD_KEY);
                    request.onsuccess = () => resolve(request.result ? request.result.payload : null);
                    request.onerror = () => reject(request.error);
                });
            } catch (_) {
                const raw = localStorage.getItem(FALLBACK_STORAGE_KEY);
                return raw ? JSON.parse(raw) : null;
            }
        }

        async function persistBackupState(payload) {
            try {
                const db = await openBackupDb();
                await new Promise((resolve, reject) => {
                    const tx = db.transaction(STORE_NAME, "readwrite");
                    const store = tx.objectStore(STORE_NAME);
                    store.put({
                        id: RECORD_KEY,
                        updatedAt: Date.now(),
                        payload
                    });
                    tx.oncomplete = () => resolve();
                    tx.onerror = () => reject(tx.error);
                    tx.onabort = () => reject(tx.error);
                });
            } catch (_) {
                localStorage.setItem(FALLBACK_STORAGE_KEY, JSON.stringify(payload));
            }
        }

        async function restoreUiState() {
            const savedState = await loadBackupState();
            if (!savedState || typeof savedState !== "object") {
                return;
            }

            const entries = Object.entries(savedState);
            for (let pass = 0; pass < 3; pass++) {
                entries.forEach(([id, value]) => {
                    const componentRoot = document.getElementById(id);
                    if (componentRoot) {
                        writeControlValue(componentRoot, value);
                    }
                });
                await delay(350);
            }
        }

        async function saveUiState() {
            const state = collectUiState();
            await persistBackupState(state);
        }

        async function setupPersistence() {
            await delay(1000);
            await restoreUiState();

            setInterval(() => {
                void saveUiState();
            }, SAVE_INTERVAL_MS);

            window.addEventListener("beforeunload", () => {
                void saveUiState();
            });

            document.addEventListener("visibilitychange", () => {
                if (document.hidden) {
                    void saveUiState();
                }
            });
        }

        void setupPersistence();
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
                create_browser_use_agent_tab(ui_manager)

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
