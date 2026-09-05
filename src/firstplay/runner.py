from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path

from rich.console import Console

from .agent import OpenAIVisionAgent
from .models import RunResult, TimelineEvent
from .report import write_report
from .windows import WindowsGameSession

console = Console()


def run_playtest(
    game: Path,
    *,
    goal: str,
    model: str,
    seconds: int = 60,
    max_steps: int = 30,
    launch_wait: float = 2.0,
    output_root: Path = Path("firstplay-runs"),
    close_game: bool = False,
) -> Path:
    if seconds <= 0:
        raise ValueError("seconds must be greater than zero")
    if max_steps <= 0:
        raise ValueError("max_steps must be greater than zero")

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = output_root / timestamp
    screenshots_dir = run_dir / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=False)

    session = WindowsGameSession(game, launch_wait=launch_wait)
    agent = OpenAIVisionAgent(model=model)
    started_wall = datetime.now(UTC)
    started = time.monotonic()
    events: list[TimelineEvent] = []
    stop_reason = ""

    console.print("[bold]FirstPlay 0.1[/bold]")
    try:
        rect = session.start()
        console.print(
            f"Game window: [cyan]{rect.title or game.name}[/cyan]  "
            f"{rect.width}x{rect.height}"
        )
        console.print(f"Model: [cyan]{model}[/cyan]")
        console.print(f"Goal: {goal}\n")

        for step in range(max_steps):
            elapsed = time.monotonic() - started
            if elapsed >= seconds:
                stop_reason = f"time limit reached ({seconds}s)"
                break
            if not session.is_running:
                stop_reason = "game process exited"
                break

            screenshot_bytes = session.capture_png()
            screenshot_rel = Path("screenshots") / f"{step:03d}.png"
            (run_dir / screenshot_rel).write_bytes(screenshot_bytes)

            decision = agent.decide(
                screenshot_bytes,
                goal=goal,
                step=step,
                history=events,
            )
            elapsed = time.monotonic() - started
            event = TimelineEvent(
                step=step,
                elapsed_seconds=elapsed,
                screenshot=screenshot_rel.as_posix(),
                decision=decision,
            )
            events.append(event)
            _print_event(event)

            if decision.action.type == "stop":
                stop_reason = decision.action.reason or "model chose to stop"
                break

            session.execute(decision.action)
            time.sleep(0.35)
        else:
            stop_reason = f"step limit reached ({max_steps})"
    except KeyboardInterrupt:
        stop_reason = "interrupted by user"
        console.print("\n[yellow]Run interrupted by user.[/yellow]")
    finally:
        duration = time.monotonic() - started
        result = RunResult(
            game=str(game),
            goal=goal,
            model=model,
            started_at=started_wall.isoformat(),
            duration_seconds=duration,
            events=events,
            stop_reason=stop_reason,
        )
        write_report(result, run_dir)
        if close_game:
            session.terminate()

    console.print(f"\nReport written to [green]{run_dir}[/green]")
    return run_dir


def _print_event(event: TimelineEvent) -> None:
    decision = event.decision
    stamp = f"[{event.elapsed_seconds:05.1f}s]"
    console.print(f"{stamp} [bold]sees[/bold]      {decision.observation}")
    if decision.friction.severity != "none" and decision.friction.message:
        console.print(
            f"{stamp} [bold yellow]friction[/bold yellow]  "
            f"{decision.friction.severity.upper()} — {decision.friction.message}"
        )

    action = decision.action
    if action.type == "click":
        detail = f"click ({action.x}, {action.y})"
    elif action.type == "key":
        detail = f"key {action.key!r}"
    elif action.type == "type_text":
        detail = "type text"
    elif action.type == "wait":
        detail = f"wait {action.seconds}s"
    else:
        detail = f"stop — {action.reason or ''}".rstrip()
    console.print(f"{stamp} [bold]action[/bold]    {detail}")
