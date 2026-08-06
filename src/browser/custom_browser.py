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

from .custom_context import CustomBrowserContext

logger = logging.getLogger(__name__)


class CustomBrowser(Browser):
    
    async def async_start(self):
        """Start the browser instance asynchronously"""
        if hasattr(self, '_browser') and self._browser:
            logger.info("Browser already started")
            return
        
        try:
            # Create Playwright instance and launch browser
            self._playwright = await async_playwright().start()
            
            # Check if external browser path is specified
            if self.config.browser_binary_path:
                self._browser = await self._setup_external_browser(self._playwright)
            else:
                self._browser = await self._setup_builtin_browser(self._playwright)
                
            logger.info("Browser started successfully")
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            raise

    async def close(self):
        """Close the browser and clean up resources"""
        try:
            if hasattr(self, '_browser') and self._browser:
                await self._browser.close()
                logger.info("Browser closed")
            if hasattr(self, '_playwright') and self._playwright:
                await self._playwright.stop()
                logger.info("Playwright stopped")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")

    async def create_context(self, config: BrowserContextConfig | None = None) -> CustomBrowserContext:
        """Create a browser context (alias for new_context for compatibility)"""
        return await self.new_context(config)

    async def new_context(self, config: BrowserContextConfig | None = None) -> CustomBrowserContext:
        """Create a browser context"""
        # Ensure browser is started
        if not hasattr(self, '_browser') or not self._browser:
            await self.async_start()
            
        browser_config = self.config.model_dump() if self.config else {}
        context_config = config.model_dump() if config else {}
        merged_config = {**browser_config, **context_config}
        return CustomBrowserContext(config=BrowserContextConfig(**merged_config), browser=self)

    async def _setup_external_browser(self, playwright: Playwright) -> PlaywrightBrowser:
        """Sets up and returns an external Browser instance (like Chrome)."""
        assert self.config.browser_binary_path is not None, 'browser_binary_path should be set for external browsers'
        
        # Use configured window size
        if (
                not self.config.headless
                and hasattr(self.config, 'new_context_config')
                and hasattr(self.config.new_context_config, 'window_width')
                and hasattr(self.config.new_context_config, 'window_height')
        ):
            screen_size = {
                'width': self.config.new_context_config.window_width,
                'height': self.config.new_context_config.window_height,
            }
            offset_x, offset_y = get_window_adjustments()
        elif self.config.headless:
            screen_size = {'width': 1920, 'height': 1080}
            offset_x, offset_y = 0, 0
        else:
            screen_size = get_screen_resolution()
            offset_x, offset_y = get_window_adjustments()

        # Build chrome args for external browser
        chrome_args = [
            f'--remote-debugging-port={self.config.chrome_remote_debugging_port}',
            *CHROME_ARGS,
            *(CHROME_DOCKER_ARGS if IN_DOCKER else []),
            *(CHROME_HEADLESS_ARGS if self.config.headless else []),
            *(CHROME_DISABLE_SECURITY_ARGS if self.config.disable_security else []),
            *(CHROME_DETERMINISTIC_RENDERING_ARGS if self.config.deterministic_rendering else []),
            f'--window-position={offset_x},{offset_y}',
            f'--window-size={screen_size["width"]},{screen_size["height"]}',
        ]
        
        # Add extra browser args if provided
        if self.config.extra_browser_args:
            chrome_args.extend(self.config.extra_browser_args)

        logger.info(f"Launching external browser: {self.config.browser_binary_path}")
        browser = await playwright.chromium.launch(
            executable_path=self.config.browser_binary_path,
            headless=self.config.headless,
            args=chrome_args,
            channel=None,  # Don't use channel for external browsers
        )
        return browser

    async def _setup_builtin_browser(self, playwright: Playwright) -> PlaywrightBrowser:
        """Sets up and returns a Playwright Browser instance with anti-detection measures."""
        assert self.config.browser_binary_path is None, 'browser_binary_path should be None if trying to use the builtin browsers'

        # Use the configured window size from new_context_config if available
        if (
                not self.config.headless
                and hasattr(self.config, 'new_context_config')
                and hasattr(self.config.new_context_config, 'window_width')
                and hasattr(self.config.new_context_config, 'window_height')
        ):
            screen_size = {
                'width': self.config.new_context_config.window_width,
                'height': self.config.new_context_config.window_height,
            }
            offset_x, offset_y = get_window_adjustments()
        elif self.config.headless:
            screen_size = {'width': 1920, 'height': 1080}
            offset_x, offset_y = 0, 0
        else:
            screen_size = get_screen_resolution()
            offset_x, offset_y = get_window_adjustments()

        chrome_args = {
            f'--remote-debugging-port={self.config.chrome_remote_debugging_port}',
            *CHROME_ARGS,
            *(CHROME_DOCKER_ARGS if IN_DOCKER else []),
            *(CHROME_HEADLESS_ARGS if self.config.headless else []),
            *(CHROME_DISABLE_SECURITY_ARGS if self.config.disable_security else []),
            *(CHROME_DETERMINISTIC_RENDERING_ARGS if self.config.deterministic_rendering else []),
            f'--window-position={offset_x},{offset_y}',
            f'--window-size={screen_size["width"]},{screen_size["height"]}',
            *self.config.extra_browser_args,
        }

        # check if chrome remote debugging port is already taken,
        # if so remove the remote-debugging-port arg to prevent conflicts
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', self.config.chrome_remote_debugging_port)) == 0:
                chrome_args.remove(f'--remote-debugging-port={self.config.chrome_remote_debugging_port}')

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
            channel='chromium',  # https://github.com/microsoft/playwright/issues/33566
            headless=self.config.headless,
            args=args[self.config.browser_class],
            proxy=self.config.proxy.model_dump() if self.config.proxy else None,
            handle_sigterm=False,
            handle_sigint=False,
        )
        return browser
