from typing import Dict, Any, Callable, Awaitable, List
from .click_helper import ClickHelper

# Dictionary to store registered skills
CUSTOM_SKILLS: Dict[str, Callable[..., Awaitable[Dict[str, Any]]]] = {}

def register_skill(name: str):
    """Decorator to register a new skill function"""
    def decorator(func):
        CUSTOM_SKILLS[name] = func
        return func
    return decorator

def get_custom_skill(name: str) -> Callable[..., Awaitable[Dict[str, Any]]]:
    """Get a registered custom skill by name"""
    return CUSTOM_SKILLS.get(name)

# Register our click helper as a skill
@register_skill("clickCss")
async def click_css_skill(ctx, args: List[Any]) -> Dict[str, Any]:
    """
    Skill to click an element by CSS selector with reliability enhancements.
    
    Args:
        ctx: Browser context
        args: List containing [selector, x (optional), y (optional)]
        
    Returns:
        Dict with status and message
    """
    return await ClickHelper.click_css(ctx, args)

# Register a goto skill to match the example
@register_skill("goto")
async def goto_skill(ctx, args: List[Any]) -> Dict[str, Any]:
    """
    Navigate to a URL.
    
    Args:
        ctx: Browser context
        args: List containing [url]
    """
    if not args or len(args) < 1:
        return {"status": "error", "message": "Missing required argument: url"}
    
    try:
        url = args[0]
        await ctx.page.goto(url, timeout=30000)
        return {"status": "success", "message": f"Navigated to {url}"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to navigate to {args[0]}: {str(e)}"}

# Register a waitFor skill
@register_skill("waitFor")
async def wait_for_skill(ctx, args: List[Any]) -> Dict[str, Any]:
    """
    Wait for an element to reach a specific state.
    
    Args:
        ctx: Browser context
        args: List containing [selector, state, timeout_ms]
    """
    if len(args) < 2:
        return {"status": "error", "message": "Missing required arguments: selector and state"}
    
    selector = args[0]
    state = args[1]  # 'attached', 'detached', 'visible', 'hidden'
    timeout = args[2] if len(args) > 2 else 5000  # Default 5 seconds
    
    try:
        if state == 'detached':
            # Wait for element to be removed from DOM
            await ctx.page.wait_for_selector(selector, state='detached', timeout=timeout)
        else:
            # Wait for element to be in specified state
            await ctx.page.wait_for_selector(selector, state=state, timeout=timeout)
        
        return {"status": "success", "message": f"Element {selector} reached state {state}"}
    except Exception as e:
        return {"status": "error", "message": f"Wait for {selector} {state} failed: {str(e)}"}

# Register a waitForUrl skill
@register_skill("waitForUrl")
async def wait_for_url_skill(ctx, args: List[Any]) -> Dict[str, Any]:
    """
    Wait for the URL to contain a specific string.
    
    Args:
        ctx: Browser context
        args: List containing [url_fragment, timeout_ms]
    """
    if not args:
        return {"status": "error", "message": "Missing required argument: url_fragment"}
    
    url_fragment = args[0]
    timeout = args[1] if len(args) > 1 else 7000  # Default 7 seconds
    
    try:
        await ctx.page.wait_for_url(
            f"*{url_fragment}*",
            timeout=timeout,
            wait_until="networkidle"
        )
        return {"status": "success", "message": f"URL contains {url_fragment}"}
    except Exception as e:
        return {"status": "error", "message": f"URL did not contain {url_fragment}: {str(e)}"}

# Export all skills
__all__ = [
    'CUSTOM_SKILLS', 
    'register_skill', 
    'get_custom_skill', 
    'click_css_skill',
    'goto_skill',
    'wait_for_skill',
    'wait_for_url_skill'
]
