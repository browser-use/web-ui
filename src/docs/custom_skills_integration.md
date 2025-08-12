# Custom Skills Integration for Browser Use Agent

This document outlines the changes made to enable deterministic execution of JSON-based browser automation scenarios in the Browser Use Agent.

## Problem Statement

The Browser Use Agent initially did not properly register custom skills (such as `goto`, `clickCss`, `waitFor`, `waitForUrl`) for use in JSON scenarios. When attempting to run JSON scenarios with these skills, the agent would fall back to built-in actions or fail to execute the steps correctly.

## Solution

We implemented dynamic registration of custom skills as controller actions to enable deterministic execution of JSON-based browser automation scenarios.

### Key Changes

1. **Dynamic Registration of Custom Skills**

   In `src/controller/custom_controller.py`, we added code to dynamically register all skills from `src.custom_skills` as controller actions:

   ```python
   # This allows JSON scenarios to call actions like "goto", "clickCss", etc.
   from src.custom_skills import CUSTOM_SKILLS
   from typing import Any, Dict
   from playwright.async_api import BrowserContext

   for _skill_name, _skill_func in CUSTOM_SKILLS.items():
       # Create a wrapper that adapts the controller action signature
       # Add explicit type annotations to avoid Pydantic JSON schema errors
       # Avoid leading underscore in function name to prevent Pydantic errors
       async def skill_wrapper(*args: Any, browser: BrowserContext, _func=_skill_func) -> Dict[str, Any]:
           # Original skill expects (ctx, args_list)
           return await _func(browser, list(args))

       # Avoid overwriting if an action with the same name already exists
       if _skill_name not in self.registry.registry.actions:
           self.registry.action(_skill_name)(skill_wrapper)
   ```

2. **Fixed Pydantic JSON Schema Error**

   We encountered two issues with Pydantic when generating JSON schemas for the dynamically created wrapper functions:

   - **Missing Type Annotations**: Added proper type annotations to the wrapper function
   - **Leading Underscore in Function Name**: Renamed the function from `_wrapper` to `skill_wrapper` to avoid the Pydantic error: "Fields must not use names with leading underscores"

## Usage

With these changes, JSON scenarios can now use custom skills directly. Here's an example scenario that navigates through Wikipedia and compares language counts:

```json
{
  "steps": [
    {
      "skill": "goto",
      "args": ["https://www.wikipedia.org/"]
    },
    {
      "skill": "waitForUrl",
      "args": ["wikipedia.org", 10000]
    },
    {
      "skill": "waitFor",
      "args": [".central-featured", 5000]
    },
    {
      "skill": "evaluate",
      "args": [
        "(() => { const languages = document.querySelectorAll('.central-featured-lang'); const count = languages.length; localStorage.setItem('languageCount', count); return { mainPageLanguageCount: count }; })()"
      ]
    },
    {
      "skill": "waitFor",
      "args": ["a[href='//meta.wikimedia.org/wiki/List_of_Wikipedias']", 5000]
    },
    {
      "skill": "clickCss",
      "args": ["a[href='//meta.wikimedia.org/wiki/List_of_Wikipedias']"]
    },
    {
      "skill": "waitForUrl",
      "args": ["meta.wikimedia.org/wiki/List_of_Wikipedias", 10000]
    },
    {
      "skill": "waitFor",
      "args": [".wikitable", 5000]
    },
    {
      "skill": "evaluate",
      "args": [
        "(() => { const rows = document.querySelectorAll('.wikitable tr'); const activeLanguages = Array.from(rows).filter(row => row.querySelector('td')).length; const mainPageCount = localStorage.getItem('languageCount'); return { mainPageLanguageCount: mainPageCount, listPageLanguageCount: activeLanguages, note: 'The counts may differ as the main page shows top languages while the list page shows all languages' }; })()"
      ]
    }
  ]
}
```

## Available Custom Skills

The following custom skills are now available for use in JSON scenarios:

- **goto**: Navigate to a URL
- **clickCss**: Click an element by CSS selector
- **waitFor**: Wait for an element to reach a specific state
- **waitForUrl**: Wait for the URL to contain a specific string

## Troubleshooting

If you encounter issues with JSON scenarios:

1. Check the browser console for errors
2. Verify that selectors are correct for the target website
3. Adjust timeout values if elements take longer to load
4. Use the `evaluate` skill to debug page state with JavaScript
