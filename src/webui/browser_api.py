"""
HTTP API handlers for direct browser control (goto, screenshot, get_url, etc.).
When BROWSER_CDP is set (e.g. startup browser), connect to it on first API call so the browser is visible.
"""
import logging
import os
from typing import Optional

from browser_use.agent.views import ActionModel, ActionResult
from browser_use.controller.views import GoToUrlAction
from browser_use.browser.browser import BrowserConfig
from browser_use.browser.context import BrowserContextConfig

from src.browser.custom_browser import CustomBrowser
from src.browser.launch_config import parse_launch_args
from src.webui.webui_manager import WebuiManager

logger = logging.getLogger(__name__)


def _no_browser_msg() -> str:
    return "Error: Browser not open. Run an agent task first (run_agent) or set BROWSER_CDP with a running browser."


async def _ensure_browser_context_from_cdp(webui_manager: WebuiManager) -> bool:
    """If BROWSER_CDP is set and we have no context yet, connect to the existing browser. Returns True if context is available."""
    if webui_manager.bu_browser_context is not None:
        return True
    cdp_url = (os.getenv("BROWSER_CDP") or "").strip()
    if not cdp_url:
        return False
    try:
        extra_args = []
        launch_args_env = os.getenv("PLAYWRIGHT_LAUNCH_ARGS", "").strip()
        if launch_args_env:
            extra_args.extend(parse_launch_args(launch_args_env))
        chrome_debug_port = int(os.getenv("BROWSER_DEBUGGING_PORT", "9222"))
        window_w = int(os.getenv("RESOLUTION_WIDTH", "1920"))
        window_h = int(os.getenv("RESOLUTION_HEIGHT", "1080"))
        webui_manager.bu_browser = CustomBrowser(
            config=BrowserConfig(
                headless=False,
                disable_security=False,
                browser_binary_path=None,
                extra_browser_args=extra_args,
                chrome_remote_debugging_port=chrome_debug_port,
                wss_url=None,
                cdp_url=cdp_url,
                new_context_config=BrowserContextConfig(window_width=window_w, window_height=window_h),
            )
        )
        webui_manager.bu_browser_context = await webui_manager.bu_browser.new_context(
            config=BrowserContextConfig(window_width=window_w, window_height=window_h)
        )
        logger.info("Connected to browser via BROWSER_CDP for API.")
        return True
    except Exception as e:
        logger.exception("Failed to connect to BROWSER_CDP: %s", e)
        return False


async def api_goto(webui_manager: WebuiManager, url: str) -> str:
    """Navigate the current browser tab to URL. Uses the same controller action as the agent."""
    await _ensure_browser_context_from_cdp(webui_manager)
    ctx = webui_manager.bu_browser_context
    if not ctx:
        return _no_browser_msg()
    url = (url or "").strip()
    if not url:
        return "Error: url is required."
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        controller = webui_manager.bu_controller
        if controller and hasattr(controller, "act"):
            result = await controller.act(
                ActionModel(go_to_url=GoToUrlAction(url=url)),
                browser_context=ctx,
            )
            if isinstance(result, ActionResult) and result.error:
                return f"Error: {result.error}"
            return f"OK: navigated to {url}"
        # Fallback: use context page directly if controller not available
        page = getattr(ctx, "get_current_page", None)
        if callable(page):
            page = await page()
        if page is None and hasattr(ctx, "pages"):
            pages = ctx.pages if not callable(ctx.pages) else await ctx.pages()
            page = pages[0] if pages else None
        if page is None and hasattr(ctx, "new_page"):
            page = await ctx.new_page()
        if page is None:
            return "Error: Could not get or create a page."
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        return f"OK: navigated to {url}"
    except Exception as e:
        logger.exception("api_goto failed")
        return f"Error: {e}"


async def api_get_url(webui_manager: WebuiManager) -> str:
    """Return the current page URL."""
    await _ensure_browser_context_from_cdp(webui_manager)
    ctx = webui_manager.bu_browser_context
    if not ctx:
        return _no_browser_msg()
    try:
        page = getattr(ctx, "get_current_page", None)
        if callable(page):
            page = await page()
        if page is None and hasattr(ctx, "pages"):
            pages = ctx.pages if not callable(ctx.pages) else await ctx.pages()
            page = pages[0] if pages else None
        if page is None:
            return "Error: No page."
        url = getattr(page, "url", None) or (await page.evaluate("() => window.location.href") if hasattr(page, "evaluate") else None)
        return url or "Error: Could not get URL"
    except Exception as e:
        logger.exception("api_get_url failed")
        return f"Error: {e}"


async def api_screenshot(webui_manager: WebuiManager) -> Optional[str]:
    """Take a screenshot of the current page. Returns base64 image or None."""
    await _ensure_browser_context_from_cdp(webui_manager)
    ctx = webui_manager.bu_browser_context
    if not ctx:
        return None
    try:
        if hasattr(ctx, "take_screenshot"):
            out = await ctx.take_screenshot()
            if isinstance(out, str):
                return out
            if isinstance(out, dict) and "base64" in out:
                return out["base64"]
            if hasattr(out, "get"):
                return out.get("base64") or out.get("path")
        return None
    except Exception as e:
        logger.exception("api_screenshot failed")
        return None


async def api_get_title(webui_manager: WebuiManager) -> str:
    """Return the current page title."""
    await _ensure_browser_context_from_cdp(webui_manager)
    ctx = webui_manager.bu_browser_context
    if not ctx:
        return _no_browser_msg()
    try:
        page = getattr(ctx, "get_current_page", None)
        if callable(page):
            page = await page()
        if page is None and hasattr(ctx, "pages"):
            pages = ctx.pages if not callable(ctx.pages) else await ctx.pages()
            page = pages[0] if pages else None
        if page is None:
            return "Error: No page."
        title = getattr(page, "title", None)
        if callable(title):
            title = await title()
        return title or "Error: Could not get title"
    except Exception as e:
        logger.exception("api_get_title failed")
        return f"Error: {e}"
