#!/usr/bin/env python3
"""
Verify Playwright and Chromium work inside the container.
Run: docker compose run --rm browser-use-webui python scripts/verify_playwright.py
"""
import asyncio
import os
import sys

# Ensure /app is on path when run from container
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def main():
    from playwright.async_api import async_playwright

    print("Launching Chromium via Playwright...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = await browser.new_page()
        await page.goto("https://example.com", wait_until="domcontentloaded")
        title = await page.title()
        await browser.close()

    print(f"OK: Page title = {title!r}")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
