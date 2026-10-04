from dotenv import load_dotenv
load_dotenv()
import argparse
import logging
import os

import gradio as gr
import uvicorn

from src.webui.interface import theme_map, create_ui

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Gradio WebUI for Browser Agent")
    parser.add_argument("--ip", type=str, default=os.getenv("WEBUI_HOST", "127.0.0.1"), help="IP address to bind to")
    # PaaS hosts such as Railway, Render and Heroku route traffic to the port given in $PORT
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT") or os.getenv("WEBUI_PORT") or 7788),
                        help="Port to listen on")
    parser.add_argument("--theme", type=str, default="Ocean", choices=theme_map.keys(), help="Theme to use for the UI")
    parser.add_argument("--enable-api", action="store_true",
                        default=os.getenv("ENABLE_BRIDGE_API", "false").lower() in ("1", "true", "yes"),
                        help="Serve the REST bridge (/api/v1) used by n8n and other HTTP clients")
    args = parser.parse_args()

    demo = create_ui(theme_name=args.theme)

    if not args.enable_api:
        demo.queue().launch(server_name=args.ip, server_port=args.port)
        return

    from src.api.bridge import create_api_app

    if not os.getenv("BRIDGE_API_TOKEN"):
        logger.warning("REST bridge is enabled without BRIDGE_API_TOKEN; /api/v1 accepts unauthenticated requests")
    app = gr.mount_gradio_app(create_api_app(), demo.queue(), path="")
    uvicorn.run(app, host=args.ip, port=args.port)


if __name__ == '__main__':
    main()
