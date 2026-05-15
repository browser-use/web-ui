"""
Compatibility layer for browser_use 0.6.0
Provides shims for the old API to work with the new one
"""

from browser_use.browser import BrowserSession, BrowserProfile
from browser_use import Controller, Agent
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class BrowserConfig:
    """Compatibility shim for old BrowserConfig"""
    def __init__(self, 
                 headless: bool = False,
                 disable_security: bool = False,
                 browser_binary_path: Optional[str] = None,
                 extra_browser_args: list = None,
                 wss_url: Optional[str] = None,
                 cdp_url: Optional[str] = None,
                 new_context_config: Optional[Any] = None,
                 **kwargs):
        self.headless = headless
        self.disable_security = disable_security  
        self.browser_binary_path = browser_binary_path
        self.extra_browser_args = extra_browser_args or []
        self.wss_url = wss_url
        self.cdp_url = cdp_url
        self.new_context_config = new_context_config
        self._extra = kwargs

class BrowserContextConfig:
    """Compatibility shim for old BrowserContextConfig"""
    def __init__(self,
                 window_width: int = 1280,
                 window_height: int = 720,
                 trace_path: Optional[str] = None,
                 save_recording_path: Optional[str] = None,
                 save_downloads_path: Optional[str] = None,
                 **kwargs):
        self.window_width = window_width
        self.window_height = window_height
        self.trace_path = trace_path
        self.save_recording_path = save_recording_path
        self.save_downloads_path = save_downloads_path
        self._extra = kwargs
    
    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Compatibility method for pydantic model_dump"""
        return {
            'window_width': self.window_width,
            'window_height': self.window_height,
            'trace_path': self.trace_path,
            'save_recording_path': self.save_recording_path,
            'save_downloads_path': self.save_downloads_path,
            **self._extra
        }

class BrowserState:
    """Compatibility shim for BrowserState"""
    pass

# Re-export the new API classes with compatibility
Browser = BrowserSession
BrowserContext = BrowserSession  # In v0.6.0, context is merged with session