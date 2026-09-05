"""
Run - Entry point for Open Automation Creator.

Usage:
    python run.py configs/linkedin_post.yaml
    python run.py configs/linkedin_post.yaml --account main_linkedin
    python run.py configs/linkedin_post.yaml --through-step 5
    python run.py --discover-url https://www.linkedin.com/feed/ --account main_linkedin --pause
"""

import argparse
import asyncio
import sys

from rich.panel import Panel

from core.console import console


def load_account_by_name(account_name: str):
    """Resolve an account from configs/accounts.yaml."""
    from core.account_manager import Account
    from core.config_loader import load_accounts

    accounts = load_accounts()
    for data in accounts:
        if data.get("name") == account_name:
            return Account(data)
    raise ValueError(f"Account not found: {account_name}")


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser."""
    parser = argparse.ArgumentParser(
        description="Open Automation Creator - Config-driven browser automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py configs/linkedin_post.yaml
  python run.py configs/linkedin_post.yaml --account main_linkedin
  python run.py configs/linkedin_post.yaml --through-step 5
  python run.py --discover-url https://www.linkedin.com/feed/ --account main_linkedin --pause
        """,
    )
    parser.add_argument("config", nargs="?", help="Path to YAML automation config")
    parser.add_argument("--account", "-a", help="Account name to use (from configs/accounts.yaml)")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--auto", action="store_true", help="Auto-mode: skip confirmations where possible")
    parser.add_argument("--from-step", type=int, default=0, help="Start from this top-level step index")
    parser.add_argument("--through-step", type=int, help="Stop after this top-level step index (inclusive)")
    parser.add_argument("--set", action="append", default=[], metavar="KEY=VALUE", help="Set or override a runtime variable; repeat as needed")

    parser.add_argument("--discover-url", help="Open a live discovery session instead of running a config")
    parser.add_argument("--snapshot-mode", choices=["quick", "full"], default="full", help="Snapshot mode for discovery")
    parser.add_argument("--pause", action="store_true", help="Pause so you can log in or navigate before capturing discovery output")
    parser.add_argument("--output-dir", default="output/discovery", help="Directory for discovery artifacts")
    parser.add_argument("--check-selector", action="append", default=[], help="Selector to verify during discovery; repeat for multiple selectors")
    parser.add_argument("--selector-timeout", type=int, default=3000, help="Timeout in ms for selector checks during discovery")
    parser.add_argument("--wait-ms", type=int, default=0, help="Extra wait in ms after initial navigation during discovery")
    return parser


def parse_runtime_variables(pairs: list[str]) -> dict[str, str]:
    """Parse repeated KEY=VALUE CLI arguments into a dictionary."""
    variables: dict[str, str] = {}
    for pair in pairs:
        if "=" not in pair:
            raise ValueError(f"Invalid --set value: {pair}. Expected KEY=VALUE")
        key, value = pair.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"Invalid --set value: {pair}. Key cannot be empty")
        variables[key] = value
    return variables


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.config and args.discover_url:
        parser.error("Use either a config path or --discover-url, not both.")
    if not args.config and not args.discover_url:
        parser.error("Provide a config path or --discover-url.")

    console.print()
    console.print(Panel(
        "[bold]Open Automation Creator[/bold]\nConfig-driven browser automation powered by Patchright",
        title="Agent Runtime",
        border_style="cyan",
    ))
    console.print()

    from core.browser import ensure_patchright_installed
    ensure_patchright_installed()
    runtime_variables = parse_runtime_variables(args.set)

    try:
        if args.discover_url:
            from core.discovery import run_discovery_session

            account = load_account_by_name(args.account) if args.account else None
            result = asyncio.run(run_discovery_session(
                url=args.discover_url,
                account=account,
                headless=args.headless,
                snapshot_mode=args.snapshot_mode,
                pause_for_manual=args.pause,
                output_dir=args.output_dir,
                selector_checks=args.check_selector,
                selector_timeout=args.selector_timeout,
                wait_after_load_ms=args.wait_ms,
            ))
        else:
            from core.engine import run_automation

            result = asyncio.run(run_automation(
                config_path=args.config,
                account_name=args.account,
                headless=args.headless,
                auto_mode=args.auto,
                start_step=args.from_step,
                end_step=args.through_step,
                runtime_variables=runtime_variables,
            ))

        console.print(f"\n[bold green]Result:[/bold green] {result['status']}")
    except KeyboardInterrupt:
        console.print("\n[yellow]Aborted by user.[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]Fatal error:[/bold red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
