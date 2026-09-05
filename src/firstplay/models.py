from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

ActionType = Literal["click", "key", "hold_key", "type_text", "wait", "stop"]
Severity = Literal["none", "low", "medium", "high"]


@dataclass(slots=True)
class Action:
    type: ActionType
    x: int | None = None
    y: int | None = None
    key: str | None = None
    text: str | None = None
    seconds: float | None = None
    reason: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Action:
        action_type = data.get("type")
        if action_type not in {"click", "key", "hold_key", "type_text", "wait", "stop"}:
            raise ValueError(f"Unsupported action type: {action_type!r}")

        action = cls(
            type=action_type,
            x=_optional_int(data.get("x")),
            y=_optional_int(data.get("y")),
            key=_optional_str(data.get("key")),
            text=_optional_str(data.get("text")),
            seconds=_optional_float(data.get("seconds")),
            reason=_optional_str(data.get("reason")),
        )
        action.validate()
        return action

    def validate(self) -> None:
        if self.type == "click" and (self.x is None or self.y is None):
            raise ValueError("click requires x and y")
        if self.type in {"key", "hold_key"} and not self.key:
            raise ValueError(f"{self.type} requires key")
        if self.type == "hold_key" and self.seconds is None:
            raise ValueError("hold_key requires seconds")
        if self.type == "type_text" and self.text is None:
            raise ValueError("type_text requires text")
        if self.type == "wait" and self.seconds is None:
            raise ValueError("wait requires seconds")


@dataclass(slots=True)
class Friction:
    severity: Severity = "none"
    message: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> Friction:
        data = data or {}
        severity = data.get("severity", "none")
        if severity not in {"none", "low", "medium", "high"}:
            severity = "none"
        return cls(severity=severity, message=str(data.get("message", "")).strip())


@dataclass(slots=True)
class Decision:
    observation: str
    understanding: str
    friction: Friction
    action: Action
    confidence: float

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Decision:
        confidence = float(data.get("confidence", 0.0))
        confidence = max(0.0, min(1.0, confidence))
        return cls(
            observation=str(data.get("observation", "")).strip(),
            understanding=str(data.get("understanding", "")).strip(),
            friction=Friction.from_dict(data.get("friction")),
            action=Action.from_dict(data.get("action") or {}),
            confidence=confidence,
        )


@dataclass(slots=True)
class TimelineEvent:
    step: int
    elapsed_seconds: float
    screenshot: str
    decision: Decision

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RunResult:
    game: str
    goal: str
    model: str
    started_at: str
    duration_seconds: float
    events: list[TimelineEvent] = field(default_factory=list)
    stop_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _optional_str(value: Any) -> str | None:
    return None if value is None else str(value)


def _optional_int(value: Any) -> int | None:
    return None if value is None else int(value)


def _optional_float(value: Any) -> float | None:
    return None if value is None else float(value)
