"""
Discovery helpers for building automations from a live page state.

This module lets an agent open a browser profile, navigate to a target page,
pause for manual login/navigation, capture a snapshot, and verify selectors
before generating a reusable YAML config.
"""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.panel import Panel
from rich.table import Table

from core.account_manager import Account
from core.browser import BrowserManager
from core.console import console
from core.interactive import InteractiveSession
from core.snapshot import PageSnapshot


def _slugify(value: str) -> str:
    """Create a compact filesystem-friendly slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:48] or "page"


async def _inspect_selector(page, selector: str, timeout: int) -> dict:
    """Check whether a selector resolves and capture a tiny preview."""
    locator = page.locator(selector)
    count = await locator.count()
    if count == 0:
        return {
            "selector": selector,
            "matched": False,
            "count": 0,
            "visible": False,
            "preview": "",
        }

    first = locator.first
    visible = False
    try:
        await first.wait_for(state="visible", timeout=timeout)
        visible = True
    except Exception:
        visible = False

    preview = ""
    readers = [
        first.inner_text,
        lambda: first.get_attribute("aria-label"),
        lambda: first.get_attribute("placeholder"),
        first.input_value,
    ]
    for reader in readers:
        try:
            value = await reader()
        except Exception:
            continue
        if value:
            preview = " ".join(str(value).split())[:120]
            break

    return {
        "selector": selector,
        "matched": True,
        "count": count,
        "visible": visible,
        "preview": preview,
    }


async def run_discovery_session(
    url: str,
    account: Optional[Account] = None,
    headless: bool = False,
    snapshot_mode: str = "full",
    pause_for_manual: bool = False,
    output_dir: str = "output/discovery",
    selector_checks: Optional[list[str]] = None,
    selector_timeout: int = 3000,
    wait_after_load_ms: int = 0,
    profile_name: Optional[str] = None,
    slow_mo: int = 50,
) -> dict:
    """Launch a live discovery session and save snapshot artifacts."""
    interactive = InteractiveSession()
    profile = account.profile_dir if account else (profile_name or "default")
    proxy = account.proxy if account else None

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    async with BrowserManager(
        headless=headless,
        slow_mo=slow_mo,
        profile_name=profile,
        proxy=proxy,
    ) as browser:
        snapshotter = PageSnapshot(browser.page)
        await browser.goto(url)

        if wait_after_load_ms > 0:
            await asyncio.sleep(wait_after_load_ms / 1000)

        if pause_for_manual:
            interactive.pause(
                "Use the browser to log in or navigate to the exact screen, then press Enter to capture the snapshot..."
            )

        if snapshot_mode == "quick":
            snapshot_data = await snapshotter.quick()
            snapshot_text = await snapshotter.quick_as_text()
        else:
            snapshot_data = await snapshotter.full()
            snapshot_text = snapshotter._format_for_llm(snapshot_data)

        current_url = browser.page.url
        title = await browser.page.title()
        slug = _slugify(title or current_url)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        json_path = output_root / f"{timestamp}_{slug}_{snapshot_mode}.json"
        text_path = output_root / f"{timestamp}_{slug}_{snapshot_mode}.txt"
        screenshot_path = output_root / f"{timestamp}_{slug}.png"

        json_path.write_text(json.dumps(snapshot_data, indent=2, ensure_ascii=False), encoding="utf-8")
        text_path.write_text(snapshot_text, encoding="utf-8")
        await browser.screenshot(str(screenshot_path), full_page=False)

        console.print(Panel(snapshot_text[:4000], title="Discovery Snapshot", border_style="blue"))

        selector_results = []
        for selector in selector_checks or []:
            selector_results.append(await _inspect_selector(browser.page, selector, selector_timeout))

        if selector_results:
            table = Table(title="Selector Checks", show_lines=True)
            table.add_column("Selector", style="cyan")
            table.add_column("Matched", style="green")
            table.add_column("Count", style="magenta")
            table.add_column("Visible", style="yellow")
            table.add_column("Preview", style="white")
            for result in selector_results:
                table.add_row(
                    result["selector"],
                    "yes" if result["matched"] else "no",
                    str(result["count"]),
                    "yes" if result["visible"] else "no",
                    result["preview"],
                )
            console.print(table)

        return {
            "status": "completed",
            "url": current_url,
            "title": title,
            "snapshot_mode": snapshot_mode,
            "snapshot_json": str(json_path),
            "snapshot_text": str(text_path),
            "screenshot": str(screenshot_path),
            "selector_results": selector_results,
        }
