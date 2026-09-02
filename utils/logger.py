"""Rich console styling and JARVIS HUD output utilities."""

import sys
import logging
from typing import Optional, List
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.theme import Theme
from rich.text import Text

# Custom theme for Tony Stark / JARVIS aesthetic (cyan, gold, blue, emerald)
custom_theme = Theme({
    "jarvis.title": "bold cyan",
    "jarvis.accent": "bold yellow",
    "jarvis.info": "cyan",
    "jarvis.success": "bold green",
    "jarvis.warning": "bold yellow",
    "jarvis.danger": "bold red",
    "jarvis.muted": "dim white",
    "jarvis.highlight": "bold magenta",
})

console = Console(theme=custom_theme)

JARVIS_BANNER = """
[bold cyan]   ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗[/bold cyan]
[bold cyan]   ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝[/bold cyan]
[bold cyan]   ██║███████║██████╔╝██║   ██║██║███████╗[/bold cyan]
[bold cyan]██╗██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║[/bold cyan]
[bold cyan]╚████║██║  ██║██║  ██║ ╚████╔╝ ██║███████║[/bold cyan]
[bold cyan] ╚═══╝╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝[/bold cyan]
[dim cyan]      Just A Rather Very Intelligent System      [/dim cyan]
[dim yellow]            Executive Email Briefing             [/dim yellow]
"""


def print_banner():
    """Render the JARVIS banner in the terminal."""
    console.print(JARVIS_BANNER)


def print_status(message: str, style: str = "cyan"):
    """Print an assistant status line."""
    console.print(f"[{style}]● [JARVIS][/] {message}")


def print_success(message: str):
    """Print a success status message."""
    console.print(f"[bold green]✔ [JARVIS][/] {message}")


def print_warning(message: str):
    """Print a warning status message."""
    console.print(f"[bold yellow]⚠ [JARVIS][/] {message}")


err_console = Console(stderr=True, theme=custom_theme)

def print_error(message: str):
    """Print an error status message."""
    err_console.print(f"[bold red]✖ [JARVIS ERROR][/] {message}")


def print_email_table(emails: List[dict]):
    """Render a structured table of fetched emails."""
    if not emails:
        console.print("[dim cyan]No emails to display.[/dim cyan]")
        return
        
    table = Table(
        title="[bold cyan]Unread Messages In Queue[/bold cyan]",
        show_header=True,
        header_style="bold yellow",
        border_style="cyan",
        expand=True,
    )
    table.add_column("#", style="dim cyan", width=4, justify="center")
    table.add_column("From", style="bold white", width=25, overflow="ellipsis")
    table.add_column("Subject", style="cyan", ratio=2, overflow="ellipsis")
    table.add_column("Date", style="dim yellow", width=18)
    table.add_column("Source", style="magenta", width=8, justify="center")
    
    for idx, em in enumerate(emails, start=1):
        date_str = str(em.get("date") or "Unknown")
        if len(date_str) > 19:
            date_str = date_str[:19]
        table.add_row(
            str(idx),
            str(em.get("sender", "Unknown")),
            str(em.get("subject", "No Subject")),
            date_str,
            str(em.get("source", "auto")).upper(),
        )
        
    console.print(table)


def print_briefing_panel(briefing_markdown: str, title: str = "JARVIS Executive Summary"):
    """Render the LLM generated briefing in a styled Stark Industries HUD panel."""
    md = Markdown(briefing_markdown)
    panel = Panel(
        md,
        title=f"[bold yellow]⚡ {title} ⚡[/bold yellow]",
        subtitle="[dim cyan]Stark Industries Tactical Interface v2.5[/dim cyan]",
        border_style="cyan",
        padding=(1, 2),
    )
    console.print(panel)


def setup_logger(debug: bool = False) -> logging.Logger:
    """Configure python logging with clean formatting."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    return logging.getLogger("JARVIS")
