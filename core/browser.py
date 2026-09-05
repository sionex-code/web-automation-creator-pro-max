"""
Browser Manager — Patchright browser lifecycle management.

Handles launching, persistent contexts, multi-account profiles,
and clean teardown. Uses Chrome channel for maximum stealth.
"""

import asyncio
import os
import sys
import subprocess
from pathlib import Path
from typing import Optional

from core.console import console

# ---------------------------------------------------------------------------
# Patchright auto-installer
# ---------------------------------------------------------------------------

def ensure_patchright_installed() -> None:
    """Install patchright + browser binaries if missing."""
    try:
        import patchright  # noqa: F401
        console.print("[green]✓[/green] patchright already installed")
    except ImportError:
        console.print("[yellow]⏳[/yellow] Installing patchright …")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "patchright", "-q"])
        console.print("[green]✓[/green] patchright installed")

    # Ensure chrome binary is available
    try:
        subprocess.check_call(
            [sys.executable, "-m", "patchright", "install", "chrome"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        console.print("[green]✓[/green] Chrome binary ready")
    except Exception:
        console.print("[yellow]⚠[/yellow] Chrome binary install skipped (may already exist)")


# ---------------------------------------------------------------------------
# Browser Manager
# ---------------------------------------------------------------------------

class BrowserManager:
    """Manages Patchright browser instances with persistent profiles."""

    PROFILES_DIR = Path("profiles")

    def __init__(
        self,
        headless: bool = False,
        slow_mo: int = 0,
        profile_name: Optional[str] = None,
        proxy: Optional[dict] = None,
        viewport: Optional[dict] = None,
    ):
        self.headless = headless
        self.slow_mo = slow_mo
        self.profile_name = profile_name or "default"
        self.proxy = proxy
        self.viewport = viewport or {"width": 1280, "height": 800}
        self._playwright = None
        self._context = None
        self._page = None

    def _resolve_profile_dir(self) -> Path:
        """Resolve a profile name or path without double-prefixing profiles/."""
        raw_path = Path(self.profile_name)
        if raw_path.is_absolute():
            return raw_path
        if len(raw_path.parts) > 1 or raw_path.parts[:1] == (self.PROFILES_DIR.name,):
            return raw_path
        return self.PROFILES_DIR / raw_path

    # ── Lifecycle ──────────────────────────────────────────────────────────

    async def launch(self):
        """Launch browser with persistent context for the given profile."""
        from patchright.async_api import async_playwright

        self._playwright = await async_playwright().start()

        profile_dir = self._resolve_profile_dir()
        profile_dir.mkdir(parents=True, exist_ok=True)

        launch_opts = {
            "user_data_dir": str(profile_dir.resolve()),
            "channel": "chrome",
            "headless": self.headless,
            "slow_mo": self.slow_mo,
            "viewport": self.viewport,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        }

        if self.proxy:
            launch_opts["proxy"] = self.proxy

        self._context = await self._playwright.chromium.launch_persistent_context(**launch_opts)

        # Use existing page or create one
        if self._context.pages:
            self._page = self._context.pages[0]
        else:
            self._page = await self._context.new_page()

        console.print(f"[green]✓[/green] Browser launched — profile: [cyan]{profile_dir}[/cyan]")
        return self

    async def close(self):
        """Gracefully close browser."""
        if self._context:
            await self._context.close()
        if self._playwright:
            await self._playwright.stop()
        console.print("[dim]Browser closed.[/dim]")

    # ── Page helpers ───────────────────────────────────────────────────────

    @property
    def page(self):
        return self._page

    @property
    def context(self):
        return self._context

    async def new_page(self):
        """Create a new tab."""
        self._page = await self._context.new_page()
        return self._page

    async def goto(self, url: str, wait_until: str = "domcontentloaded"):
        """Navigate to URL with network-idle fallback for long-polling apps."""
        console.print(f"[blue]→[/blue] Navigating to [underline]{url}[/underline]")

        initial_wait = "domcontentloaded" if wait_until == "networkidle" else wait_until
        await self._page.goto(url, wait_until=initial_wait)

        if wait_until == "networkidle":
            try:
                await self._page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                console.print("[yellow]⚠[/yellow] Network idle not reached; continuing with current page state")

        console.print(f"[green]✓[/green] Page loaded: {await self._page.title()}")

    async def screenshot(self, path: str = "screenshot.png", full_page: bool = False):
        """Take a screenshot of the current page."""
        await self._page.screenshot(path=path, full_page=full_page)
        console.print(f"[green]✓[/green] Screenshot saved: {path}")
        return path

    # ── Context manager ────────────────────────────────────────────────────

    async def __aenter__(self):
        await self.launch()
        return self

    async def __aexit__(self, *args):
        await self.close()
