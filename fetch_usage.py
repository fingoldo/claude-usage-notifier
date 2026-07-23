"""Fetches the claude.ai usage JSON using a real Chrome profile.

claude.ai's /api/organizations/{org}/usage endpoint is authenticated by browser
session cookies, not by an Anthropic API key (the console API key has no concept
of the Pro/Max 5-hour and weekly usage limits). Login (especially "Sign in with
Google") aggressively blocks automation-driven browsers, so the one-time login
step launches a genuinely manual Chrome window (plain subprocess, no CDP, no
Playwright involved) against a dedicated profile directory. Once that profile
holds a valid session, later runs drive it headlessly through Playwright only
to load the usage page - that step merely needs to clear Cloudflare's JS
challenge, which a real Chromium engine does on its own without tripping
Google's much stricter bot detection.
"""

import json
import os
import subprocess
import sys
import time

from playwright.sync_api import sync_playwright

import config

FETCH_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 10

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def _find_chrome() -> str:
    for path in CHROME_CANDIDATES:
        if os.path.exists(path):
            return path
    raise RuntimeError("Google Chrome not found in the usual install locations.")


def _context(playwright, headless: bool):
    config.BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    if headless:
        # Cloudflare's managed challenge detects real headless rendering (even
        # on the genuine Chrome channel) and loops forever. A headed window
        # positioned off-screen uses the same rendering path as a normal tab,
        # so it clears the challenge - it's just never visible to the user.
        # --disable-gpu forces software rendering: Windows can tear down a
        # process's GPU device context when the desktop session locks or the
        # display powers off, which otherwise surfaces as an unpredictable
        # Chrome launch/render failure under Task Scheduler on a locked machine.
        return playwright.chromium.launch_persistent_context(
            str(config.BROWSER_PROFILE_DIR),
            headless=False,
            channel="chrome",
            args=["--window-position=-32000,-32000", "--window-size=1200,900", "--disable-gpu"],
        )
    return playwright.chromium.launch_persistent_context(
        str(config.BROWSER_PROFILE_DIR),
        headless=False,
        channel="chrome",
    )


def ensure_logged_in() -> None:
    """Opens a plain, non-automated Chrome window for a one-time manual login."""
    chrome_path = _find_chrome()
    config.BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen([chrome_path, f"--user-data-dir={config.BROWSER_PROFILE_DIR}", "https://claude.ai/new"])
    print(
        "A normal Chrome window has opened. Log in to claude.ai (Google login included), "
        "then close that Chrome window completely, and press Enter here to continue..."
    )
    input()
    proc.terminate()


def _clear_stale_lock() -> None:
    """Removes Chrome's user-data-dir singleton lock file.

    A prior run that got killed mid-launch (e.g. Task Scheduler firing a new
    instance into a session-locked desktop) can leave this behind, which then
    makes every subsequent launch_persistent_context() fail immediately - not
    a transient issue a plain retry would fix on its own.
    """
    lock_path = config.BROWSER_PROFILE_DIR / "lockfile"
    if lock_path.exists():
        lock_path.unlink(missing_ok=True)


def _fetch_usage_once() -> dict:
    """Returns the parsed usage JSON, raising if the session is not authenticated.

    Uses a real page navigation (not a raw HTTP request) so headless Chromium's
    JS engine can transparently solve Cloudflare's managed challenge and refresh
    the short-lived cf_clearance cookie on its own, the same way a real browser
    tab would. A bare context.request.get() cannot execute that JS and would
    start failing every time cf_clearance expires (roughly every 30min-24h).
    """
    with sync_playwright() as p:
        context = _context(p, headless=True)
        try:
            page = context.new_page()
            page.goto(config.USAGE_URL, wait_until="domcontentloaded")

            try:
                page.wait_for_function(
                    "document.body.innerText.trim().startsWith('{')",
                    timeout=20000,
                )
            except Exception:
                body_preview = page.inner_text("body")[:300]
                if "Log in" in body_preview or "log-in" in page.url:
                    raise RuntimeError("Session expired, redirected to login. " "Run `python fetch_usage.py --login` to log in again.")
                raise RuntimeError(f"Usage endpoint did not return JSON: {body_preview}")

            body_text = page.inner_text("body")
            return json.loads(body_text)
        finally:
            context.close()


def fetch_usage() -> dict:
    """Retries _fetch_usage_once a few times before giving up.

    Covers transient failures - a session-locked desktop denying window
    creation, a leftover profile lock from a killed prior run, a slow
    Cloudflare challenge - that a single attempt wouldn't survive but a second
    one moments later usually does.
    """
    last_error: Exception | None = None
    for attempt in range(1, FETCH_ATTEMPTS + 1):
        try:
            return _fetch_usage_once()
        except RuntimeError:  # noqa: PERF203 - retry-until-success loop; the try/except IS the control flow
            raise  # session/auth problems won't fix themselves on retry
        except Exception as e:
            last_error = e
            if attempt < FETCH_ATTEMPTS:
                _clear_stale_lock()
                time.sleep(RETRY_DELAY_SECONDS)
    raise RuntimeError(f"Failed to fetch usage after {FETCH_ATTEMPTS} attempts: {last_error}") from last_error


if __name__ == "__main__":
    if "--login" in sys.argv:
        ensure_logged_in()
    else:
        print(json.dumps(fetch_usage(), indent=2))
