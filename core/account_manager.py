"""
Account Manager — Multi-account support with profile isolation.

Each account gets its own browser profile directory so cookies,
localStorage, and sessions persist independently.
"""

from pathlib import Path
from typing import Optional

from rich.table import Table

from core.console import console


class Account:
    """Single account profile."""

    def __init__(self, data: dict):
        self.name: str = data.get("name", "unnamed")
        self.platform: str = data.get("platform", "generic")
        self.profile_dir: str = data.get("profile_dir", f"profiles/{self.platform}_{self.name}")
        self.proxy: Optional[dict] = data.get("proxy")
        self.credentials: dict = data.get("credentials", {})
        self.variables: dict = data.get("variables", {})
        self.tags: list[str] = data.get("tags", [])

    @property
    def email(self) -> Optional[str]:
        return self.credentials.get("email")

    @property
    def username(self) -> Optional[str]:
        return self.credentials.get("username")

    def __repr__(self):
        return f"Account({self.name}@{self.platform})"


class AccountManager:
    """Manages multiple accounts and their browser profiles."""

    def __init__(self, accounts_data: list[dict] = None):
        self.accounts: list[Account] = []
        if accounts_data:
            for data in accounts_data:
                self.accounts.append(Account(data))

    def get(self, name: str) -> Optional[Account]:
        """Get account by name."""
        for acc in self.accounts:
            if acc.name == name:
                return acc
        return None

    def get_by_platform(self, platform: str) -> list[Account]:
        """Get all accounts for a platform."""
        return [a for a in self.accounts if a.platform == platform]

    def display(self):
        """Pretty print all accounts."""
        table = Table(title="📋 Accounts", show_lines=True)
        table.add_column("Name", style="cyan")
        table.add_column("Platform", style="magenta")
        table.add_column("Profile Dir", style="dim")
        table.add_column("Proxy", style="yellow")

        for acc in self.accounts:
            proxy_str = acc.proxy.get("server", "none") if acc.proxy else "none"
            table.add_row(acc.name, acc.platform, acc.profile_dir, proxy_str)

        console.print(table)

    def ensure_profile_dirs(self):
        """Create profile directories for all accounts."""
        for acc in self.accounts:
            Path(acc.profile_dir).mkdir(parents=True, exist_ok=True)
        console.print(f"[green]✓[/green] Profile directories ready for {len(self.accounts)} account(s)")
