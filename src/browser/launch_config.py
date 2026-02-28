"""
Shared browser launch config from environment. Used by the startup browser process
and by the WebUI when building the same args (PLAYWRIGHT_LAUNCH_ARGS, user-data-dir, etc.).
"""
import os
import shlex
from typing import List

from browser_use.browser.browser import BrowserConfig
from browser_use.browser.context import BrowserContextConfig


def parse_launch_args(env_value: str) -> List[str]:
    """Parse PLAYWRIGHT_LAUNCH_ARGS env (space-separated, supports quotes)."""
    if not env_value or not env_value.strip():
        return []
    try:
        return shlex.split(env_value.strip())
    except ValueError:
        return env_value.split()


def get_shared_browser_config(
    *,
    headless: bool = False,
    window_width: int = 1920,
    window_height: int = 1080,
) -> BrowserConfig:
    """
    Build BrowserConfig from environment, with the same parameters the WebUI uses:
    PLAYWRIGHT_LAUNCH_ARGS, BROWSER_USER_DATA (--user-data-dir), BROWSER_DEBUGGING_PORT.
    Use for the startup browser so it matches the WebUI launch exactly.
    """
    extra_args: List[str] = []
    launch_args_env = os.getenv("PLAYWRIGHT_LAUNCH_ARGS", "").strip()
    if launch_args_env:
        extra_args.extend(parse_launch_args(launch_args_env))
    browser_user_data = os.getenv("BROWSER_USER_DATA", "").strip()
    if browser_user_data:
        extra_args.append(f"--user-data-dir={browser_user_data}")

    chrome_debug_port = int(os.getenv("BROWSER_DEBUGGING_PORT", "9223"))

    return BrowserConfig(
        headless=headless,
        disable_security=False,
        browser_binary_path=None,
        extra_browser_args=extra_args,
        chrome_remote_debugging_port=chrome_debug_port,
        wss_url=None,
        cdp_url=None,
        new_context_config=BrowserContextConfig(
            window_width=window_width,
            window_height=window_height,
        ),
    )
