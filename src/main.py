#!/usr/bin/env python3
"""Roborock Vacuum Ballet.

Tiny CLI and pattern generators to choreograph a Roborock **S4 Max** using
simple ``goto`` waypoints.  The script logs in with the credentials from a
``.env`` file and exposes a few sub‑commands:

``devices``
    List devices on the account and highlight the S4 Max.

``beep``
    Make the robot play its locate/beep sound.

``goto X Y``
    Move the robot to ``(X, Y)`` in map millimetres.

``dance PATTERN SIZE [BEAT_MS]``
    Send a sequence of ``goto`` commands following ``PATTERN`` at the tempo
    defined by ``BEAT_MS`` (defaults to 600 ms between points).

Only a single device – the first S4 Max on the account – is controlled.
The geometry helpers are pure functions and are unit‑tested so they can be
studied independently from the robot hardware.
"""

from __future__ import annotations

import argparse
import asyncio
import math
import os
from typing import Iterable, Iterator, List, Tuple

from dotenv import load_dotenv
from roborock.const import ROBOROCK_S4_MAX
from roborock.web_api import RoborockApiClient
from roborock.roborock_typing import RoborockCommand
from roborock.version_1_apis.roborock_mqtt_client_v1 import RoborockMqttClientV1
from roborock.containers import DeviceData

Point = Tuple[int, int]


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def circle(center: Point, radius_mm: int, steps: int = 20) -> Iterator[Point]:
    """Generate points on a circle."""

    cx, cy = center
    for i in range(steps):
        t = 2 * math.pi * i / steps
        yield int(cx + radius_mm * math.cos(t)), int(cy + radius_mm * math.sin(t))


def square(center: Point, half_mm: int = 600) -> List[Point]:
    """Return the corners of a square (closed path)."""

    cx, cy = center
    return [
        (cx - half_mm, cy - half_mm),
        (cx + half_mm, cy - half_mm),
        (cx + half_mm, cy + half_mm),
        (cx - half_mm, cy + half_mm),
        (cx - half_mm, cy - half_mm),
    ]


def figure_eight(center: Point, radius_mm: int = 800, steps: int = 24) -> Iterator[Point]:
    """Generate a figure‑eight (infinity symbol)."""

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
    """Generate a basic Lissajous curve."""

    cx, cy = center
    for i in range(steps):
        t = 2 * math.pi * i / steps
        x = cx + ax * math.sin(a * t + delta)
        y = cy + ay * math.sin(b * t)
        yield int(x), int(y)


# ---------------------------------------------------------------------------
# Roborock helpers
# ---------------------------------------------------------------------------

async def _login():
    """Log in to Roborock cloud and return user and home data."""

    email = os.environ.get("ROBO_EMAIL")
    password = os.environ.get("ROBO_PASSWORD")
    if not email or not password:
        raise RuntimeError("ROBO_EMAIL and ROBO_PASSWORD must be set in .env")

    api = RoborockApiClient(email)
    user_data = await api.pass_login(password)
    home_data = await api.get_home_data(user_data)
    return api, user_data, home_data


async def _client() -> RoborockMqttClientV1:
    _, user_data, home = await _login()

    # choose the first S4 Max
    for device, product in home.device_products.values():
        if product.model == ROBOROCK_S4_MAX:
            device_info = DeviceData(device=device, model=product.model)
            client = RoborockMqttClientV1(user_data, device_info)
            await client.async_connect()
            return client
    raise RuntimeError("No Roborock S4 Max found on this account")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

async def list_devices() -> None:
    """Print devices tied to the account."""

    _, _, home = await _login()
    for dev in home.devices:
        name = dev.name
        product_id = dev.product_id
        print(f"{name} ({product_id})")


async def beep() -> None:
    """Play the locate/beep sound."""
    client = await _client()
    try:
        await client.send_command(RoborockCommand.FIND_ME)
    finally:
        await client.async_disconnect()


async def clean() -> None:
    """Start a full cleaning cycle."""
    client = await _client()
    try:
        await client.send_command(RoborockCommand.APP_START)
    finally:
        await client.async_disconnect()


