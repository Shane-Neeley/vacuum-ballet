"""Offline planning and guardrails for physical-vacuum choreography.

The Roborock API accepts map-frame targets, but it does not know that a
sequence was produced for a child, a joke, or an unfamiliar garage.  This
module keeps the plan inspectable and rejects surprising physical commands
before they reach the transport.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from patterns import Point, make_pattern


@dataclass(frozen=True)
class SafetyPolicy:
    """Conservative limits for real-vacuum waypoint choreography."""

    min_radius_mm: int = 200
    max_radius_mm: int = 1200
    min_beat_ms: int = 250
    max_waypoints: int = 32
    max_segment_count: int = 8
    max_repeat: int = 2

    def validate_dance(
        self,
        *,
        size_mm: int,
        beat_ms: int,
        waypoints: int,
        real_robot: bool = True,
    ) -> None:
        """Reject a dance that is too large, too fast, or too long.

        Preview plans can opt out of the real-robot beat limit.  They still
        retain the same geometry so a child can explore deliberately silly
        values without touching the device.
        """
        if size_mm < self.min_radius_mm or size_mm > self.max_radius_mm:
            raise ValueError(
                f"dance size must be between {self.min_radius_mm} and "
                f"{self.max_radius_mm} mm (requested {size_mm})"
            )
        if beat_ms < 0:
            raise ValueError("beat_ms cannot be negative")
        if real_robot and beat_ms < self.min_beat_ms:
            raise ValueError(
                f"real-vacuum beat_ms must be at least {self.min_beat_ms}; "
                "use `play too_fast` for a simulator-only joke"
            )
        if waypoints < 1:
            raise ValueError("dance produced no waypoints")
        if waypoints > self.max_waypoints:
            raise ValueError(f"dance has {waypoints} waypoints; limit is {self.max_waypoints}")

    def validate_segments(self, segments: list[int], repeat: int) -> None:
        """Validate a room-clean request before sending it."""
        if not segments:
            raise ValueError("at least one room segment is required")
        if len(segments) > self.max_segment_count:
            raise ValueError(f"at most {self.max_segment_count} room segments may be requested")
        if any(segment < 0 for segment in segments):
            raise ValueError("room segment ids must be non-negative")
        if repeat < 1 or repeat > self.max_repeat:
            raise ValueError(f"room-clean repeat must be between 1 and {self.max_repeat}")


def dance_plan(
    pattern: str,
    center: Point,
    size_mm: int,
    beat_ms: int,
    *,
    policy: SafetyPolicy | None = None,
    real_robot: bool = False,
) -> dict[str, Any]:
    """Create a JSON-friendly dance plan without network access."""
    policy = policy or SafetyPolicy()
    points = make_pattern(pattern, center, int(size_mm))
    policy.validate_dance(
        size_mm=int(size_mm),
        beat_ms=int(beat_ms),
        waypoints=len(points),
        real_robot=real_robot,
    )
    return {
        "mode": "real_robot" if real_robot else "preview",
        "pattern": pattern,
        "center": {"x": int(center[0]), "y": int(center[1])},
        "size_mm": int(size_mm),
        "beat_ms": int(beat_ms),
        "waypoints": [{"x": x, "y": y} for x, y in points],
        "waypoint_count": len(points),
        "estimated_duration_ms": max(0, len(points) - 1) * int(beat_ms),
        "safety": {
            "radius_range_mm": [policy.min_radius_mm, policy.max_radius_mm],
            "minimum_real_beat_ms": policy.min_beat_ms,
            "maximum_waypoints": policy.max_waypoints,
            "robot_owns_obstacle_avoidance": True,
        },
    }
