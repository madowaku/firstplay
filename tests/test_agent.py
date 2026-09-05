from firstplay.agent import parse_decision


def test_parse_click_decision() -> None:
    decision = parse_decision(
        """{
          "observation": "Main menu",
          "understanding": "I can start here",
          "friction": {"severity": "none", "message": ""},
          "action": {"type": "click", "x": 120, "y": 240},
          "confidence": 0.9
        }"""
    )

    assert decision.observation == "Main menu"
    assert decision.action.type == "click"
    assert decision.action.x == 120
    assert decision.action.y == 240
    assert decision.confidence == 0.9


def test_parse_fenced_json() -> None:
    decision = parse_decision(
        """```json
        {
          "observation": "No obvious next action",
          "understanding": "I am stuck",
          "friction": {"severity": "high", "message": "No visible affordance"},
          "action": {"type": "wait", "seconds": 1},
          "confidence": 0.4
        }
        ```"""
    )

    assert decision.friction.severity == "high"
    assert decision.action.type == "wait"


def test_parse_hold_key() -> None:
    decision = parse_decision(
        """{
          "observation": "Character can move",
          "understanding": "W likely moves forward",
          "friction": {"severity": "none", "message": ""},
          "action": {"type": "hold_key", "key": "w", "seconds": 0.5},
          "confidence": 0.8
        }"""
    )

    assert decision.action.type == "hold_key"
    assert decision.action.key == "w"
    assert decision.action.seconds == 0.5


def test_confidence_is_clamped() -> None:
    decision = parse_decision(
        """{
          "observation": "Result screen",
          "understanding": "The run ended",
          "friction": {"severity": "none", "message": ""},
          "action": {"type": "stop", "reason": "goal complete"},
          "confidence": 4.2
        }"""
    )

    assert decision.confidence == 1.0
