import json
import logging
import os

from browser_use.browser.browser import Browser, IN_DOCKER
from browser_use.browser.context import BrowserContext, BrowserContextConfig
from typing import Optional
from browser_use.browser.context import BrowserContextState

logger = logging.getLogger(__name__)


class CustomBrowserContext(BrowserContext):
    def __init__(
            self,
            browser: 'Browser',
            config: BrowserContextConfig | None = None,
            state: Optional[BrowserContextState] = None,
    ):
        super(CustomBrowserContext, self).__init__(browser=browser, config=config, state=state)
