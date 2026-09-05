from __future__ import annotations

import json
from pathlib import Path

from .models import RunResult, TimelineEvent

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2, "none": 3}


def write_report(result: RunResult, run_dir: Path) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "timeline.json").write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (run_dir / "report.md").write_text(_markdown_report(result), encoding="utf-8")


def _markdown_report(result: RunResult) -> str:
    friction_events = [
        event
        for event in result.events
        if event.decision.friction.severity != "none" and event.decision.friction.message
    ]
    friction_events.sort(
        key=lambda event: (
            SEVERITY_ORDER[event.decision.friction.severity],
            event.elapsed_seconds,
        )
    )

    lines = [
        "# FirstPlay report",
        "",
        f"- **Game:** `{result.game}`",
        f"- **Goal:** {result.goal}",
        f"- **Model:** `{result.model}`",
        f"- **Started:** {result.started_at}",
        f"- **Duration:** {result.duration_seconds:.1f}s",
        f"- **Steps:** {len(result.events)}",
        f"- **Stop reason:** {result.stop_reason or 'limit reached'}",
        "",
        "## Friction findings",
        "",
    ]

    if not friction_events:
        lines.append("No explicit first-time-player friction was recorded in this run.")
    else:
        for event in friction_events:
            friction = event.decision.friction
            lines.extend(
                [
                    f"### {friction.severity.upper()} · {event.elapsed_seconds:.1f}s",
                    "",
                    friction.message,
                    "",
                    f"Evidence: [`{event.screenshot}`]({event.screenshot})",
                    "",
                    f"> Visible observation: {event.decision.observation}",
                    "",
                ]
            )

    lines.extend(["## Timeline", ""])
    for event in result.events:
        lines.extend(_timeline_markdown(event))

    lines.extend(
        [
            "## Interpretation note",
            "",
            "FirstPlay is a black-box simulated first-time player, not ground truth. "
            "Treat findings as evidence to review, not automatic bug verdicts.",
            "",
        ]
    )
    return "\n".join(lines)


def _timeline_markdown(event: TimelineEvent) -> list[str]:
    action = event.decision.action
    if action.type == "click":
        action_text = f"click ({action.x}, {action.y})"
    elif action.type == "key":
        action_text = f"key `{action.key}`"
    elif action.type == "hold_key":
        action_text = f"hold key `{action.key}` for {action.seconds}s"
    elif action.type == "type_text":
        action_text = "type text"
    elif action.type == "wait":
        action_text = f"wait {action.seconds}s"
    else:
        action_text = f"stop: {action.reason or ''}".rstrip()

    return [
        f"### Step {event.step} · {event.elapsed_seconds:.1f}s",
        "",
        f"- **Saw:** {event.decision.observation}",
        f"- **Understood:** {event.decision.understanding}",
        f"- **Action:** {action_text}",
        f"- **Confidence:** {event.decision.confidence:.2f}",
        f"- **Screenshot:** [`{event.screenshot}`]({event.screenshot})",
        "",
    ]
