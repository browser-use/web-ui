#!/usr/bin/env python3
"""
Launch Chromium at container startup with the same args as the WebUI (PLAYWRIGHT_LAUNCH_ARGS,
BROWSER_USER_DATA, BROWSER_DEBUGGING_PORT). Chrome is started as a subprocess so it listens
on BROWSER_DEBUGGING_PORT (9223); socat forwards 9222 -> 9223. WebUI/agent connect via
BROWSER_CDP (http://127.0.0.1:9222). Set LAUNCH_BROWSER_AT_STARTUP=true to enable.
Blocks until SIGTERM.
"""
import glob
import os
import signal
import socket
import subprocess
import sys
import time

if os.environ.get("LAUNCH_BROWSER_AT_STARTUP", "").lower() not in ("true", "1", "yes"):
    sys.exit(0)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _clear_stale_profile_lock(user_data_dir: str) -> None:
    """Remove Chromium singleton lock files from a previous run (e.g. old container)."""
    for name in ("SingletonLock", "SingletonSocket", "SingletonCookie"):
        path = os.path.join(user_data_dir, name)
        try:
            if os.path.lexists(path):
                os.unlink(path)
        except OSError:
            pass


def _find_chromium_executable() -> str:
    """Resolve Chromium path from PLAYWRIGHT_BROWSERS_PATH (e.g. /ms-browsers/chromium-1208/chrome-linux64/chrome)."""
    base = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/ms-browsers")
    pattern = os.path.join(base, "chromium-*", "chrome-linux64", "chrome")
    hits = glob.glob(pattern)
    if not hits:
        raise FileNotFoundError(f"Chromium not found at {pattern}")
    return hits[0]


def _wait_for_port(host: str, port: int, timeout_sec: float = 90.0) -> bool:
    """Wait until something listens on host:port (Chrome may take 10–30s to open CDP in headful mode)."""
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=2):
                return True
        except (socket.error, OSError):
            time.sleep(1)
    return False


def main() -> None:
    from src.browser.launch_config import get_shared_browser_config

    config = get_shared_browser_config(
        headless=False,
        window_width=int(os.environ.get("RESOLUTION_WIDTH", "1920")),
        window_height=int(os.environ.get("RESOLUTION_HEIGHT", "1080")),
    )
    port = config.chrome_remote_debugging_port
    args = [f"--remote-debugging-port={port}"]
    # Use a dedicated startup profile so CDP comes up reliably (no stale lock or corrupt state from agent-default)
    user_data_dir = os.environ.get("BROWSER_STARTUP_PROFILE") or "/tmp/startup-browser-profile"
    args.append(f"--user-data-dir={user_data_dir}")
    # Default: headful so the browser is visible in VNC. Set STARTUP_BROWSER_HEADLESS=1 for headless (CDP only, no window).
    headful = os.environ.get("STARTUP_BROWSER_HEADLESS", "").lower() not in ("1", "true", "yes")
    if not headful:
        args.append("--headless=new")
    if config.extra_browser_args:
        for a in config.extra_browser_args:
            if a.startswith("--remote-debugging-port") or a.startswith("--user-data-dir="):
                continue
            # In headful mode, skip extension args so CDP port opens (with extension headful often never opens the port)
            if headful and ("extension" in a.lower() or "stealth" in a):
                continue
            args.append(a)
    # Allow CDP connections from any origin (e.g. WebUI, agent, host via socat)
    args.append("--remote-allow-origins=*")

    os.makedirs(user_data_dir, exist_ok=True)
    _clear_stale_profile_lock(user_data_dir)

    chrome_exe = _find_chromium_executable()
    env = os.environ.copy()
    env.setdefault("DISPLAY", ":99")

    # Open initial page so CDP port becomes ready (Chrome may take 20–30s to open port with extensions)
    args.append("about:blank")

    print(f"Startup browser: launching Chrome (profile={user_data_dir})", flush=True)
    proc = subprocess.Popen(
        [chrome_exe] + args,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=None,
        stderr=None,
    )

    def on_sigterm(*_args: object) -> None:
        proc.terminate()

    signal.signal(signal.SIGTERM, on_sigterm)
    signal.signal(signal.SIGINT, on_sigterm)

    # Headless: port usually ready in 5–15s; headful (no extension) typically 15–35s
    wait_before = 5 if "--headless" in " ".join(args) else 20
    print(f"Startup browser: waiting {wait_before}s then checking 127.0.0.1:{port} ...", flush=True)
    time.sleep(wait_before)
    if not _wait_for_port("127.0.0.1", port, timeout_sec=90):
        print(f"Startup browser: port {port} did not open in time, killing Chrome", flush=True)
        proc.kill()
        sys.exit(1)
    print(f"Startup browser: CDP port {port} is ready", flush=True)
    proc.wait()
    sys.exit(proc.returncode or 0)


if __name__ == "__main__":
    main()
