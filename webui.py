import argparse
import logging
import signal
import socket
import sys
from contextlib import closing

from dotenv import load_dotenv

from src.web_ui.webui.interface import create_ui, theme_map

load_dotenv()

logger = logging.getLogger(__name__)


def is_port_available(host: str, port: int) -> bool:
    """Check if a port is available on the given host."""
    try:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            return result != 0  # Port is available if connection failed
    except Exception:
        return False


def find_available_port(host: str, start_port: int, max_attempts: int = 10) -> int:
    """Find an available port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        if is_port_available(host, port):
            return port
    raise OSError(
        f"Could not find an available port in range {start_port}-{start_port + max_attempts - 1}"
    )


def setup_signal_handlers(demo):
    """Setup graceful shutdown handlers."""

    def signal_handler(sig, frame):
        print("\n🛑 Shutting down gracefully...")
        try:
            demo.close()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def main():
    parser = argparse.ArgumentParser(
        description="Browser Use WebUI - AI-Powered Browser Automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python webui.py                    # Start with defaults (127.0.0.1:7788)
  python webui.py --port 8080        # Use custom port
  python webui.py --ip 0.0.0.0       # Expose to network
  python webui.py --theme Soft       # Use different theme
  python webui.py --auto-port        # Auto-find available port
        """,
    )
    parser.add_argument(
        "--ip", type=str, default="127.0.0.1", help="IP address to bind to (default: 127.0.0.1)"
    )
    parser.add_argument("--port", type=int, default=7788, help="Port to listen on (default: 7788)")
    parser.add_argument(
        "--theme",
        type=str,
        default="Ocean",
        choices=theme_map.keys(),
        help="Theme to use for the UI (default: Ocean)",
    )
    parser.add_argument(
        "--auto-port",
        action="store_true",
        help="Automatically find an available port if specified port is in use",
    )
    parser.add_argument("--share", action="store_true", help="Create a public Gradio share link")
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug mode with detailed logging"
    )
    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    print("\n" + "=" * 70)
    print("🌐 Browser Use WebUI - AI-Powered Browser Automation")
    print("=" * 70)

    # Check if port is available
    selected_port = args.port
    if not is_port_available(args.ip, selected_port):
        if args.auto_port:
            print(f"⚠️  Port {selected_port} is already in use, finding alternative...")
            try:
                selected_port = find_available_port(args.ip, selected_port + 1)
                print(f"✅ Found available port: {selected_port}")
            except OSError as e:
                print(f"❌ Error: {e}")
                print("\n💡 Try one of these:")
                print(f"   - Stop the process using port {args.port}")
                print("   - Use a different port: python webui.py --port 8080")
                print("   - Use --auto-port flag to find available port automatically")
                sys.exit(1)
        else:
            print(f"❌ Error: Port {selected_port} is already in use!")
            print("\n💡 Try one of these:")
            print(f"   1. Stop the existing process on port {selected_port}")
            print("   2. Use a different port: python webui.py --port 8080")
            print("   3. Use auto-port selection: python webui.py --auto-port")
            sys.exit(1)

    try:
        print("\n🚀 Starting server...")
        print(f"   • Theme: {args.theme}")
        print(f"   • Host: {args.ip}")
        print(f"   • Port: {selected_port}")
        if args.share:
            print("   • Share: Enabled (public link will be generated)")

        # Create and launch the UI
        demo = create_ui(theme_name=args.theme)

        # Setup graceful shutdown
        setup_signal_handlers(demo)

        print("\n" + "=" * 70)
        print(f"✅ Server running at: http://{args.ip}:{selected_port}")
        if args.ip == "127.0.0.1":
            print(f"   Local access: http://localhost:{selected_port}")
        print("=" * 70)
        print("\n💡 Quick Tips:")
        print("   • Press Ctrl+C to stop the server")
        print("   • Press '?' in the UI to see keyboard shortcuts")
        print("   • Check the Quick Start tab for preset configurations")
        print("\n📚 Documentation: https://github.com/savagelysubtle/web-ui-1")
        print("-" * 70 + "\n")

        # Launch with error handling
        demo.queue().launch(
            server_name=args.ip,
            server_port=selected_port,
            share=args.share,
            show_error=True,
            quiet=False,
        )

    except KeyboardInterrupt:
        print("\n🛑 Shutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=args.debug)
        print(f"\n❌ Error starting server: {e}")
        if not args.debug:
            print("💡 Run with --debug flag for detailed error information")
        sys.exit(1)


if __name__ == "__main__":
    main()
