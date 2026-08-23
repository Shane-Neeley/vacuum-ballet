"""Small, deliberately narrow natural-language intent parser.

This is a planner for family-friendly commands, not a general-purpose LLM
or an authorization layer.  Unknown requests fail closed and physical
actions remain confirmation-gated by the CLI.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class KidIntent:
    """A parsed request with enough metadata for a human-readable plan."""

    action: str
    args: dict[str, Any] = field(default_factory=dict)
    explanation: str = ""
    requires_confirmation: bool = False
    simulator_only: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "args": self.args,
            "explanation": self.explanation,
            "requires_confirmation": self.requires_confirmation,
            "simulator_only": self.simulator_only,
        }


def _number(text: str, pattern: str) -> int | None:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def parse_kid_request(text: str) -> KidIntent:
    """Parse a safe subset of natural-language robot requests."""
    normalized = " ".join(text.casefold().strip().split())
    if not normalized:
        raise ValueError("say what you want the robot to do")

    # Comedy is always local.  Keep this before dance/clean matching so a
    # child asking it to "fail cleaning" cannot accidentally start cleaning.
    if re.search(r"too\s+fast|go\s+fast|turbo|speed", normalized):
        return KidIntent(
            "play",
            {"scenario": "too_fast"},
            "Run the pretend too-fast gag in the local playground.",
            simulator_only=True,
        )
    if re.search(r"pretend.*fail|fail|broken|stuck|sock", normalized):
        return KidIntent(
            "play",
            {"scenario": "failure"},
            "Run a pretend failure; never send a movement command.",
            simulator_only=True,
        )
    if re.search(r"confus|lost", normalized):
        return KidIntent(
            "play",
            {"scenario": "confused"},
            "Run the pretend confused routine locally.",
            simulator_only=True,
        )
    if re.search(r"victory|celebrat|win", normalized):
        return KidIntent(
            "play",
            {"scenario": "victory"},
            "Run the pretend victory dance locally.",
            simulator_only=True,
        )

    if re.search(r"\b(stop|halt)\b", normalized):
        return KidIntent("stop", explanation="Stop the physical vacuum.", requires_confirmation=True)
    if re.search(r"\b(pause|wait)\b", normalized):
        return KidIntent("pause", explanation="Pause the physical vacuum.", requires_confirmation=True)
    if re.search(r"\b(dock|home|charge)\b", normalized):
        return KidIntent("dock", explanation="Send the physical vacuum back to its dock.", requires_confirmation=True)
    if re.search(r"\b(beep|locate|find)\b", normalized):
        return KidIntent("beep", explanation="Play the physical vacuum's locate sound.", requires_confirmation=True)
    if re.search(r"\b(status|state|where|location)\b", normalized):
        return KidIntent("status", explanation="Read status and location without changing the vacuum.")
    if re.search(r"\b(rooms?|segments?)\b", normalized) and not re.search(r"\b(clean|vacuum)\b", normalized):
        return KidIntent("rooms", explanation="Read the map's room-to-segment mapping.")

    if re.search(r"\b(clean|vacuum|sweep)\b", normalized):
        segments = [int(value) for value in re.findall(r"\b(?:room|segment)\s*(\d+)\b", normalized)]
        if segments:
            return KidIntent(
                "clean_rooms",
                {"segments": segments, "repeat": 1},
                f"Clean map segments {segments}.",
                requires_confirmation=True,
            )
        return KidIntent("clean", explanation="Start the physical vacuum's normal cleaning routine.", requires_confirmation=True)

    if re.search(r"\b(dance|wiggle|choreograph|move)\b", normalized):
        if re.search(r"figure\s*[- ]?eight|figure8|lemniscate", normalized):
            pattern = "figure8"
        elif "lissajous" in normalized:
            pattern = "lissajous"
        elif "square" in normalized:
            pattern = "square"
        elif "spin" in normalized or "spiral" in normalized:
            pattern = "spin_crazy"
        else:
            pattern = "circle"
        size = _number(normalized, r"(\d+)\s*(?:mm|millimet(?:er|re)s?)") or (700 if "big" in normalized else 300)
        beat = _number(normalized, r"(\d+)\s*(?:ms|milliseconds?)") or 500
        return KidIntent(
            "dance",
            {"pattern": pattern, "size": size, "beat_ms": beat},
            f"Plan a bounded {pattern} dance and show it before execution.",
            requires_confirmation=True,
        )

    raise ValueError(
        "I know status, clean, dock, pause, stop, beep, rooms, bounded dances, "
        "and pretend failure/speed/confusion/victory playground routines"
    )


def intent_plan(intent: KidIntent) -> dict[str, Any]:
    """Return a concise plan suitable for a parent or agent review."""
    return {
        "mode": "playground" if intent.simulator_only else "physical_or_read_only",
        "intent": intent.as_dict(),
        "next_step": (
            "run locally; no vacuum connection"
            if intent.simulator_only
            else "add --execute --confirm to perform a physical action"
            if intent.requires_confirmation
            else "execute as a read-only request"
        ),
    }
