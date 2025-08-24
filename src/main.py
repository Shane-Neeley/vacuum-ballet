#!/usr/bin/env python3
"""Simple vacuum dance patterns.

This simplified module generates waypoints for three basic patterns:
``circle``, ``square`` and ``spin``.  The functions return integer
coordinates that can be used to choreograph a robot.  A tiny CLI is
provided for manual experimentation which simply prints the points for a
chosen pattern.
"""

from __future__ import annotations

import argparse
import logging
import math
import os
import random
import time
from pathlib import Path
from typing import Callable, List, Tuple

from dotenv import dotenv_values
import matplotlib

matplotlib.use("Agg")  # headless image generation
import matplotlib.pyplot as plt

Point = Tuple[int, int]

# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def circle(center: Point, radius_mm: int, steps: int = 16) -> List[Point]:
    """Return points evenly spaced on a circle."""
    cx, cy = center
    points: List[Point] = []
    for i in range(steps):
        t = 2 * math.pi * i / steps
        points.append((int(cx + radius_mm * math.cos(t)), int(cy + radius_mm * math.sin(t))))
    return points

def square(center: Point, half_mm: int = 600) -> List[Point]:
    """Return the corners of a square, closing the path."""
    cx, cy = center
    return [
        (int(cx - half_mm), int(cy - half_mm)),
        (int(cx + half_mm), int(cy - half_mm)),
        (int(cx + half_mm), int(cy + half_mm)),
        (int(cx - half_mm), int(cy + half_mm)),
        (int(cx - half_mm), int(cy - half_mm)),
    ]

def spin(center: Point, radius_mm: int = 200, steps: int = 8) -> List[Point]:
    """Return points forming a small circle to simulate spinning."""
    return circle(center, radius_mm, steps)

PATTERNS: dict[str, Callable[..., List[Point]]] = {
    "circle": circle,
    "square": square,
    "spin": spin,
}

logger = logging.getLogger("vacuum")
if not logger.handlers:
    handler = logging.StreamHandler()
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Dance helper
# ---------------------------------------------------------------------------

def dance(pattern: str, size: int, beat_ms: int = 500, center: Point = (0, 0)) -> List[Point]:
    """Generate and print waypoints for a dance pattern.

    Parameters
    ----------
    pattern: name of the pattern (``circle``, ``square`` or ``spin``)
    size:    radius or half-size in millimetres
    beat_ms: delay between printed points
    center:  origin for the pattern, defaults to ``(0, 0)``
    """
    generator = PATTERNS.get(pattern)
    if generator is None:
        raise ValueError(f"Unknown pattern: {pattern}")

    logger.info("dancing %s", pattern)
    if pattern == "square":
        points = generator(center, half_mm=size)
    else:
        points = generator(center, radius_mm=size)

    for x, y in points:
        print(f"goto {x} {y}")
        if beat_ms > 0:
            time.sleep(beat_ms / 1000.0)
    return points


def clean(size: int, center: Point = (0, 0)) -> List[Point]:
    """Return a square cleaning path and log the action."""
    logger.info("cleaning")
    return square(center, half_mm=size)


def random_dance(size: int, center: Point = (0, 0)) -> List[Point]:
    """Choose a random pattern and return its points."""
    pattern = random.choice(list(PATTERNS.keys()))
    return dance(pattern, size, beat_ms=0, center=center)


def devices() -> List[str]:
    """Return placeholder list of connected devices."""
    return ["simulated-vacuum"]


def beep(times: int = 1) -> None:
    """Print 'beep' a number of times."""
    for _ in range(times):
        print("beep")


def load_envs(path: str = ".env") -> None:
    """Load environment variables from a .env file if present."""
    env_path = Path(path)
    if env_path.exists():
        for key, value in dotenv_values(env_path).items():
            os.environ.setdefault(key, value)


def generate_image(points: List[Point], filename: str) -> None:
    """Generate a simple plot of the path."""
    if not points:
        return
    xs, ys = zip(*points)
    plt.figure()
    plt.plot(xs, ys, marker="o")
    plt.axis("equal")
    plt.savefig(filename)
    plt.close()

# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Roborock Vacuum Ballet")
    sub = parser.add_subparsers(dest="cmd")
    p_dance = sub.add_parser("dance", help="Dance a pattern")
    p_dance.add_argument("pattern", choices=sorted(PATTERNS.keys()))
    p_dance.add_argument("size", type=int, nargs="?", default=100)
    p_dance.add_argument("beat_ms", type=int, nargs="?", default=500)

    p_beep = sub.add_parser("beep", help="Emit a simple beep")
    p_beep.add_argument("times", type=int, nargs="?", default=1)

    args = parser.parse_args(argv)
    if args.cmd == "dance":
        dance(args.pattern, args.size, args.beat_ms)
    elif args.cmd == "beep":
        beep(args.times)
    else:
        parser.print_help()

if __name__ == "__main__":  # pragma: no cover - CLI entry
    main()