async def dock() -> None:
    """Return to the charging dock."""
    client = await _client()
    try:
        await client.send_command(RoborockCommand.APP_CHARGE)
    finally:
        await client.async_disconnect()


async def status() -> None:
    """Print battery level and state."""
    client = await _client()
    try:
        st = await client.get_status()
        state = st.state_name or "unknown"
        battery = st.battery if st.battery is not None else "?"
        print(f"State: {state}, Battery: {battery}%")
    finally:
        await client.async_disconnect()


async def goto(x: int, y: int) -> None:
    """Move to an absolute map coordinate in millimetres."""
    client = await _client()
    try:
        await client.send_command(RoborockCommand.APP_GOTO_TARGET, [x, y])
    finally:
        await client.async_disconnect()


async def _map_center(client: RoborockMqttClientV1) -> Point | None:
    """Return charger or vacuum position from the current map if available."""

    try:
        from vacuum_map_parser_base.config.color import ColorsPalette
        from vacuum_map_parser_base.config.image_config import ImageConfig
        from vacuum_map_parser_base.config.size import Sizes
        from vacuum_map_parser_roborock.map_data_parser import RoborockMapDataParser

        raw = await client.get_map_v1()
        if not raw:
            return None
        parser = RoborockMapDataParser(ColorsPalette(), Sizes(), [], ImageConfig(), [])
        data = parser.parse(raw)
        if data.charger is not None:
            return int(data.charger.x), int(data.charger.y)
        if data.vacuum_position is not None:
            return int(data.vacuum_position.x), int(data.vacuum_position.y)
    except Exception:
        return None
    return None


async def dance(pattern: str, size: int, beat_ms: int) -> None:
    """Dance using one of the built‑in patterns."""
    client = await _client()
    try:
        center = await _map_center(client)
        if center is None:
            center = (
                int(os.getenv("DEFAULT_CENTER_X", "32000")),
                int(os.getenv("DEFAULT_CENTER_Y", "27000")),
            )

        if pattern == "circle":
            points: Iterable[Point] = circle(center, size)
        elif pattern == "square":
            points = square(center, size)
        elif pattern == "figure8":
            points = figure_eight(center, size)
        elif pattern == "lissajous":
            points = lissajous(center, ax=size, ay=size)
        else:
            raise ValueError("Unknown pattern")

        for px, py in points:
            await client.send_command(RoborockCommand.APP_GOTO_TARGET, [px, py])
            await asyncio.sleep(beat_ms / 1000)
    finally:
        await client.async_disconnect()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Roborock Vacuum Ballet CLI")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("devices", help="List devices on the account")
    sub.add_parser("beep", help="Play locate sound")
    sub.add_parser("status", help="Show battery and state")
    sub.add_parser("clean", help="Start full cleaning cycle")
    sub.add_parser("dock", help="Return to charging dock")

    p_goto = sub.add_parser("goto", help="Move to map coordinates (mm)")
    p_goto.add_argument("x", type=int)
    p_goto.add_argument("y", type=int)

    p_dance = sub.add_parser("dance", help="Dance a pattern")
    p_dance.add_argument("pattern", choices=["circle", "square", "figure8", "lissajous"])
    p_dance.add_argument(
        "size",
        type=int,
        nargs="?",
        default=int(os.getenv("DEFAULT_RADIUS", "800")),
        help="Radius or half-size in mm",
    )
    p_dance.add_argument(
        "beat_ms",
        type=int,
        nargs="?",
        default=int(os.getenv("DEFAULT_BEAT_MS", "600")),
        help="Delay between points in milliseconds",
    )

    args = parser.parse_args(argv)

    if args.cmd == "devices":
        asyncio.run(list_devices())
    elif args.cmd == "beep":
        asyncio.run(beep())
    elif args.cmd == "status":
        asyncio.run(status())
    elif args.cmd == "clean":
        asyncio.run(clean())
    elif args.cmd == "dock":
        asyncio.run(dock())
    elif args.cmd == "goto":
        asyncio.run(goto(args.x, args.y))
    elif args.cmd == "dance":
        asyncio.run(dance(args.pattern, args.size, args.beat_ms))
    else:
        parser.print_help()


if __name__ == "__main__":  # pragma: no cover - manual invocation
    main()

