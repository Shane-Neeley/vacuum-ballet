from __future__ import annotations

import pytest

from intents import intent_plan, parse_kid_request
from playground import run_playground
from safety import SafetyPolicy, dance_plan


def test_kid_parser_routes_comedy_to_the_playground() -> None:
    intent = parse_kid_request("make it go too fast")
    assert intent.action == "play"
    assert intent.args == {"scenario": "too_fast"}
    assert intent.simulator_only is True
    assert run_playground("too_fast")["executed_on_robot"] is False


def test_kid_parser_builds_bounded_dance_plan_without_execution() -> None:
    intent = parse_kid_request("do a big figure eight dance 700 mm 600 ms")
    assert intent.action == "dance"
    assert intent.args == {"pattern": "figure8", "size": 700, "beat_ms": 600}
    plan = intent_plan(intent)
    assert plan["next_step"] == "add --execute --confirm to perform a physical action"


def test_real_policy_rejects_too_fast_but_preview_allows_it() -> None:
    with pytest.raises(ValueError, match="play too_fast"):
        dance_plan("circle", (0, 0), 300, 0, real_robot=True)

    preview = dance_plan("circle", (0, 0), 300, 0)
    assert preview["mode"] == "preview"
    assert preview["waypoint_count"] == 16


def test_policy_rejects_large_or_long_physical_plans() -> None:
    policy = SafetyPolicy(max_waypoints=4)
    with pytest.raises(ValueError, match="waypoints"):
        dance_plan("circle", (0, 0), 300, 500, policy=policy, real_robot=True)
    with pytest.raises(ValueError, match="segments"):
        policy.validate_segments(list(range(9)), 1)
