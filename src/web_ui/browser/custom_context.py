import logging

from browser_use.browser.browser import Browser
from browser_use.browser.context import BrowserContext, BrowserContextConfig, BrowserContextState

logger = logging.getLogger(__name__)


class CustomBrowserContext(BrowserContext):
    def __init__(
        self,
        browser: Browser,
        config: BrowserContextConfig | None = None,
        state: BrowserContextState | None = None,
    ):
        super().__init__(browser=browser, config=config, state=state)
