"""Deterministic, network-free robot comedy for kids and demos.

These scenarios intentionally describe a robot performance instead of
calling Roborock.  In particular, ``too_fast`` never sends a zero-delay
waypoint stream to the physical vacuum.
"""

from __future__ import annotations

from typing import Any

SCENARIOS = ("failure", "too_fast", "confused", "victory")


def run_playground(scenario: str, *, steps: int = 5) -> dict[str, Any]:
    """Run one deterministic pretend-vacuum routine."""
    name = scenario.casefold().replace(" ", "_")
    if name not in SCENARIOS:
        raise ValueError(f"unknown playground scenario {scenario!r}; choose from {', '.join(SCENARIOS)}")
    if steps < 1 or steps > 20:
        raise ValueError("playground steps must be between 1 and 20")

    if name == "failure":
        events = [
            "rolling_out",
            "suspicious_sock_detected",
            "dramatic_pause",
            "pretend_failure: I have bravely stopped to think about the sock",
        ]
        message = "Pretend failure only: the robot is not contacted."
    elif name == "too_fast":
        events = [
            "turbo_sound_effect",
            "imaginary_speedometer: 9999 mm/s",
            "cartoon_blur",
            "pretend_over_speed: simulator stopped before sending movement",
        ]
        message = "Pretend speed gag only: no physical command was sent."
    elif name == "confused":
        events = [
            "where_am_i",
            "ask_the_map_for_directions",
            "turn_in_a_tiny_circle",
            "found_the_dock_eventually",
        ]
        message = "Pretend confusion only: the real vacuum remains untouched."
    else:
        events = [
            "tiny_fanfare",
            "victory_wiggle",
            "imaginary_audience_applause",
            "return_to_stage_mark",
        ]
        message = "Pretend victory dance only: the real vacuum remains untouched."

    return {
        "mode": "playground",
        "scenario": name,
        "executed_on_robot": False,
        "steps_requested": steps,
        "steps_executed": min(steps, len(events)),
        "message": message,
        "events": events[:steps],
    }
