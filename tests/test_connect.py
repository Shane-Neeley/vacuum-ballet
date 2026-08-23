from __future__ import annotations

import os

import pytest

from roborock_agent import AgentConfig, RoborockAgent


@pytest.mark.asyncio
async def test_live_connection_is_opt_in() -> None:
    if os.getenv("RUN_ROBOROCK_LIVE_TEST") != "1":
        pytest.skip("set RUN_ROBOROCK_LIVE_TEST=1 to allow a live Roborock check")
    if not (os.getenv("ROBO_EMAIL") and os.getenv("ROBO_PASSWORD")):
        pytest.skip("ROBO_EMAIL and ROBO_PASSWORD must be exported for the live check")
    async with await RoborockAgent.connect(AgentConfig.from_env(), require_device=False) as agent:
        devices = await agent.devices()
    assert devices
