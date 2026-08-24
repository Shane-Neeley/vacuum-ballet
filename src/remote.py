"""Bounded joystick-style movement plans for physical Roborock dances."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


MAX_REMOTE_VELOCITY_MPS = 0.30
MAX_REMOTE_OMEGA_RAD_S = 3.0
MIN_REMOTE_DURATION_MS = 250
MAX_REMOTE_DURATION_MS = 1500
MAX_REMOTE_STEPS = 12
REMOTE_INTER_PULSE_PAUSE_MS = 120


@dataclass(frozen=True)
class RemoteMove:
    """One bounded ``app_rc_move`` pulse."""

    omega: float
    velocity: float
    duration_ms: int

    def as_payload(self, seqnum: int) -> dict[str, Any]:
        return {
            "omega": round(self.omega, 2),
            "velocity": round(self.velocity, 2),
            "duration": self.duration_ms,
            "seqnum": seqnum,
        }


def _validate_moves(moves: list[RemoteMove]) -> None:
    if not moves or len(moves) > MAX_REMOTE_STEPS:
        raise ValueError(f"remote dance must contain 1–{MAX_REMOTE_STEPS} pulses")
    for move in moves:
        if abs(move.velocity) > MAX_REMOTE_VELOCITY_MPS:
            raise ValueError(f"remote velocity must be at most {MAX_REMOTE_VELOCITY_MPS} m/s")
        if abs(move.omega) > MAX_REMOTE_OMEGA_RAD_S:
            raise ValueError(f"remote turn rate must be at most {MAX_REMOTE_OMEGA_RAD_S} rad/s")
        if not MIN_REMOTE_DURATION_MS <= move.duration_ms <= MAX_REMOTE_DURATION_MS:
            raise ValueError(
                f"remote pulse duration must be between {MIN_REMOTE_DURATION_MS} and "
                f"{MAX_REMOTE_DURATION_MS} ms"
            )


def remote_dance_plan(style: str) -> dict[str, Any]:
    """Build a deterministic, bounded RC plan without touching the vacuum."""
    duration = 700
    if style == "wiggle":
        moves = [
            RemoteMove(omega=omega, velocity=0.22, duration_ms=duration)
            for omega in (1.8, -1.8, 1.8, -1.8, -1.8, 1.8, -1.8, 1.8)
        ]
    elif style == "spin":
        moves = [RemoteMove(omega=2.0, velocity=0.0, duration_ms=duration) for _ in range(8)]
    elif style == "crazy":
        moves = [
            RemoteMove(omega=2.0, velocity=0.24, duration_ms=duration),
            RemoteMove(omega=-2.0, velocity=0.24, duration_ms=duration),
            RemoteMove(omega=2.0, velocity=-0.24, duration_ms=duration),
            RemoteMove(omega=-2.0, velocity=-0.24, duration_ms=duration),
            RemoteMove(omega=-2.0, velocity=0.24, duration_ms=duration),
            RemoteMove(omega=2.0, velocity=0.24, duration_ms=duration),
            RemoteMove(omega=-2.0, velocity=-0.24, duration_ms=duration),
            RemoteMove(omega=2.0, velocity=-0.24, duration_ms=duration),
        ]
    elif style == "drift":
        moves = [
            RemoteMove(omega=2.8, velocity=0.28, duration_ms=900),
            RemoteMove(omega=-2.8, velocity=0.28, duration_ms=900),
            RemoteMove(omega=-2.8, velocity=-0.28, duration_ms=900),
            RemoteMove(omega=2.8, velocity=-0.28, duration_ms=900),
            RemoteMove(omega=2.8, velocity=0.28, duration_ms=900),
            RemoteMove(omega=-2.8, velocity=-0.28, duration_ms=900),
        ]
    elif style == "sprint":
        moves = [RemoteMove(omega=0.0, velocity=MAX_REMOTE_VELOCITY_MPS, duration_ms=1500)]
    else:
        raise ValueError(f"Unknown remote dance style: {style}")

    _validate_moves(moves)
    return {
        "mode": "remote_control_preview",
        "style": style,
        "moves": [move.as_payload(index + 1) for index, move in enumerate(moves)],
        "pulse_count": len(moves),
        "inter_pulse_pause_ms": REMOTE_INTER_PULSE_PAUSE_MS,
        "estimated_duration_ms": sum(move.duration_ms for move in moves)
        + REMOTE_INTER_PULSE_PAUSE_MS * (len(moves) - 1),
        "safety": {
            "maximum_velocity_mps": MAX_REMOTE_VELOCITY_MPS,
            "maximum_turn_rate_rad_s": MAX_REMOTE_OMEGA_RAD_S,
            "pulse_duration_ms": [MIN_REMOTE_DURATION_MS, MAX_REMOTE_DURATION_MS],
            "maximum_pulses": MAX_REMOTE_STEPS,
            "requires_explicit_confirmation": True,
            "cleanup": ["app_rc_stop", "app_rc_end"],
        },
    }
