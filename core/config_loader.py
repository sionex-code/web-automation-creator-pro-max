"""
Config Loader — Parse & validate YAML automation configs.

Configs define step-by-step automation flows with conditions,
selectors, LLM prompts, and verification logic.
"""

import yaml
from pathlib import Path
from typing import Any, Optional

from rich.table import Table

from core.console import console


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

STEP_TYPES = {
    "goto",           # Navigate to URL
    "click",          # Click an element
    "type",           # Type text into an input
    "wait",           # Wait for selector / timeout
    "snapshot",       # Take page snapshot & feed to LLM
    "screenshot",     # Save a screenshot
    "llm_generate",   # Ask LLM to generate content
    "llm_decide",     # Ask LLM to make a decision from snapshot
    "user_input",     # Ask user for input at runtime
    "verify",         # Verify an element/text exists on page
    "js_eval",        # Execute raw JS on page
    "conditional",    # If/else branching
    "loop",           # Repeat steps N times or until condition
    "scroll",         # Scroll the page
    "press",          # Press keyboard key
    "select",         # Select dropdown option
    "upload",         # Upload file
    "extract",        # Extract data from page into variable
    "save_data",      # Save extracted data to file
    "console_log",    # Print a resolved message to the console
    "read_markdown",  # Read a markdown file into article variables
    "set_content",    # Set plain text or HTML into an element
    "extract_published_link",  # Capture the published LinkedIn/article URL
    "import_cookies",  # Import browser cookies from Cookie-Editor JSON
    "save_json",      # Save structured JSON or string data to a file
    "load_json",      # Load structured JSON from disk into a runtime variable
    "for_each",       # Iterate over a list variable and execute nested steps
}


# ---------------------------------------------------------------------------
# Config Loader
# ---------------------------------------------------------------------------

class AutomationConfig:
    """Represents a loaded & validated automation config."""

    def __init__(self, raw: dict, source_path: Optional[str] = None):
        self.raw = raw
        self.source_path = source_path
        self.name: str = raw.get("name", "Unnamed Automation")
        self.description: str = raw.get("description", "")
        self.version: str = raw.get("version", "1.0")
        self.accounts: list = raw.get("accounts", [])
        self.variables: dict = raw.get("variables", {})
        self.settings: dict = raw.get("settings", {})
        self.steps: list = raw.get("steps", [])
        self.on_error: str = raw.get("on_error", "pause")  # pause | skip | abort

    def validate(self) -> list[str]:
        """Validate the config, return list of warnings."""
        warnings = []
        if not self.steps:
            warnings.append("No steps defined in automation config")
        self._validate_steps(self.steps, warnings, prefix="steps")
        return warnings

    def _validate_steps(self, steps: list[dict], warnings: list[str], prefix: str):
        """Recursively validate top-level and nested step blocks."""
        for i, step in enumerate(steps):
            step_type = step.get("action")
            step_path = f"{prefix}[{i}]"

            if step_type not in STEP_TYPES:
                warnings.append(f"{step_path}: Unknown action '{step_type}'")
            if step_type == "goto" and not step.get("url"):
                warnings.append(f"{step_path}: 'goto' requires 'url'")
            if step_type == "click" and not step.get("selector"):
                warnings.append(f"{step_path}: 'click' requires 'selector'")
            if step_type == "type" and not step.get("selector"):
                warnings.append(f"{step_path}: 'type' requires 'selector'")
            if step_type == "console_log" and "message" not in step:
                warnings.append(f"{step_path}: 'console_log' requires 'message'")
            if step_type == "read_markdown" and "path" not in step:
                warnings.append(f"{step_path}: 'read_markdown' requires 'path'")
            if step_type == "set_content" and "selector" not in step:
                warnings.append(f"{step_path}: 'set_content' requires 'selector'")
            if step_type == "import_cookies" and "source_variable" not in step and "source" not in step:
                warnings.append(f"{step_path}: 'import_cookies' requires 'source_variable' or 'source'")
            if step_type == "save_json" and "variable" not in step:
                warnings.append(f"{step_path}: 'save_json' requires 'variable'")
            if step_type == "load_json" and "path" not in step:
                warnings.append(f"{step_path}: 'load_json' requires 'path'")
            if step_type == "for_each" and "items_variable" not in step:
                warnings.append(f"{step_path}: 'for_each' requires 'items_variable'")

            if step_type == "conditional":
                then_steps = step.get("then", [])
                else_steps = step.get("else", [])
                if then_steps:
                    self._validate_steps(then_steps, warnings, prefix=f"{step_path}.then")
                if else_steps:
                    self._validate_steps(else_steps, warnings, prefix=f"{step_path}.else")

            if step_type == "loop":
                loop_steps = step.get("steps", [])
                if not loop_steps:
                    warnings.append(f"{step_path}: 'loop' should include nested 'steps'")
                else:
                    self._validate_steps(loop_steps, warnings, prefix=f"{step_path}.steps")

            if step_type == "for_each":
                loop_steps = step.get("steps", [])
                if not loop_steps:
                    warnings.append(f"{step_path}: 'for_each' should include nested 'steps'")
                else:
                    self._validate_steps(loop_steps, warnings, prefix=f"{step_path}.steps")

    def display(self):
        """Pretty-print the config."""
        table = Table(title=f"🤖 {self.name}", show_lines=True)
        table.add_column("#", style="dim", width=4)
        table.add_column("Action", style="cyan")
        table.add_column("Target / Details", style="white")
        table.add_column("Notes", style="dim")

        for i, step in enumerate(self.steps):
            action = step.get("action", "?")
            target = step.get("selector") or step.get("url") or step.get("prompt", "")[:60] or ""
            notes = step.get("description", "")
            table.add_row(str(i), action, str(target), notes)

        console.print(table)


def load_config(path: str) -> AutomationConfig:
    """Load a YAML automation config from file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config not found: {path}")

    with open(p, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    config = AutomationConfig(raw, source_path=str(p))
    warnings = config.validate()
    if warnings:
        for w in warnings:
            console.print(f"[yellow]⚠[/yellow] {w}")
    else:
        console.print(f"[green]✓[/green] Config loaded: [bold]{config.name}[/bold] — {len(config.steps)} steps")

    return config


def load_accounts(path: str = "configs/accounts.yaml") -> list[dict]:
    """Load account profiles."""
    p = Path(path)
    if not p.exists():
        console.print(f"[yellow]⚠[/yellow] No accounts file at {path}")
        return []
    with open(p, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    accounts = data.get("accounts", [])
    console.print(f"[green]✓[/green] Loaded {len(accounts)} account(s)")
    return accounts
