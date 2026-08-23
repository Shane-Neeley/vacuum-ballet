"""Small, capability-oriented control layer for Roborock V1 vacuums.

This module deliberately hides the upstream transport details. Callers work
with a selected device and a small set of explicit intents while
``python-roborock`` handles cloud login, MQTT, local fallback, reconnects,
and device-specific traits.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from roborock import RoborockCommand
from roborock.devices.device import RoborockDevice
from roborock.devices.device_manager import DeviceManager, UserParams, create_device_manager
from roborock.devices.file_cache import FileCache, load_value, store_value
from roborock.exceptions import RoborockException
from roborock.web_api import RoborockApiClient

from patterns import Point
from safety import SafetyPolicy, dance_plan

LOGGER = logging.getLogger("vacuum_ballet")


class AgentError(RuntimeError):
    """Expected configuration, selection, or safety error."""


@dataclass(frozen=True)
class AgentConfig:
    """Runtime configuration loaded from environment variables."""

    username: str | None = None
    password: str | None = None
    code: str | None = None
    device_name: str | None = None
    duid: str | None = None
    cache_dir: Path = Path.home() / ".cache" / "vacuum-ballet"
    min_radius_mm: int = 200
    max_radius_mm: int = 1200
    default_beat_ms: int = 500
    default_center: Point | None = None
    min_beat_ms: int = 250
    max_waypoints: int = 32

    @classmethod
    def from_env(cls) -> "AgentConfig":
        """Build configuration without ever logging credential values."""
        center: Point | None = None
        x, y = os.getenv("DEFAULT_CENTER_X"), os.getenv("DEFAULT_CENTER_Y")
        if x is not None and y is not None:
            center = (int(x), int(y))
        cache_dir = Path(os.getenv("ROBOROCK_CACHE_DIR", str(Path.home() / ".cache" / "vacuum-ballet")))
        return cls(
            username=os.getenv("ROBO_EMAIL"),
            password=os.getenv("ROBO_PASSWORD"),
            code=os.getenv("ROBO_CODE"),
            device_name=os.getenv("ROBO_DEVICE_NAME"),
            duid=os.getenv("ROBO_DUID"),
            cache_dir=cache_dir,
            min_radius_mm=int(os.getenv("MIN_DANCE_RADIUS_MM", "200")),
            max_radius_mm=int(os.getenv("MAX_DANCE_RADIUS_MM", "1200")),
            default_beat_ms=int(os.getenv("DEFAULT_BEAT_MS", "500")),
            default_center=center,
            min_beat_ms=int(os.getenv("MIN_DANCE_BEAT_MS", "250")),
            max_waypoints=int(os.getenv("MAX_DANCE_WAYPOINTS", "32")),
        )

    @property
    def user_params_path(self) -> Path:
        return self.cache_dir / "user-params.pkl"

    @property
    def device_cache_path(self) -> Path:
        return self.cache_dir / "device-cache.pkl"


async def _load_or_login(config: AgentConfig, fresh: bool = False) -> UserParams:
    """Load cached auth data or perform one password login."""
    if not fresh:
        cached = await load_value(config.user_params_path)
        if isinstance(cached, UserParams):
            return cached

    if not config.username or not config.password:
        raise AgentError(
            "Roborock credentials are not configured. Copy .env.example to .env and set "
            "ROBO_EMAIL and ROBO_PASSWORD, then retry."
        )

    api = RoborockApiClient(username=config.username)
    try:
        user_data = await api.pass_login(config.password)
    except RoborockException as exc:
        if "2031" not in str(exc):
            raise AgentError(f"Roborock login failed: {exc}") from exc
        LOGGER.info("Roborock requires two-step validation; requesting an email code")
        user_data = await _code_login(api, config.code)
    params = UserParams(
        username=config.username,
        user_data=user_data,
        base_url=await api.base_url,
    )
    config.cache_dir.mkdir(parents=True, exist_ok=True)
    await store_value(config.user_params_path, params)
    try:
        config.user_params_path.chmod(0o600)
    except OSError:
        LOGGER.debug("Could not tighten auth cache permissions", exc_info=True)
    return params


async def _code_login(api: RoborockApiClient, configured_code: str | None = None) -> Any:
    """Complete the current Roborock email-code login flow."""
    code = configured_code
    if not code:
        try:
            await api.request_code_v4()
        except RoborockException as exc:
            if _is_code_rate_limit(exc):
                raise AgentError(
                    "Roborock is rate-limiting verification-code requests. Wait for the cooldown and "
                    "do not keep retrying login; a fresh code can then be entered locally."
                ) from exc
            raise AgentError(f"Could not request the Roborock verification code: {exc}") from exc
        try:
            code = input("Enter the Roborock verification code sent to your email: ").strip()
        except EOFError as exc:
            raise AgentError(
                "Roborock requires two-step validation. Run this command in an interactive terminal "
                "or set ROBO_CODE for this one login."
            ) from exc
    if not code:
        raise AgentError("A Roborock verification code is required")
    try:
        return await api.code_login_v4(code)
    except RoborockException as exc:
        raise AgentError(f"Roborock verification failed: {exc}") from exc


def _device_summary(device: RoborockDevice) -> dict[str, Any]:
    return {
        "name": device.name,
        "duid": device.duid,
        "model": device.product.model,
        "protocol": device.device_info.pv,
        "connected": device.is_connected,
        "local_connected": device.is_local_connected,
        "supports_v1": device.v1_properties is not None,
    }


def _point_dict(point: Any) -> dict[str, int] | None:
    if point is None or not hasattr(point, "x") or not hasattr(point, "y"):
        return None
    return {"x": int(point.x), "y": int(point.y)}


def _is_code_rate_limit(exc: BaseException) -> bool:
    message = str(exc).casefold()
    return (
        "too many" in message
        or "toomany" in message
        or "rate limit" in message
        or "rate_limit" in message
    )


class RoborockAgent:
    """Connected, selected Roborock device with explicit safe operations."""

    def __init__(
        self,
        manager: DeviceManager,
        cache: FileCache,
        device: RoborockDevice | None,
        config: AgentConfig | None = None,
    ) -> None:
        self.manager = manager
        self.cache = cache
        self.device = device
        self.config = config or AgentConfig.from_env()

    @classmethod
    async def connect(
        cls,
        config: AgentConfig,
        *,
        fresh_login: bool = False,
        require_device: bool = True,
    ) -> "RoborockAgent":
        """Connect through the current upstream DeviceManager API."""
        params = await _load_or_login(config, fresh=fresh_login)
        config.cache_dir.mkdir(parents=True, exist_ok=True)
        cache = FileCache(config.device_cache_path)
        try:
            manager = await create_device_manager(params, cache=cache, prefer_cache=not fresh_login)
        except Exception as exc:
            # A cached token can expire. Retry once with a fresh password login
            # when credentials are available, without overwriting the first error.
            if not fresh_login and config.username and config.password:
                LOGGER.info("Cached Roborock session failed; retrying fresh login")
                params = await _load_or_login(config, fresh=True)
                try:
                    manager = await create_device_manager(params, cache=cache, prefer_cache=False)
                except Exception as retry_exc:
                    raise AgentError(f"Could not connect to Roborock after fresh login: {retry_exc}") from retry_exc
            else:
                raise AgentError(f"Could not connect to Roborock: {exc}") from exc

        try:
            devices = await manager.get_devices()
            selected = _select_device(devices, config)
            if require_device and selected is None:
                raise AgentError(
                    "No target V1 vacuum selected. Set ROBO_DEVICE_NAME or ROBO_DUID in .env. "
                    f"Available devices: {json.dumps([_device_summary(d) for d in devices])}"
                )
        except Exception:
            await manager.close()
            await cache.flush()
            raise
        return cls(manager, cache, selected, config)

    async def __aenter__(self) -> "RoborockAgent":
        return self

    async def __aexit__(self, _exc_type: Any, _exc: Any, _tb: Any) -> None:
        await self.manager.close()
        await self.cache.flush()

    def require_device(self) -> RoborockDevice:
        if self.device is None:
            raise AgentError("This operation requires a selected V1 Roborock vacuum")
        if self.device.v1_properties is None:
            raise AgentError(f"Device {self.device.name!r} does not expose the V1 vacuum API")
        return self.device

    def safety_policy(self) -> SafetyPolicy:
        return SafetyPolicy(
            min_radius_mm=self.config.min_radius_mm,
            max_radius_mm=self.config.max_radius_mm,
            min_beat_ms=self.config.min_beat_ms,
            max_waypoints=self.config.max_waypoints,
        )

    async def devices(self) -> list[dict[str, Any]]:
        return [_device_summary(device) for device in await self.manager.get_devices()]

    async def status(self) -> dict[str, Any]:
        device = self.require_device()
        props = device.v1_properties
        assert props is not None
        await props.status.refresh()
        status = props.status.as_dict()
        status.update(
            {
                "state_name": props.status.state_name,
                "error_code_name": props.status.error_code_name,
                "current_map": props.status.current_map,
            }
        )
        return {
            "device": _device_summary(device),
            "status": status,
        }

    async def map_info(self, save_to: Path | None = None) -> dict[str, Any]:
        """Refresh the parsed map and optionally save its rendered PNG."""
        device = self.require_device()
        props = device.v1_properties
        assert props is not None
        await props.status.refresh()
        await props.map_content.refresh()
        map_data = props.map_content.map_data
        image_path: str | None = None
        if save_to is not None:
            if not props.map_content.image_content:
                raise AgentError("Roborock returned no rendered map image")
            save_to.parent.mkdir(parents=True, exist_ok=True)
            save_to.write_bytes(props.map_content.image_content)
            image_path = str(save_to)
        return {
            "device": _device_summary(device),
            "map": {
                "current_map": props.status.current_map,
                "charger": _point_dict(getattr(map_data, "charger", None)),
                "vacuum_position": _point_dict(getattr(map_data, "vacuum_position", None)),
                "image_path": image_path,
            },
        }

    async def send(self, command: RoborockCommand | str, params: Any = None) -> Any:
        """Send one explicitly chosen V1 command through the trait API."""
        device = self.require_device()
        props = device.v1_properties
        assert props is not None
        return await props.command.send(command, params)

    async def clean(self) -> Any:
        return await self.send(RoborockCommand.APP_START)

    async def dock(self) -> Any:
        return await self.send(RoborockCommand.APP_CHARGE)

    async def pause(self) -> Any:
        return await self.send(RoborockCommand.APP_PAUSE)

    async def stop(self) -> Any:
        return await self.send(RoborockCommand.APP_STOP)

    async def beep(self) -> Any:
        return await self.send(RoborockCommand.FIND_ME)

    async def rooms(self) -> list[dict[str, Any]]:
        """Refresh and return the V1 map's segment-to-room mapping."""
        device = self.require_device()
        props = device.v1_properties
        assert props is not None
        rooms_trait = getattr(props, "rooms", None)
        if rooms_trait is None:
            raise AgentError("This vacuum does not expose the V1 rooms trait")
        await rooms_trait.refresh()
        return [
            {
                "segment_id": int(room.segment_id),
                "iot_id": room.iot_id,
                "name": room.raw_name,
            }
            for room in (rooms_trait.rooms or [])
        ]

    async def clean_rooms(self, segments: list[int], repeat: int = 1) -> Any:
        """Start a bounded segment clean using the current upstream payload."""
        policy = self.safety_policy()
        try:
            policy.validate_segments(segments, repeat)
        except ValueError as exc:
            raise AgentError(str(exc)) from exc
        return await self.send(
            RoborockCommand.APP_SEGMENT_CLEAN,
            [{"segments": [int(segment) for segment in segments], "repeat": int(repeat)}],
        )

    async def goto(self, point: Point) -> Any:
        """Send a map-frame Pin n Go target in millimetres."""
        return await self.send(RoborockCommand.APP_GOTO_TARGET, [int(point[0]), int(point[1])])

    async def dance(self, pattern: str, size_mm: int, beat_ms: int, center: Point | None = None) -> dict[str, Any]:
        """Send a previewable sequence of map-frame targets."""
        device = self.require_device()
        if center is None:
            center = self.config.default_center
        if center is None:
            info = await self.map_info()
            center_data = info["map"].get("vacuum_position") or info["map"].get("charger")
            if center_data is None:
                raise AgentError("No map position is available; pass an explicit dance center")
            center = (center_data["x"], center_data["y"])
        try:
            plan = dance_plan(
                pattern,
                center,
                int(size_mm),
                int(beat_ms),
                policy=self.safety_policy(),
                real_robot=True,
            )
        except (TypeError, ValueError) as exc:
            raise AgentError(str(exc)) from exc
        for index, point in enumerate(plan["waypoints"]):
            target = (point["x"], point["y"])
            await self.goto(target)
            if index < len(plan["waypoints"]) - 1 and plan["beat_ms"] > 0:
                await asyncio.sleep(plan["beat_ms"] / 1000)
        plan.pop("waypoints", None)
        plan["device"] = _device_summary(device)
        plan["waypoints"] = plan.pop("waypoint_count")
        return plan


def _select_device(devices: list[RoborockDevice], config: AgentConfig) -> RoborockDevice | None:
    """Select by stable DUID/name; refuse ambiguous control."""
    candidates = [device for device in devices if device.v1_properties is not None]
    if config.duid:
        matches = [device for device in candidates if device.duid == config.duid]
    elif config.device_name:
        wanted = config.device_name.casefold()
        matches = [device for device in candidates if device.name.casefold() == wanted]
    else:
        matches = candidates if len(candidates) == 1 else []

    if len(matches) > 1:
        raise AgentError("Device selector matched multiple vacuums; set ROBO_DUID")
    return matches[0] if matches else None
