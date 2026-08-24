from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from roborock import RoborockCommand
from roborock.devices.cache import CacheData

from roborock_agent import AgentConfig, AgentError, RoborockAgent, SafeFileCache, _code_login, _select_device


def fake_device(name: str = "Garage Roborock", duid: str = "duid-1") -> SimpleNamespace:
    status = SimpleNamespace(
        refresh=AsyncMock(),
        as_dict=lambda: {"battery": 88},
        state_name="charging",
        error_code_name=None,
        current_map=0,
    )
    map_data = SimpleNamespace(
        charger=SimpleNamespace(x=1000, y=2000),
        vacuum_position=SimpleNamespace(x=1100, y=2100),
    )
    props = SimpleNamespace(
        status=status,
        map_content=SimpleNamespace(
            refresh=AsyncMock(),
            map_data=map_data,
            image_content=b"png",
        ),
        command=SimpleNamespace(send=AsyncMock(return_value={"ok": True})),
        rooms=SimpleNamespace(
            refresh=AsyncMock(),
            rooms=[SimpleNamespace(segment_id=3, iot_id="kitchen", raw_name="Kitchen")],
        ),
    )
    return SimpleNamespace(
        name=name,
        duid=duid,
        product=SimpleNamespace(model="roborock.vacuum.a19"),
        device_info=SimpleNamespace(pv="1.0"),
        is_connected=True,
        is_local_connected=False,
        v1_properties=props,
    )


def test_select_device_requires_explicit_selection_when_ambiguous() -> None:
    devices = [fake_device("Garage"), fake_device("House", "duid-2")]
    assert _select_device(devices, AgentConfig(device_name="Garage")) is devices[0]
    assert _select_device(devices, AgentConfig()) is None


@pytest.mark.asyncio
async def test_status_and_map_are_read_only_and_structured(tmp_path) -> None:
    device = fake_device()
    manager = SimpleNamespace(get_devices=AsyncMock(return_value=[device]))
    agent = RoborockAgent(manager, SimpleNamespace(), device)

    result = await agent.status()
    assert result["status"]["battery"] == 88
    device.v1_properties.status.refresh.assert_awaited_once()

    map_result = await agent.map_info(tmp_path / "map.png")
    assert map_result["map"]["charger"] == {"x": 1000, "y": 2000}
    assert (tmp_path / "map.png").read_bytes() == b"png"


@pytest.mark.asyncio
async def test_actions_use_latest_command_trait() -> None:
    device = fake_device()
    agent = RoborockAgent(SimpleNamespace(), SimpleNamespace(), device)

    await agent.clean()
    await agent.goto((123, 456))

    send = device.v1_properties.command.send
    assert send.await_args_list[0].args == (RoborockCommand.APP_START, None)
    assert send.await_args_list[1].args == (RoborockCommand.APP_GOTO_TARGET, [123, 456])


@pytest.mark.asyncio
async def test_rooms_and_segment_clean_use_bounded_upstream_payload() -> None:
    device = fake_device()
    agent = RoborockAgent(SimpleNamespace(), SimpleNamespace(), device)

    assert await agent.rooms() == [{"segment_id": 3, "iot_id": "kitchen", "name": "Kitchen"}]
    await agent.clean_rooms([3], repeat=2)

    send = device.v1_properties.command.send
    assert send.await_args_list[-1].args == (
        RoborockCommand.APP_SEGMENT_CLEAN,
        [{"segments": [3], "repeat": 2}],
    )


@pytest.mark.asyncio
async def test_dance_safety_rejects_zero_delay_before_any_command() -> None:
    device = fake_device()
    agent = RoborockAgent(SimpleNamespace(), SimpleNamespace(), device)

    with pytest.raises(AgentError, match="play too_fast"):
        await agent.dance("circle", 300, 0, center=(1000, 2000))
    device.v1_properties.command.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_dance_waits_for_final_target_to_settle() -> None:
    device = fake_device()
    device.v1_properties.status.state_name = "going_to_target"
    refresh_count = 0

    async def refresh() -> None:
        nonlocal refresh_count
        refresh_count += 1
        if refresh_count % 2 == 0:
            device.v1_properties.status.state_name = "idle"
        else:
            device.v1_properties.status.state_name = "going_to_target"

    device.v1_properties.status.refresh = AsyncMock(side_effect=refresh)
    agent = RoborockAgent(SimpleNamespace(), SimpleNamespace(), device)

    with patch("roborock_agent.asyncio.sleep", new=AsyncMock()):
        result = await agent.dance("square", 200, 250, center=(1000, 2000))

    assert result["settled_state"] == "idle"
    assert refresh_count == 10
    assert device.v1_properties.command.send.await_count == 5


@pytest.mark.asyncio
async def test_remote_dance_stops_and_ends_manual_control() -> None:
    device = fake_device()
    device.v1_properties.status.state_name = "manual_mode"
    agent = RoborockAgent(SimpleNamespace(), SimpleNamespace(), device)

    with patch("roborock_agent.asyncio.sleep", new=AsyncMock()):
        result = await agent.remote_dance("crazy")

    send = device.v1_properties.command.send
    assert result["mode"] == "remote_control"
    assert result["pulse_count"] == 8
    assert send.await_args_list[0].args == (RoborockCommand.APP_RC_START, None)
    assert send.await_args_list[1].args[0] == RoborockCommand.APP_RC_MOVE
    assert send.await_args_list[1].args[1][0]["seqnum"] == 1
    assert send.await_args_list[-2].args == (RoborockCommand.APP_RC_STOP, None)
    assert send.await_args_list[-1].args == (RoborockCommand.APP_RC_END, None)


@pytest.mark.asyncio
async def test_missing_credentials_fail_before_network(tmp_path) -> None:
    with pytest.raises(AgentError, match="ROBO_EMAIL"):
        await RoborockAgent.connect(AgentConfig(cache_dir=tmp_path))


@pytest.mark.asyncio
async def test_code_login_requests_code_and_uses_it_once() -> None:
    api = SimpleNamespace(
        request_code_v4=AsyncMock(),
        code_login_v4=AsyncMock(return_value="user-data"),
    )
    with patch("builtins.input", return_value="654321"):
        result = await _code_login(api)

    assert result == "user-data"
    api.request_code_v4.assert_awaited_once()
    api.code_login_v4.assert_awaited_once_with("654321")


@pytest.mark.asyncio
async def test_configured_code_does_not_request_a_replacement() -> None:
    api = SimpleNamespace(
        request_code_v4=AsyncMock(),
        code_login_v4=AsyncMock(return_value="user-data"),
    )
    result = await _code_login(api, "654321")

    assert result == "user-data"
    api.request_code_v4.assert_not_awaited()
    api.code_login_v4.assert_awaited_once_with("654321")


@pytest.mark.asyncio
async def test_device_cache_survives_unserializable_runtime_state(tmp_path) -> None:
    cache_path = tmp_path / "device-cache.pkl"
    cache = SafeFileCache(cache_path)
    cache_data = CacheData(trait_data={"runtime_callback": lambda: None})
    await cache.set(cache_data)

    await cache.flush()

    recovered = SafeFileCache(cache_path)
    assert isinstance(await recovered.get(), CacheData)
