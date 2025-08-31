from typing import Any, Dict, List, Optional
from dataclasses import dataclass

@dataclass
class ClickHelper:
    """Helper class for reliable clicking with hover"""
    
    @staticmethod
    async def click_css(ctx, args: List[Any]) -> Dict[str, Any]:
        """
        Click an element by CSS selector with reliability enhancements.
        
        Args:
            ctx: The browser context
            args: List containing [selector, x (optional), y (optional)]
            
        Returns:
            Dict with status and message
        """
        if not args or len(args) < 1:
            return {"status": "error", "message": "Missing required argument: selector"}
            
        selector = args[0]
        x = args[1] if len(args) > 1 else 5
        y = args[2] if len(args) > 2 else 5
        
        try:
            page = ctx.page
            el = page.locator(selector)
            await el.wait_for(state='visible', timeout=5000)
            await page.mouse.move(20, 20)  # Move to neutral position
            await el.hover()  # Hover over the element
            await el.click(position={'x': x, 'y': y}, force=True)
            
            return {"status": "success", "message": f"Clicked {selector}"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to click {selector}: {str(e)}"}
