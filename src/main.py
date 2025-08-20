#!/usr/bin/env python3
"""
Vacuum Ballet (Minimal) — pure-Python pattern generators.
"""

from __future__ import annotations
import math
from typing import Iterable, Iterator, Tuple, List

Point = Tuple[int, int]


def circle(center: Point, radius_mm: int, steps: int = 20) -> Iterator[Point]:
    cx, cy = center
    for i in range(steps):
        t = 2 * math.pi * i / steps
        yield int(cx + radius_mm * math.cos(t)), int(cy + radius_mm * math.sin(t))


def square(center: Point, half_mm: int = 600) -> List[Point]:
    cx, cy = center
    return [
        (cx - half_mm, cy - half_mm),
        (cx + half_mm, cy - half_mm),
        (cx + half_mm, cy + half_mm),
        (cx - half_mm, cy + half_mm),
        (cx - half_mm, cy - half_mm),
    ]


def figure_eight(
    center: Point, radius_mm: int = 800, steps: int = 24
) -> Iterator[Point]:
    cx, cy = center
    for i in range(steps):
        t = 2 * math.pi * i / (steps - 1)
        x = cx + radius_mm * math.sin(t)
        y = cy + radius_mm * math.sin(t) * math.cos(t)
        yield int(x), int(y)


def lissajous(
    center: Point,
    ax: int = 800,
    ay: int = 600,
    a: int = 3,
    b: int = 2,
    delta: float = math.pi / 2,
    steps: int = 32,
) -> Iterator[Point]:
    cx, cy = center
    for i in range(steps):
        t = 2 * math.pi * i / steps
        x = cx + ax * math.sin(a * t + delta)
        y = cy + ay * math.sin(b * t)
        yield int(x), int(y)


if __name__ == "__main__":
    # Demo printout
    print(list(circle((0, 0), 100, steps=4)))
