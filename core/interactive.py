"""
Interactive — User input & confirmation prompts during automation.

Provides a clean interface for the automation to pause and ask the
user questions, get confirmations, or display choices.
"""

import asyncio
from typing import Optional

from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.markdown import Markdown

from core.console import console


class InteractiveSession:
    """Handles user interaction during automation runs."""

    def __init__(self, auto_mode: bool = False):
        self.auto_mode = auto_mode
        self._log: list[dict] = []

    def ask(self, question: str, default: Optional[str] = None) -> str:
        """Ask the user a free-text question."""
        console.print()
        console.print(Panel(question, title="🤖 Agent Question", border_style="cyan"))
        if self.auto_mode and default:
            console.print(f"[dim]Auto-mode: using default → {default}[/dim]")
            return default
        answer = Prompt.ask("[bold cyan]Your answer[/bold cyan]", default=default)
        self._log.append({"type": "ask", "question": question, "answer": answer})
        return answer

    def confirm(self, message: str, default: bool = True) -> bool:
        """Ask for yes/no confirmation."""
        console.print()
        console.print(Panel(message, title="⚡ Confirm", border_style="yellow"))
        if self.auto_mode:
            console.print(f"[dim]Auto-mode: proceeding with {default}[/dim]")
            return default
        result = Confirm.ask("[bold yellow]Continue?[/bold yellow]", default=default)
        self._log.append({"type": "confirm", "message": message, "result": result})
        return result

    def choose(self, question: str, choices: list[str], default: Optional[str] = None) -> str:
        """Present multiple choices."""
        console.print()
        console.print(Panel(question, title="📋 Choose", border_style="magenta"))
        for i, choice in enumerate(choices):
            console.print(f"  [magenta]{i + 1}.[/magenta] {choice}")
        if self.auto_mode and default:
            return default
        answer = Prompt.ask(
            "[bold magenta]Pick a number[/bold magenta]",
            choices=[str(i + 1) for i in range(len(choices))],
            default=str(choices.index(default) + 1) if default and default in choices else "1",
        )
        selected = choices[int(answer) - 1]
        self._log.append({"type": "choose", "question": question, "selected": selected})
        return selected

    def show_info(self, title: str, content: str):
        """Display info panel to user."""
        console.print()
        console.print(Panel(Markdown(content), title=title, border_style="green"))

    def show_error(self, message: str):
        """Display error to user."""
        console.print()
        console.print(Panel(message, title="❌ Error", border_style="red"))

    def show_step(self, step_num: str, action: str, description: str = ""):
        """Show current step being executed."""
        desc = f" — {description}" if description else ""
        console.print(f"\n[bold white on blue] STEP {step_num} [/bold white on blue] [cyan]{action}[/cyan]{desc}")

    def pause(self, message: str = "Paused. Press Enter to continue…"):
        """Pause execution until user presses Enter."""
        if not self.auto_mode:
            console.input(f"\n[dim]{message}[/dim] ")
