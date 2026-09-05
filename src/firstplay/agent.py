from __future__ import annotations

import base64
import json
import os
import re
from collections.abc import Sequence

from .models import Decision, TimelineEvent

SYSTEM_PROMPT = """You are FirstPlay, a black-box first-time game playtester.
You must behave like a real new player who can only see the current game window and use ordinary mouse/keyboard input.
Never assume hidden state, source code, scene trees, debug APIs, DOM/accessibility metadata, telemetry, or developer intent.
Take exactly ONE action per turn.
Prefer cautious, ordinary player actions. Do not use operating-system shortcuts, shell commands, developer consoles, or destructive actions.
If the game is clearly finished, the goal is complete, or continuing would be unsafe, choose stop.
Record friction only when the visible experience gives a new player a real reason to hesitate, misread, or get stuck.
Return JSON only, with this exact shape:
{
  "observation": "what is visibly on screen",
  "understanding": "what a new player currently thinks is happening",
  "friction": {"severity": "none|low|medium|high", "message": "short explanation or empty string"},
  "action": {
    "type": "click|key|type_text|wait|stop",
    "x": 0,
    "y": 0,
    "key": "",
    "text": "",
    "seconds": 1.0,
    "reason": ""
  },
  "confidence": 0.0
}
For click, coordinates are pixels relative to the supplied game screenshot, whose top-left is (0,0).
Only include fields relevant to the chosen action when practical.
"""


class OpenAIVisionAgent:
    def __init__(self, model: str | None = None) -> None:
        from openai import OpenAI

        self.model = model or os.getenv("FIRSTPLAY_MODEL", "gpt-5.6-luna")
        self.client = OpenAI()

    def decide(
        self,
        screenshot_png: bytes,
        *,
        goal: str,
        step: int,
        history: Sequence[TimelineEvent],
    ) -> Decision:
        encoded = base64.b64encode(screenshot_png).decode("ascii")
        recent = _history_text(history[-6:])
        prompt = (
            f"Playtest goal: {goal}\n"
            f"Current step: {step}\n"
            f"Recent visible history:\n{recent or '(none; this is the first observation)'}\n\n"
            "Inspect the screenshot as a first-time player and choose one next action."
        )

        response = self.client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": SYSTEM_PROMPT}],
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {
                            "type": "input_image",
                            "image_url": f"data:image/png;base64,{encoded}",
                        },
                    ],
                },
            ],
        )
        return parse_decision(response.output_text)


def parse_decision(text: str) -> Decision:
    raw = text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError(f"Model did not return a JSON object: {text[:200]!r}") from None
        data = json.loads(raw[start : end + 1])

    if not isinstance(data, dict):
        raise ValueError("Model response must be a JSON object")
    return Decision.from_dict(data)


def _history_text(events: Sequence[TimelineEvent]) -> str:
    lines: list[str] = []
    for event in events:
        action = event.decision.action
        detail = action.type
        if action.type == "click":
            detail += f"({action.x},{action.y})"
        elif action.type == "key":
            detail += f"({action.key})"
        elif action.type == "type_text":
            detail += "(<text>)"
        elif action.type == "wait":
            detail += f"({action.seconds}s)"
        lines.append(
            f"step {event.step}: saw {event.decision.observation!r}; acted {detail}"
        )
    return "\n".join(lines)
