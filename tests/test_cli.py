from __future__ import annotations

import pytest

from main import _parser
from main import _run
from roborock_agent import AgentError


def test_cli_requires_confirmation_for_real_actions() -> None:
    parser = _parser()
    args = parser.parse_args(["goto", "100", "200", "--confirm"])
    assert args.confirm is True
    assert args.x == 100 and args.y == 200


def test_cli_exposes_structured_intent_and_read_only_commands() -> None:
    parser = _parser()
    assert parser.parse_args(["status"]).cmd == "status"
    assert parser.parse_args(["intent", '{"action":"status"}']).cmd == "intent"


def test_cli_exposes_offline_playground_and_preview() -> None:
    parser = _parser()
    assert parser.parse_args(["play", "failure"]).scenario == "failure"
    preview = parser.parse_args(["preview", "circle", "300", "500"])
    assert preview.cmd == "preview"


@pytest.mark.asyncio
async def test_offline_commands_do_not_need_roborock_credentials() -> None:
    parser = _parser()
    result = await _run(parser.parse_args(["play", "failure"]))
    assert result["executed_on_robot"] is False
    result = await _run(parser.parse_args(["preview", "square", "300", "500"]))
    assert result["waypoint_count"] == 5


@pytest.mark.asyncio
async def test_invalid_real_dance_is_rejected_before_login() -> None:
    parser = _parser()
    with pytest.raises(AgentError, match="play too_fast"):
        await _run(parser.parse_args(["dance", "circle", "300", "0", "--confirm"]))
