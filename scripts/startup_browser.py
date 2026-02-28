#!/usr/bin/env python3
"""
Launch Chromium at container startup with the same args as the WebUI (PLAYWRIGHT_LAUNCH_ARGS,
BROWSER_USER_DATA, BROWSER_DEBUGGING_PORT). Uses Playwright directly so the process always
starts; WebUI then connects via BROWSER_CDP. Set LAUNCH_BROWSER_AT_STARTUP=true to enable.
Blocks until SIGTERM.
"""
import asyncio
import os
import signal
import sys

if os.environ.get("LAUNCH_BROWSER_AT_STARTUP", "").lower() not in ("true", "1", "yes"):
    sys.exit(0)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def main():
    from playwright.async_api import async_playwright
    from src.browser.launch_config import get_shared_browser_config

    config = get_shared_browser_config(
        headless=False,
        window_width=int(os.environ.get("RESOLUTION_WIDTH", "1920")),
        window_height=int(os.environ.get("RESOLUTION_HEIGHT", "1080")),
    )
    # Build args: port + PLAYWRIGHT_LAUNCH_ARGS, but drop --user-data-dir (Playwright requires launch_persistent_context for that)
    args = [f"--remote-debugging-port={config.chrome_remote_debugging_port}"]
    user_data_dir = None
    if config.extra_browser_args:
        for a in config.extra_browser_args:
            if a.startswith("--user-data-dir="):
                user_data_dir = a.split("=", 1)[1].strip()
            else:
                args.append(a)

    viewport = {"width": config.new_context_config.window_width, "height": config.new_context_config.window_height}
    if user_data_dir is None:
        user_data_dir = os.path.join(os.environ.get("HOME", "/tmp"), ".browser-use-startup-profile")

    async with async_playwright() as p:
        # Playwright requires launch_persistent_context when using user_data_dir (no --user-data-dir in args)
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,
            args=args,
            viewport=viewport,
        )
        if not context.pages:
            await context.new_page()

        done = asyncio.Event()
        try:
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, done.set)
        except NotImplementedError:
            pass
        await done.wait()

        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
