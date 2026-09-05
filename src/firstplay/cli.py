from __future__ import annotations

import os
import platform
import sys
from pathlib import Path

import typer
from rich.console import Console

from . import __version__
from .runner import run_playtest

app = typer.Typer(
    name="firstplay",
    help="Black-box first-time game playtesting with a vision model.",
    no_args_is_help=True,
)
console = Console()
DEFAULT_OUTPUT_ROOT = Path("firstplay-runs")


@app.command()
def doctor() -> None:
    """Check whether the local machine is ready for a FirstPlay run."""
    checks: list[tuple[str, bool, str]] = []
    checks.append(("Windows", os.name == "nt", platform.platform()))
    checks.append(("Python 3.11+", sys.version_info >= (3, 11), platform.python_version()))
    checks.append(
        (
            "OPENAI_API_KEY",
            bool(os.getenv("OPENAI_API_KEY")),
            "set" if os.getenv("OPENAI_API_KEY") else "missing",
        )
    )

    console.print(f"[bold]FirstPlay {__version__} doctor[/bold]\n")
    failed = False
    for label, ok, detail in checks:
        icon = "[green]PASS[/green]" if ok else "[red]FAIL[/red]"
        console.print(f"{icon}  {label}: {detail}")
        failed = failed or not ok

    if failed:
        raise typer.Exit(code=1)
    console.print("\n[green]Ready for a first playtest.[/green]")


@app.command("run")
def run_command(
    game: Path = typer.Argument(  # noqa: B008
        ..., exists=True, dir_okay=False, readable=True
    ),
    goal: str = typer.Option(
        "Start the game and try to understand how to play.",
        "--goal",
        help="What the first-time player should try to accomplish.",
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        help="Vision model. Defaults to FIRSTPLAY_MODEL or gpt-5.6-luna.",
    ),
    seconds: int = typer.Option(60, min=1, max=3600),
    max_steps: int = typer.Option(30, min=1, max=500),
    launch_wait: float = typer.Option(2.0, min=0.0, max=30.0),
    output: Path = typer.Option(DEFAULT_OUTPUT_ROOT, "--output"),
    close_game: bool = typer.Option(False, "--close-game"),
) -> None:
    """Launch GAME and run one black-box first-time playtest."""
    if os.name != "nt":
        console.print("[red]FirstPlay v0.1 currently supports Windows only.[/red]")
        raise typer.Exit(code=2)
    if not os.getenv("OPENAI_API_KEY"):
        console.print(
            "[red]OPENAI_API_KEY is not set.[/red] "
            "Set it in the environment before starting a v0.1 run."
        )
        raise typer.Exit(code=2)

    chosen_model = model or os.getenv("FIRSTPLAY_MODEL", "gpt-5.6-luna")
    try:
        run_playtest(
            game,
            goal=goal,
            model=chosen_model,
            seconds=seconds,
            max_steps=max_steps,
            launch_wait=launch_wait,
            output_root=output,
            close_game=close_game,
        )
    except Exception as exc:
        console.print(f"[red]FirstPlay failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc


@app.callback()
def version_callback(
    version: bool = typer.Option(False, "--version", help="Show version and exit.", is_eager=True),
) -> None:
    if version:
        console.print(__version__)
        raise typer.Exit()
