import gradio as gr

from src.web_ui.webui.webui_manager import WebuiManager


def create_load_save_config_tab(webui_manager: WebuiManager):
    """
    Creates a load and save config tab.
    """
    tab_components = {}

    config_file = gr.File(
        label="Load UI Settings from json", file_types=[".json"], interactive=True
    )
    with gr.Row():
        load_config_button = gr.Button("Load Config", variant="primary")
        save_config_button = gr.Button("Save UI Settings", variant="primary")

    config_status = gr.Textbox(label="Status", lines=2, interactive=False)

    tab_components.update(
        {
            "load_config_button": load_config_button,
            "save_config_button": save_config_button,
            "config_status": config_status,
            "config_file": config_file,
        }
    )

    webui_manager.add_components("load_save_config", tab_components)

    def save_config_wrapper(*args):
        """Wrapper for save_config that accepts individual component values."""
        # Convert individual component values to a components dict
        components_dict = {}
        all_components = webui_manager.get_components()
        for i, comp in enumerate(all_components):
            if i < len(args):
                components_dict[comp] = args[i]
        return webui_manager.save_config(components_dict)

    save_config_button.click(
        fn=save_config_wrapper,
        inputs=list(webui_manager.get_components()),
        outputs=[config_status],
    )

    load_config_button.click(
        fn=webui_manager.load_config,
        inputs=[config_file],
        outputs=webui_manager.get_components(),
    )
