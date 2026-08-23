"""Pure waypoint generators used by the Roborock coordinator.

The robot's planner owns the low-level driving. These helpers only produce
map-frame millimetre targets, which makes them easy to preview and test
without a live vacuum.
"""

from __future__ import annotations

import math
from collections.abc import Iterator
from typing import TypeAlias

Point: TypeAlias = tuple[int, int]


def circle(center: Point, radius_mm: float, steps: int = 16) -> Iterator[Point]:
    """Yield points around a circle."""
    if steps < 1:
        return
    cx, cy = center
    for i in range(steps):
        angle = 2 * math.pi * i / steps
        yield round(cx + radius_mm * math.cos(angle)), round(cy + radius_mm * math.sin(angle))


def square(center: Point, half_mm: float = 600) -> list[Point]:
    """Return a closed square path."""
    cx, cy = center
    half = round(half_mm)
    return [
        (round(cx - half), round(cy - half)),
        (round(cx + half), round(cy - half)),
        (round(cx + half), round(cy + half)),
        (round(cx - half), round(cy + half)),
        (round(cx - half), round(cy - half)),
    ]


def figure_eight(center: Point, radius_mm: float, steps: int = 24) -> Iterator[Point]:
    """Yield a compact lemniscate (figure-eight) path."""
    if steps < 1:
        return
    cx, cy = center
    for i in range(steps):
        angle = 2 * math.pi * i / steps
        yield round(cx + radius_mm * math.sin(angle)), round(cy + radius_mm * math.sin(2 * angle))


def lissajous(
    center: Point,
    ax: float,
    ay: float,
    a: int = 3,
    b: int = 2,
    steps: int = 24,
) -> Iterator[Point]:
    """Yield a bounded Lissajous path."""
    if steps < 1:
        return
    cx, cy = center
    for i in range(steps):
        angle = 2 * math.pi * i / steps
        yield round(cx + ax * math.sin(a * angle)), round(cy + ay * math.sin(b * angle))


def spin_crazy(center: Point, radius_mm: float, steps: int = 16) -> Iterator[Point]:
    """Yield a deterministic tight spiral-like path around ``center``.

    A coordinator can preview exactly what it will send, which is preferable
    to random motion around a real robot.
    """
    if steps < 1:
        return
    cx, cy = center
    for i in range(steps):
        angle = 4 * math.pi * i / steps
        radius = radius_mm * (0.35 + 0.65 * (i + 1) / steps)
        yield round(cx + radius * math.cos(angle)), round(cy + radius * math.sin(angle))


def make_pattern(name: str, center: Point, size_mm: int, steps: int = 16) -> list[Point]:
    """Build a named path and reject unknown patterns early."""
    if name == "circle":
        return list(circle(center, size_mm, steps))
    if name == "square":
        return square(center, size_mm)
    if name == "figure8":
        return list(figure_eight(center, size_mm, max(steps, 24)))
    if name == "lissajous":
        return list(lissajous(center, size_mm, size_mm // 2, steps=max(steps, 24)))
    if name in {"spin", "spin_crazy"}:
        return list(spin_crazy(center, size_mm, steps))
    raise ValueError(f"Unknown pattern: {name}")
