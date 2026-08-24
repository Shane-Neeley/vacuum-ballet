#!/usr/bin/env python3
"""CLI entrypoint for the Roborock agent layer."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from intents import intent_plan, parse_kid_request
from patterns import Point
from playground import SCENARIOS, run_playground
from remote import remote_dance_plan
from roborock_agent import AgentConfig, AgentError, RoborockAgent, _load_or_login
from safety import SafetyPolicy, dance_plan


def _load_env() -> None:
    load_dotenv()
    root = Path(__file__).resolve().parent.parent
    load_dotenv(root / ".env.ballet", override=False)


def _setup_logging() -> None:
    root = Path(__file__).resolve().parent.parent
    log_dir = root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[logging.FileHandler(log_dir / "logs.txt", encoding="utf-8")],
    )


def _print(value: Any, as_json: bool = False) -> None:
    if as_json:
        print(json.dumps(value, indent=2, default=str))
    elif isinstance(value, (dict, list)):
        print(json.dumps(value, indent=2, default=str))
    else:
        print(value)


def _confirm(args: argparse.Namespace, action: str) -> None:
    if not args.confirm:
        raise AgentError(f"{action} controls a real vacuum; repeat with --confirm")


async def _run(args: argparse.Namespace) -> Any:
    config = AgentConfig.from_env()
    if args.cmd == "login":
        await _load_or_login(config, fresh=True)
        return {"logged_in": True, "cache_path": str(config.user_params_path)}

    # Planning and comedy stay offline by design.  They are the safe default
    # for agent and kid experimentation while the real device is unverified.
    if args.cmd == "play":
        return run_playground(args.scenario, steps=args.steps)
    if args.cmd == "preview":
        try:
            return dance_plan(args.pattern, (args.center_x, args.center_y), args.size, args.beat_ms)
        except (TypeError, ValueError) as exc:
            raise AgentError(str(exc)) from exc
    if args.cmd == "remote-preview":
        try:
            return remote_dance_plan(args.style)
        except ValueError as exc:
            raise AgentError(str(exc)) from exc
    if args.cmd == "ask":
        try:
            parsed = parse_kid_request(" ".join(args.text))
        except ValueError as exc:
            raise AgentError(str(exc)) from exc
        if parsed.simulator_only:
            return run_playground(parsed.args["scenario"])
        if not args.execute:
            result = intent_plan(parsed)
            if parsed.action == "dance":
                try:
                    result["dance_preview"] = dance_plan(
                        parsed.args["pattern"],
                        (0, 0),
                        parsed.args["size"],
                        parsed.args["beat_ms"],
                    )
                except (TypeError, ValueError) as exc:
                    raise AgentError(str(exc)) from exc
            return result
        if parsed.requires_confirmation and not args.confirm:
            raise AgentError("physical ask requires both --execute and --confirm")
        args.cmd = parsed.action
        for key, value in parsed.args.items():
            setattr(args, key, value)

    if args.cmd == "intent":
        try:
            payload = json.loads(args.payload)
        except json.JSONDecodeError as exc:
            raise AgentError(f"intent payload is not valid JSON: {exc.msg}") from exc
        if not isinstance(payload, dict):
            raise AgentError("intent payload must be a JSON object")
        action = payload.get("action")
        known_actions = {
            "devices", "status", "where", "map", "rooms", "beep", "clean", "clean_rooms",
            "dock", "pause", "stop", "goto", "dance", "preview", "remote_preview",
            "remote_dance", "play",
        }
        if action not in known_actions:
            raise AgentError(f"Unknown intent action: {action!r}")
        if action == "play":
            try:
                return run_playground(str(payload.get("scenario", "failure")))
            except ValueError as exc:
                raise AgentError(str(exc)) from exc
        if action == "preview":
            center_payload = payload.get("center", {"x": 0, "y": 0})
            if not isinstance(center_payload, dict):
                raise AgentError("preview center must be an object with x and y")
            try:
                return dance_plan(
                    str(payload.get("pattern", "circle")),
                    (int(center_payload["x"]), int(center_payload["y"])),
                    int(payload.get("size", 300)),
                    int(payload.get("beat_ms", 500)),
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise AgentError(str(exc)) from exc
        if action == "remote_preview":
            try:
                return remote_dance_plan(str(payload.get("style", "crazy")))
            except ValueError as exc:
                raise AgentError(str(exc)) from exc
        writes = {
            "clean", "clean_rooms", "dock", "pause", "stop", "beep", "goto", "dance", "remote_dance",
        }
        if action in writes and not payload.get("confirm", False):
            raise AgentError(f"intent {action!r} requires JSON field confirm=true")
        args.cmd = action
        for key, value in payload.items():
            setattr(args, key, value)
        if action == "dance":
            args.pattern = str(payload.get("pattern", "circle"))
            args.size = int(payload.get("size", os.getenv("DEFAULT_RADIUS", "400")))
            args.beat_ms = int(payload.get("beat_ms", config.default_beat_ms))
        if action == "dance" and isinstance(payload.get("center"), dict):
            args.center_x = int(payload["center"]["x"])
            args.center_y = int(payload["center"]["y"])
        if action == "clean_rooms":
            try:
                args.segments = [int(segment) for segment in payload["segments"]]
            except (KeyError, TypeError, ValueError) as exc:
                raise AgentError("clean_rooms intent requires an integer segments array") from exc
            args.repeat = int(payload.get("repeat", 1))
        if action == "remote_dance":
            args.cmd = "remote-dance"
            args.style = str(payload.get("style", "crazy"))
        args.confirm = bool(payload.get("confirm", False))
        args.as_json = True

    writes = {
        "clean", "clean_rooms", "dock", "pause", "stop", "beep", "goto", "dance", "remote-dance",
    }
    if args.cmd in writes:
        _confirm(args, args.cmd)
    if args.cmd == "dance":
        try:
            # Validate geometry before opening a session.  The real centre is
            # resolved from the map later, but size/tempo safety is offline.
            dance_plan(
                args.pattern,
                (0, 0),
                args.size,
                args.beat_ms,
                policy=SafetyPolicy(
                    min_radius_mm=config.min_radius_mm,
                    max_radius_mm=config.max_radius_mm,
                    min_beat_ms=config.min_beat_ms,
                    max_waypoints=config.max_waypoints,
                ),
                real_robot=True,
            )
        except (TypeError, ValueError) as exc:
            raise AgentError(str(exc)) from exc
    if args.cmd == "clean_rooms":
        try:
            SafetyPolicy().validate_segments(args.segments, args.repeat)
        except ValueError as exc:
            raise AgentError(str(exc)) from exc

    require_device = args.cmd != "devices"
    async with await RoborockAgent.connect(
        config,
        fresh_login=args.fresh_login,
        require_device=require_device,
    ) as agent:
        if args.cmd == "devices":
            return await agent.devices()
        if args.cmd == "status":
            return await agent.status()
        if args.cmd == "where":
            result = await agent.status()
            result["map"] = (await agent.map_info())["map"]
            return result
        if args.cmd == "rooms":
            return await agent.rooms()
        if args.cmd == "map":
            path = Path(args.save) if getattr(args, "save", None) else None
            if path is None:
                path = Path("logs/maps") / f"map_{datetime.now():%Y%m%d-%H%M%S}.png"
            return await agent.map_info(path)
        if args.cmd == "beep":
            return await agent.beep()
        if args.cmd == "clean":
            return await agent.clean()
        if args.cmd == "clean_rooms":
            return await agent.clean_rooms(args.segments, args.repeat)
        if args.cmd == "dock":
            return await agent.dock()
        if args.cmd == "pause":
            return await agent.pause()
        if args.cmd == "stop":
            return await agent.stop()
        if args.cmd == "goto":
            return await agent.goto((args.x, args.y))
        if args.cmd == "dance":
            center: Point | None = None
            if getattr(args, "center_x", None) is not None and getattr(args, "center_y", None) is not None:
                center = (args.center_x, args.center_y)
            return await agent.dance(args.pattern, args.size, args.beat_ms, center)
        if args.cmd == "remote-dance":
            return await agent.remote_dance(args.style)
        raise AgentError(f"Unknown command: {args.cmd}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Agent-friendly Roborock coordinator")
    parser.add_argument("--fresh-login", action="store_true", help="Ignore cached login data")
    parser.add_argument("--json", dest="as_json", action="store_true", help="Print machine-readable JSON")
    parser.add_argument("--confirm", action="store_true", help="Confirm a real-vacuum action")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("login", help="Authenticate and cache the Roborock session")
    sub.add_parser("devices", help="Discover devices and connection modes")
    sub.add_parser("status", help="Refresh target status")
    sub.add_parser("where", help="Refresh status and current map positions")
    sub.add_parser("rooms", help="Refresh map room-to-segment names")
    p_map = sub.add_parser("map", help="Refresh parsed map and save a PNG")
    p_map.add_argument("--save", help="Output PNG path")
    p_beep = sub.add_parser("beep", help="Play the locate sound")
    p_beep.add_argument("--confirm", action="store_true", default=argparse.SUPPRESS)
    for name, help_text in (("clean", "Start cleaning"), ("dock", "Return to dock"), ("pause", "Pause"), ("stop", "Stop")):
        action_parser = sub.add_parser(name, help=help_text)
        action_parser.add_argument("--confirm", action="store_true", default=argparse.SUPPRESS)

    p_clean_rooms = sub.add_parser("clean-rooms", help="Clean selected map segments")
    p_clean_rooms.add_argument("segments", type=int, nargs="+")
    p_clean_rooms.add_argument("--repeat", type=int, default=1)
    p_clean_rooms.add_argument("--confirm", action="store_true", default=argparse.SUPPRESS)

    p_goto = sub.add_parser("goto", help="Send a map-frame Pin n Go target")
    p_goto.add_argument("x", type=int)
    p_goto.add_argument("y", type=int)
    p_goto.add_argument("--confirm", action="store_true", default=argparse.SUPPRESS)

    p_dance = sub.add_parser("dance", help="Send a previewable waypoint pattern")
    p_dance.add_argument("pattern", choices=["circle", "square", "figure8", "lissajous", "spin", "spin_crazy"])
    p_dance.add_argument("size", type=int, nargs="?", default=int(os.getenv("DEFAULT_RADIUS", "400")))
    p_dance.add_argument("beat_ms", type=int, nargs="?", default=int(os.getenv("DEFAULT_BEAT_MS", "500")))
    p_dance.add_argument("--center-x", type=int)
    p_dance.add_argument("--center-y", type=int)
    p_dance.add_argument("--confirm", action="store_true", default=argparse.SUPPRESS)

    p_preview = sub.add_parser("preview", help="Build a dance plan without connecting to Roborock")
    p_preview.add_argument("pattern", choices=["circle", "square", "figure8", "lissajous", "spin", "spin_crazy"])
    p_preview.add_argument("size", type=int, nargs="?", default=int(os.getenv("DEFAULT_RADIUS", "400")))
    p_preview.add_argument("beat_ms", type=int, nargs="?", default=int(os.getenv("DEFAULT_BEAT_MS", "500")))
    p_preview.add_argument("--center-x", type=int, default=0)
    p_preview.add_argument("--center-y", type=int, default=0)

    p_remote_preview = sub.add_parser("remote-preview", help="Preview a bounded joystick-style dance")
    p_remote_preview.add_argument("style", choices=["wiggle", "spin", "crazy", "drift", "sprint"])

    p_remote = sub.add_parser("remote-dance", help="Run a bounded joystick-style dance")
    p_remote.add_argument("style", choices=["wiggle", "spin", "crazy", "drift", "sprint"])
    p_remote.add_argument("--confirm", action="store_true", default=argparse.SUPPRESS)

    p_play = sub.add_parser("play", help="Run a simulator-only kid comedy routine")
    p_play.add_argument("scenario", choices=list(SCENARIOS))
    p_play.add_argument("--steps", type=int, default=5)

    p_ask = sub.add_parser("ask", help="Plan a kid-style request; add --execute to run it")
    p_ask.add_argument("text", nargs="+")
    p_ask.add_argument("--execute", action="store_true", help="Allow the parsed request to run")
    p_ask.add_argument("--confirm", action="store_true", default=argparse.SUPPRESS)

    p_intent = sub.add_parser("intent", help="Run a structured JSON intent")
    p_intent.add_argument("payload", help='e.g. \'{"action":"status"}\'')
    return parser


def main(argv: list[str] | None = None) -> None:
    _load_env()
    _setup_logging()
    parser = _parser()
    args = parser.parse_args(argv)
    if not args.cmd:
        parser.print_help()
        return
    try:
        result = asyncio.run(_run(args))
    except (AgentError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    else:
        _print(result, args.as_json)


if __name__ == "__main__":
    main()
