# Browser-Use CLI and Python with Docker CDP

This guide explains how to use **Browser-Use CLI** and **Python API** with the browser running inside the browser-use-webui Docker container (Chrome DevTools Protocol on port 9222).

## Prerequisites

1. **Container running** with CDP exposed:
   ```bash
   cd /path/to/browser-use-webui
   docker compose up -d
   ```

2. **Browser must be running inside the container** so that port 9222 is active. Either:
   - Run at least one agent task in the Web UI (http://localhost:7788), then leave the browser open, or
   - Use the container as usual; CDP is available whenever a task has started the browser.

3. **Verify CDP from the host:**
   ```bash
   curl -s http://127.0.0.1:9222/json | head -20
   ```
   You should see JSON with browser tabs. If you get "Connection refused" or "Connection reset", start a task in the Web UI first.

---

## Option 1: Python (recommended for CDP)

Use the browser-use Python API and connect to the container’s browser via CDP.

### Setup on the host

```bash
# Create a venv and install browser-use
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install browser-use python-dotenv
```

### .env on the host

Create or edit `.env` in the same directory as your script:

```env
# Any LLM key you need for Agent (e.g. for run())
OPENAI_API_KEY=sk-...

# Optional: point at container CDP (Python script can pass cdp_url explicitly instead)
BROWSER_CDP=http://127.0.0.1:9222
```

### Connect to the container’s browser

```python
import asyncio
from browser_use import Agent, Browser, ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

# CDP URL: use 127.0.0.1:9222 when Docker maps 9222 to the host
CDP_URL = "http://127.0.0.1:9222"

async def main():
    browser = Browser(cdp_url=CDP_URL)
    # Use the shared browser for automation
    agent = Agent(
        task="Open example.com and return the page title",
        llm=ChatOpenAI(model="gpt-4o-mini"),
        browser=browser,
    )
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())
```

If the host is not the same machine as the server (e.g. you’re on a laptop and the container runs on a server), replace `127.0.0.1` with the server’s IP or hostname:

```python
CDP_URL = "http://YOUR_SERVER_IP:9222"
```

---

## Option 2: Browser-Use CLI

The browser-use CLI can use a **remote** (cloud) browser or a **local** one. To use the **container’s browser**, the CLI must connect via CDP.

### If your CLI supports CDP

- **Environment variable:** Try setting the CDP URL before running the CLI:
  ```bash
  export BROWSER_CDP=http://127.0.0.1:9222
  browser-use open https://example.com
  ```
  Whether this works depends on your CLI version; if it ignores `BROWSER_CDP`, use Python (Option 1).

- **Explicit CDP flag:** If the CLI has a `--cdp` or `--browser cdp` style option, use it, for example:
  ```bash
  browser-use --cdp http://127.0.0.1:9222 open https://example.com
  ```
  Check with:
  ```bash
  browser-use --help
  ```

### If the CLI has no CDP mode

Use one of these:

1. **Python (Option 1)** for any automation that must use the container’s browser.
2. **Run the CLI inside the container** so it uses the same Chromium as the Web UI (no CDP needed from the host):
   ```bash
   docker compose exec browser-use-webui bash
   # Inside container (ensure browser-use is installed):
   uv pip install browser-use
   uvx browser-use install
   export OPENAI_API_KEY=...
   browser-use --browser chromium open https://example.com
   browser-use state
   ```
   This uses a **new** browser inside the container, not the same window as the Web UI. To control the **same** browser as the Web UI, you must use CDP from the host (Python or CLI with CDP support).

---

## Summary

| Goal                         | Method                                                                 |
|-----------------------------|-------------------------------------------------------------------------|
| Use container browser from host | **Python** with `Browser(cdp_url="http://127.0.0.1:9222")`             |
| CLI with container CDP      | Set `BROWSER_CDP=http://127.0.0.1:9222` or use `--cdp` if supported    |
| CLI in container (own browser) | `docker compose exec browser-use-webui ...` and run CLI inside         |

Port **9222** is forwarded from the container to the host only when the container is up; the browser inside the container must be started (e.g. by running a task in the Web UI) for CDP to respond.
