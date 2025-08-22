#!/usr/bin/env python3
"""Roborock Vacuum Ballet.

Tiny CLI and pattern generators to choreograph a Roborock **S4 Max** using
simple ``goto`` waypoints.  The script logs in with the credentials from a
``.env`` file and exposes a few sub-commands:

``devices``
    List devices on the account and highlight the S4 Max.

``beep``
    Make the robot play its locate/beep sound.

``goto X Y``
    Move the robot to ``(X, Y)`` in map millimetres.

``dance PATTERN SIZE [BEAT_MS]``
    Send a sequence of ``goto`` commands following ``PATTERN`` at the tempo
    defined by ``BEAT_MS`` (defaults to 600 ms between points).

Only a single device - the first S4 Max on the account - is controlled.
The geometry helpers are pure functions and are unit-tested so they can be
studied independently from the robot hardware.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import math
import os
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator, List, Tuple

from dotenv import load_dotenv, dotenv_values
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
        (int(cx - half_mm), int(cy - half_mm)),
        (int(cx + half_mm), int(cy - half_mm)),
        (int(cx + half_mm), int(cy + half_mm)),
        (int(cx - half_mm), int(cy + half_mm)),
        (int(cx - half_mm), int(cy - half_mm)),
    ]


def figure_eight(
    center: Point, radius_mm: int = 800, steps: int = 24
) -> Iterator[Point]:
    """Generate a figure-eight (infinity symbol)."""

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


def spin_crazy(center: Point, radius_mm: int = 400, steps: int = 20) -> Iterator[Point]:
    """Generate erratic spinning and jerky movements near center position.

    Creates a chaotic pattern with rapid direction changes, small spirals,
    and sudden jerks to simulate 'crazy' movement.
    """
    import random

    cx, cy = center
    # Set a consistent seed for reproducible 'craziness'
    random.seed(42)

    for i in range(steps):
        # Base circular motion with random radius variations
        base_angle = 2 * math.pi * i / steps * 3  # 3x speed for more spinning

        # Add random jerkiness - sudden direction changes
        jerk_factor = random.uniform(0.3, 1.8)
        angle_jitter = random.uniform(-math.pi / 2, math.pi / 2)
        actual_angle = base_angle + angle_jitter

        # Varying radius for erratic movement
        current_radius = radius_mm * jerk_factor * random.uniform(0.2, 1.0)

        # Add random offset for jerky movements
        jerk_x = random.uniform(-radius_mm * 0.3, radius_mm * 0.3)
        jerk_y = random.uniform(-radius_mm * 0.3, radius_mm * 0.3)

        x = cx + current_radius * math.cos(actual_angle) + jerk_x
        y = cy + current_radius * math.sin(actual_angle) + jerk_y

        # Occasionally add dramatic jerks to random positions
        if random.random() < 0.2:  # 20% chance of dramatic jerk
            jerk_distance = radius_mm * random.uniform(0.5, 1.2)
            jerk_angle = random.uniform(0, 2 * math.pi)
            x = cx + jerk_distance * math.cos(jerk_angle)
            y = cy + jerk_distance * math.sin(jerk_angle)

        yield int(x), int(y)


# ---------------------------------------------------------------------------
# Roborock helpers
# ---------------------------------------------------------------------------


def _setup_logging() -> None:
    """Initialize a simple file logger at logs/logs.txt."""
    log_dir = Path(__file__).resolve().parent.parent / "logs"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        # If we can't create a directory, silently skip logging setup
        return

    log_file = log_dir / "logs.txt"
    logger = logging.getLogger("vacuum_ballet")
    if logger.handlers:
        return

    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(str(log_file), encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def _load_envs() -> None:
    """Load base .env and optional project-specific env files.

    Load order (lowest to highest precedence, without overriding OS env):
    - .env
    - .env.ballet
    - .envs/controls.env
    """
    # Base credentials and simple defaults
    load_dotenv()

    # Optional project-specific env next
    base_dir = Path(__file__).resolve().parent.parent
    ballet_env = base_dir / ".env.ballet"
    if ballet_env.exists():
        load_dotenv(ballet_env, override=False)

    # Optional controls file inside .envs
    controls_env = base_dir / ".envs" / "controls.env"
    if controls_env.exists():
        # Respect OS env values already set
        # Only set keys that aren't present yet
        vals = dotenv_values(controls_env)
        for k, v in vals.items():
            if k not in os.environ and v is not None:
                os.environ[k] = v

async def _login():
    """Log in to Roborock cloud and return user and home data."""

    email = os.environ.get("ROBO_EMAIL")
    password = os.environ.get("ROBO_PASSWORD")
    if not email or not password:
        raise RuntimeError("ROBO_EMAIL and ROBO_PASSWORD must be set in .env")

    api = RoborockApiClient(email)
    user_data = await api.pass_login(password)
    home_data = await api.get_home_data(user_data)
    logging.getLogger("vacuum_ballet").info(
        "Logged in and fetched home data with %d devices", len(home_data.devices)
    )
    return api, user_data, home_data


async def _client() -> RoborockMqttClientV1:
    _, user_data, home = await _login()

    # choose the first S4 Max
    for device, product in home.device_products.values():
        if product.model == ROBOROCK_S4_MAX:
            device_info = DeviceData(device=device, model=product.model)
            client = RoborockMqttClientV1(user_data, device_info)
            await client.async_connect()
            logging.getLogger("vacuum_ballet").info(
                "Connected to device '%s' (%s)", device.name, product.model
            )
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
        logging.getLogger("vacuum_ballet").info("beep requested")
        await client.send_command(RoborockCommand.FIND_ME)
    finally:
        await client.async_disconnect()


async def clean() -> None:
    """Start a full cleaning cycle."""
    client = await _client()
    try:
        logging.getLogger("vacuum_ballet").info("clean start requested")
        await client.send_command(RoborockCommand.APP_START)
    finally:
        await client.async_disconnect()


async def dock() -> None:
    """Return to the charging dock."""
    client = await _client()
    try:
        logging.getLogger("vacuum_ballet").info("dock requested")
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
        logging.getLogger("vacuum_ballet").info(
            "Status queried: state=%s battery=%s", state, battery
        )
    finally:
        await client.async_disconnect()


async def where() -> None:
    """Show current robot position and map center info for debugging."""
    client = await _client()
    try:
        print("🤖 Robot Location Debug Info:")

        # Try to get current vacuum position
        vacuum_pos = await _vacuum_position(client)
        if vacuum_pos:
            print(f"   Current position: ({vacuum_pos[0]}, {vacuum_pos[1]}) mm")
        else:
            print("   Current position: Unable to detect")

        # Try to get map center (charger or vacuum position)
        map_center = await _map_center(client)
        if map_center:
            print(f"   Map center: ({map_center[0]}, {map_center[1]}) mm")
        else:
            print("   Map center: Unable to detect")
            default_x = int(os.getenv("DEFAULT_CENTER_X", "32000"))
            default_y = int(os.getenv("DEFAULT_CENTER_Y", "27000"))
            print(f"   Fallback center: ({default_x}, {default_y}) mm")

        # Show robot status
        st = await client.get_status()
        if st:
            state = st.state_name or "unknown"
            print(f"   Robot state: {state}")
            if hasattr(st, "in_cleaning") and st.in_cleaning is not None:
                print(f"   In cleaning mode: {st.in_cleaning}")
        logging.getLogger("vacuum_ballet").info(
            "where: pos=%s center=%s state=%s cleaning=%s",
            vacuum_pos,
            map_center,
            st.state_name if st else None,
            getattr(st, "in_cleaning", None) if st else None,
        )

        print("\n💡 Tips:")
        print(
            "   - If positions are 0 or very large numbers, the robot might not be localized"
        )
        print("   - Try running 'beep' first to wake the robot")
        print("   - Make sure the robot has completed initial mapping")

    finally:
        await client.async_disconnect()


async def goto(x: int, y: int) -> None:
    """Move to an absolute map coordinate in millimetres."""
    client = await _client()
    try:
        logging.getLogger("vacuum_ballet").info("goto requested: (%d, %d)", x, y)
        await client.send_command(RoborockCommand.APP_GOTO_TARGET, [x, y])
    finally:
        await client.async_disconnect()


async def _parse_map_data(client: RoborockMqttClientV1):
    """Parse map data from client. Returns parsed data or None on error."""
    try:
        from vacuum_map_parser_base.config.color import ColorsPalette
        from vacuum_map_parser_base.config.image_config import ImageConfig
        from vacuum_map_parser_base.config.size import Sizes
        from vacuum_map_parser_roborock.map_data_parser import RoborockMapDataParser

        raw = await client.get_map_v1()
        if not raw:
            return None
        parser = RoborockMapDataParser(ColorsPalette(), Sizes(), [], ImageConfig(), [])
        return parser.parse(raw)
    except Exception:
        return None


async def _map_center(client: RoborockMqttClientV1) -> Point | None:
    """Return charger or vacuum position from the current map if available."""
    data = await _parse_map_data(client)
    if data is None:
        return None

    if data.charger is not None:
        return int(data.charger.x), int(data.charger.y)
    if data.vacuum_position is not None:
        return int(data.vacuum_position.x), int(data.vacuum_position.y)
    return None


async def _charger_position(client: RoborockMqttClientV1) -> Point | None:
    """Return charger (dock) position if available."""
    data = await _parse_map_data(client)
    if data is None or data.charger is None:
        return None
    return int(data.charger.x), int(data.charger.y)


def _generate_map_image(data) -> "object | None":
    """Render a map image (PIL Image) from parsed map data, if possible.

    Returns a PIL Image or None if rendering isn't possible.
    """
    try:
        from vacuum_map_parser_base import image_generator
        from vacuum_map_parser_base.config.color import ColorsPalette
        from vacuum_map_parser_base.config.image_config import ImageConfig
        from vacuum_map_parser_base.config.size import Sizes
        from vacuum_map_parser_base.config.drawable import Drawable
    except Exception:
        return None

    gen = image_generator.ImageGenerator(
        ColorsPalette(),
        Sizes(),
        [
            Drawable.CLEANED_AREA.value,
            Drawable.ZONES.value,
            Drawable.NO_GO_AREAS.value,
            Drawable.VIRTUAL_WALLS.value,
            Drawable.PATH.value,
            Drawable.GOTO_PATH.value,
            Drawable.CHARGER.value,
            Drawable.VACUUM_POSITION.value,
        ],
        ImageConfig(),
        [],
    )

    if data is None:
        return gen.create_empty_map_image("NO MAP")

    if getattr(data, "image", None) is None:
        return gen.create_empty_map_image("NO MAP")

    # Mutates data.image.data in place
    gen.draw_map(data)
    return data.image.data


def _save_snapshot_image(image_obj: "object", suffix: str = "") -> Path | None:
    """Save a PIL Image to logs/maps with timestamp. Returns path or None."""
    try:
        logs_dir = Path(__file__).resolve().parent.parent / "logs" / "maps"
        logs_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        name = f"map_{ts}{suffix}.png"
        out_path = logs_dir / name
        image_obj.save(str(out_path), format="PNG")
        logging.getLogger("vacuum_ballet").info("saved map snapshot: %s", out_path)
        return out_path
    except Exception:
        return None


def _offset_center_from_dock(dock: Point, radius_mm: int) -> Point:
    """Return a center offset away from the dock by a safe buffer + radius.

    This helps avoid waypoints falling inside the charger/dock restricted area,
    which can cause the robot to spin and report 'Could not reach the target'.
    """
    buffer_mm = int(os.getenv("DOCK_BUFFER_MM", "300"))
    # Offset along +Y by default; simple and deterministic.
    offset_y = buffer_mm + radius_mm
    return dock[0], dock[1] + offset_y


async def _ensure_ready_for_goto(client: RoborockMqttClientV1) -> None:
    """Ensure robot will accept goto: wake, undock, and pause if necessary.

    Many firmwares accept APP_GOTO_TARGET best from a paused/active state.
    We optionally issue start->pause to undock and get out of idle/charging.
    Controlled by ENABLE_GOTO_PREFLIGHT (default: true).
    """
    if os.getenv("ENABLE_GOTO_PREFLIGHT", "1") not in {"1", "true", "True"}:
        return

    try:
        st = await client.get_status()
        state = (st.state_name or "").lower() if st else ""
    except Exception:
        state = ""

    # States that usually don't need preflight
    no_op_states = {"going_to_target", "spot", "cleaning", "returning"}
    if state in no_op_states:
        return

    # Wake up if needed
    try:
        await client.send_command(RoborockCommand.APP_WAKEUP_ROBOT)
    except Exception:
        pass

    # Start then pause to undock and enter an active paused state
    try:
        await client.send_command(RoborockCommand.APP_START)
    except Exception:
        pass
    await asyncio.sleep(float(os.getenv("PREFLIGHT_START_DELAY_S", "0.4")))
    try:
        await client.send_command(RoborockCommand.APP_PAUSE)
    except Exception:
        pass
    await asyncio.sleep(float(os.getenv("PREFLIGHT_PAUSE_DELAY_S", "0.3")))


async def _vacuum_position(client: RoborockMqttClientV1) -> Point | None:
    """Return the vacuum position from the current map if available.

    This intentionally ignores the charger position so it can be used for
    arrival-gating while the robot is moving.
    """
    data = await _parse_map_data(client)
    if data is None:
        return None

    if data.vacuum_position is not None:
        return int(data.vacuum_position.x), int(data.vacuum_position.y)
    return None


def _clamp_radius(size: int) -> int:
    """Clamp dance size to a safe range, configurable via env vars."""

    # Defaults align with test expectations when env vars are missing
    min_mm = int(os.getenv("MIN_DANCE_RADIUS_MM", "200"))
    max_mm = int(os.getenv("MAX_DANCE_RADIUS_MM", "1200"))
    return max(min_mm, min(size, max_mm))


async def _wait_until_near(
    client: RoborockMqttClientV1,
    target: Point,
    threshold_mm: int,
    timeout_s: float,
    poll_s: float = 0.4,
) -> bool:
    """Wait until the robot is within ``threshold_mm`` of ``target``.

    Returns True on near-arrival, False on timeout or if position is unavailable.
    """

    # Allow overriding poll interval via env to reduce map spam
    try:
        env_poll = os.getenv("ARRIVAL_POLL_S")
        if env_poll is not None:
            poll_s = float(env_poll)
    except Exception:
        pass

    deadline = asyncio.get_event_loop().time() + timeout_s
    while asyncio.get_event_loop().time() < deadline:
        pos = await _vacuum_position(client)
        if pos is None:
            await asyncio.sleep(poll_s)
            continue
        distance_mm = ((pos[0] - target[0]) ** 2 + (pos[1] - target[1]) ** 2) ** 0.5
        if distance_mm <= threshold_mm:
            return True
        await asyncio.sleep(poll_s)
    return False


async def dance(pattern: str, size: int, beat_ms: int) -> None:
    """Dance using one of the built-in patterns."""
    client = await _client()
    try:
        print(f"🕺 Starting {pattern} dance (size: {size}mm, beat: {beat_ms}ms)")
        log = logging.getLogger("vacuum_ballet")

        # Clamp size first so offset uses the final radius
        size = _clamp_radius(size)
        if size != int(os.getenv("DEFAULT_RADIUS", "800")):
            print(f"   📐 Clamped dance size to: {size}mm")

        # Prefer dancing around the dock (charger) when available
        dock = await _charger_position(client)
        if dock:
            center = _offset_center_from_dock(dock, size)
            print(f"   Centering near dock at: ({dock[0]}, {dock[1]}) mm")
            print(f"   Using offset center: ({center[0]}, {center[1]}) mm")
        else:
            # Next best: current robot position
            current_pos = await _vacuum_position(client)
            if current_pos:
                center = current_pos
                print(f"   Centering at robot position: ({center[0]}, {center[1]}) mm")
            else:
                # Fallback to map center (if any), else small safe defaults
                center = await _map_center(client)
                if center:
                    print(f"   Using map-derived center: ({center[0]}, {center[1]}) mm")
                else:
                    center = (
                        int(os.getenv("DEFAULT_CENTER_X", "0")),
                        int(os.getenv("DEFAULT_CENTER_Y", "0")),
                    )
                    print(f"   ⚠️  Using fallback center: ({center[0]}, {center[1]}) mm")
                    print(
                        "   💡 Consider setting DEFAULT_CENTER_X/Y environment variables"
                    )
        log.info(
            "dance start: pattern=%s size=%s beat_ms=%s center=%s",
            pattern,
            size,
            beat_ms,
            center,
        )

        if pattern == "circle":
            points: Iterable[Point] = circle(center, size)
        elif pattern == "square":
            points = square(center, size)
        elif pattern == "figure8":
            points = figure_eight(center, size)
        elif pattern == "lissajous":
            points = lissajous(center, ax=size, ay=size)
        elif pattern == "spin_crazy":
            points = spin_crazy(center, size)
        else:
            raise ValueError("Unknown pattern")

        # Arrival gating and beat timing
        arrival_mm = int(os.getenv("ARRIVAL_THRESHOLD_MM", "250"))
        hop_timeout_s = float(os.getenv("WAYPOINT_TIMEOUT_S", "35"))
        min_beat_s = beat_ms / 1000

        # Generate all waypoints first to show preview
        waypoints = list(points)
        print(f"   🎯 Dance will visit {len(waypoints)} waypoints")
        log.info("generated %d waypoints", len(waypoints))

        # Ensure robot will accept goto commands
        await _ensure_ready_for_goto(client)

        for i, (px, py) in enumerate(waypoints, 1):
            # Keep stdout concise; detailed targets go to the log file
            if i == 1 or i == len(waypoints) or i % 5 == 0:
                print(f"   Step {i}/{len(waypoints)}")
            log.info("waypoint %d/%d -> (%d, %d)", i, len(waypoints), px, py)

            try:
                # Skip waypoints already within arrival threshold
                current_pos = await _vacuum_position(client)
                if current_pos is not None:
                    dist = ((current_pos[0]-px)**2 + (current_pos[1]-py)**2) ** 0.5
                    if dist <= arrival_mm:
                        log.info("skip waypoint %d: already within %.0fmm (%.0fmm)", i, arrival_mm, dist)
                        continue

                await client.send_command(RoborockCommand.APP_GOTO_TARGET, [px, py])
                # Prefer arrival gating; if it times out, fall back to beat
                arrived = await _wait_until_near(
                    client, (px, py), arrival_mm, timeout_s=hop_timeout_s
                )
                # Optional settle delay after near-arrival to let odometry catch up
                if arrived:
                    settle_s = float(os.getenv("ARRIVAL_SETTLE_S", "0.2"))
                    if settle_s > 0:
                        await asyncio.sleep(settle_s)
                elif min_beat_s > 0:
                    log.debug("arrival timed out; beat sleep %.3fs", min_beat_s)
                    await asyncio.sleep(min_beat_s)

            except Exception as e:
                log.exception("error sending waypoint %d: %s", i, e)
                # Re-raise to surface error to caller/tests while still disconnecting in finally
                raise

        print("   🎉 Dance complete!")
        log.info("dance complete")
    finally:
        await client.async_disconnect()


async def mapsnap() -> None:
    """Fetch current map and save one PNG snapshot in logs/maps."""
    client = await _client()
    try:
        data = await _parse_map_data(client)
        image_obj = _generate_map_image(data)
        if image_obj is None:
            print("Could not render map image (missing parser/image libs)")
            return
        out = _save_snapshot_image(image_obj)
        if out:
            print(f"Saved map snapshot to: {out}")
        else:
            print("Failed to save map snapshot")
    finally:
        await client.async_disconnect()


async def mapwatch(interval_s: float, count: int) -> None:
    """Periodically save map snapshots to logs/maps."""
    client = await _client()
    try:
        for i in range(count):
            data = await _parse_map_data(client)
            image_obj = _generate_map_image(data)
            if image_obj is not None:
                _save_snapshot_image(image_obj, suffix=f"_{i:03d}")
            await asyncio.sleep(interval_s)
        print(f"Saved {count} snapshot(s) to logs/maps")
    finally:
        await client.async_disconnect()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    _load_envs()
    _setup_logging()
    parser = argparse.ArgumentParser(description="Roborock Vacuum Ballet CLI")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("devices", help="List devices on the account")
    sub.add_parser("beep", help="Play locate sound")
    sub.add_parser("status", help="Show battery and state")
    sub.add_parser("where", help="Show robot position and coordinates for debugging")
    sub.add_parser("clean", help="Start full cleaning cycle")
    sub.add_parser("dock", help="Return to charging dock")
    sub.add_parser("mapsnap", help="Save one lidar map snapshot to logs/maps")

    p_goto = sub.add_parser("goto", help="Move to map coordinates (mm)")
    p_goto.add_argument("x", type=int)
    p_goto.add_argument("y", type=int)

    p_dance = sub.add_parser("dance", help="Dance a pattern")
    p_watch = sub.add_parser("mapwatch", help="Periodically save map snapshots")
    p_watch.add_argument("interval_s", type=float, nargs="?", default=float(os.getenv("MAPWATCH_INTERVAL_S", "5")))
    p_watch.add_argument("count", type=int, nargs="?", default=int(os.getenv("MAPWATCH_COUNT", "12")))
    p_dance.add_argument(
        "pattern", choices=["circle", "square", "figure8", "lissajous", "spin_crazy"]
    )
    p_dance.add_argument(
        "size",
        type=int,
        nargs="?",
        default=int(os.getenv("DEFAULT_RADIUS", "400")),
        help="Radius or half-size in mm",
    )
    p_dance.add_argument(
        "beat_ms",
        type=int,
        nargs="?",
        default=int(os.getenv("DEFAULT_BEAT_MS", "1000")),
        help="Delay between points in milliseconds",
    )

    args = parser.parse_args(argv)

    if args.cmd == "devices":
        asyncio.run(list_devices())
    elif args.cmd == "beep":
        asyncio.run(beep())
    elif args.cmd == "status":
        asyncio.run(status())
    elif args.cmd == "where":
        asyncio.run(where())
    elif args.cmd == "clean":
        asyncio.run(clean())
    elif args.cmd == "dock":
        asyncio.run(dock())
    elif args.cmd == "goto":
        asyncio.run(goto(args.x, args.y))
    elif args.cmd == "dance":
        asyncio.run(dance(args.pattern, args.size, args.beat_ms))
    elif args.cmd == "mapsnap":
        asyncio.run(mapsnap())
    elif args.cmd == "mapwatch":
        asyncio.run(mapwatch(args.interval_s, args.count))
    else:
        parser.print_help()


if __name__ == "__main__":  # pragma: no cover - manual invocation
    main()
