import asyncio
import pdb

from playwright.async_api import Browser as PlaywrightBrowser
from playwright.async_api import (
    BrowserContext as PlaywrightBrowserContext,
)
from playwright.async_api import (
    Playwright,
    async_playwright,
)
from browser_use.browser.browser import Browser, IN_DOCKER
from browser_use.browser.context import BrowserContext, BrowserContextConfig
from playwright.async_api import BrowserContext as PlaywrightBrowserContext
import logging

from browser_use.browser.chrome import (
    CHROME_ARGS,
    CHROME_DETERMINISTIC_RENDERING_ARGS,
    CHROME_DISABLE_SECURITY_ARGS,
    CHROME_DOCKER_ARGS,
    CHROME_HEADLESS_ARGS,
)
from browser_use.browser.context import BrowserContext, BrowserContextConfig
from browser_use.browser.utils.screen_resolution import get_screen_resolution, get_window_adjustments
from browser_use.utils import time_execution_async
import socket

from .custom_context import CustomBrowserContext, CustomBrowserContextConfig

logger = logging.getLogger(__name__)


class CustomBrowser(Browser):

    async def new_context(self, config: CustomBrowserContextConfig | None = None) -> CustomBrowserContext:
        """Create a browser context"""
        browser_config = self.config.model_dump() if self.config else {}
        context_config = config.model_dump() if config else {}
        merged_config = {**browser_config, **context_config}
        return CustomBrowserContext(config=CustomBrowserContextConfig(**merged_config), browser=self)

    async def _setup_builtin_browser(self, playwright: Playwright) -> PlaywrightBrowser:
        """Sets up and returns a Playwright Browser instance with anti-detection measures."""
        assert self.config.browser_binary_path is None, 'browser_binary_path should be None if trying to use the builtin browsers'

        if self.config.headless:
            screen_size = {'width': 1920, 'height': 1080}
            offset_x, offset_y = 0, 0
        else:
            screen_size = get_screen_resolution()
            offset_x, offset_y = get_window_adjustments()

        chrome_args = {
            *CHROME_ARGS,
            *(CHROME_DOCKER_ARGS if IN_DOCKER else []),
            *(CHROME_HEADLESS_ARGS if self.config.headless else []),
            *(CHROME_DISABLE_SECURITY_ARGS if self.config.disable_security else []),
            *(CHROME_DETERMINISTIC_RENDERING_ARGS if self.config.deterministic_rendering else []),
            f'--window-position={offset_x},{offset_y}',
            *self.config.extra_browser_args,
        }
        contain_window_size = False
        for arg in self.config.extra_browser_args:
            if "--window-size" in arg:
                contain_window_size = True
                break
        if not contain_window_size:
            chrome_args.add(f'--window-size={screen_size["width"]},{screen_size["height"]}')

        # check if port 9222 is already taken, if so remove the remote-debugging-port arg to prevent conflicts
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', 9222)) == 0:
                chrome_args.remove('--remote-debugging-port=9222')

        browser_class = getattr(playwright, self.config.browser_class)
        args = {
            'chromium': list(chrome_args),
            'firefox': [
                *{
                    '-no-remote',
                    *self.config.extra_browser_args,
                }
            ],
            'webkit': [
                *{
                    '--no-startup-window',
                    *self.config.extra_browser_args,
                }
            ],
        }

        browser = await browser_class.launch(
            headless=self.config.headless,
            args=args[self.config.browser_class],
            proxy=self.config.proxy.model_dump() if self.config.proxy else None,
            handle_sigterm=False,
            handle_sigint=False,
        )
        return browser
