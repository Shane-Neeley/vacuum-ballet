# Vacuum Ballet

[![Tests](https://github.com/Shane-Neeley/vacuum-ballet/actions/workflows/test.yml/badge.svg)](https://github.com/Shane-Neeley/vacuum-ballet/actions/workflows/test.yml)

An agent-first control layer for Roborock vacuums: preview a plan, let a
person approve physical actions, and give kids a robot that can perform safe,
pretend comedy without touching the real device.

Vacuum Ballet is for people who want more than a dashboard, but less than a
raw reverse-engineering project. It turns the current `python-roborock` device
API into a small, inspectable CLI and JSON interface for agents, experiments,
and playful household automation.

## See it in 30 seconds

The first commands need no account and do not open a device connection:

```bash
uv sync
uv run vacuum-ballet play victory
uv run vacuum-ballet --json ask "make it go too fast"
uv run vacuum-ballet preview figure8 300 500
```

Then ask for a physical plan without executing it:

```bash
uv run vacuum-ballet --json ask "do a big square dance 700 mm 600 ms"
```

The output is JSON that an agent or a parent can review. Physical execution
requires both explicit opt-ins:

```bash
uv run vacuum-ballet ask "do a figure eight dance 300 mm 700 ms" --execute --confirm
```

The funny routines—`failure`, `too_fast`, `confused`, and `victory`—are
simulator-only. They never turn a joke into a zero-delay or motor-level
command.

## Why this exists

Roborock projects tend to optimize for one of three jobs:

| Approach | Excellent for | Where Vacuum Ballet fits |
| --- | --- | --- |
| [`python-roborock`](https://github.com/Python-roborock/python-roborock) | Keeping up with device protocols and exposing capabilities | A focused coordinator built on top of its current `DeviceManager` and V1 traits |
| [Home Assistant’s Roborock integration](https://www.home-assistant.io/integrations/roborock) | Dashboards, sensors, and household automations | A standalone terminal/JSON tool that is easy to call from an agent, script, or child-friendly interface |
| One-off scripts | Quickly sending one command to one vacuum | Explicit device selection, cached auth, previews, tests, confirmation gates, and a simulator |

The project’s wedge is the boundary between “the agent has an idea” and “the
robot moves”:

- Agents get reviewable JSON plans instead of an opaque command call.
- Humans confirm every physical write.
- Geometry is pure, deterministic, and previewable offline.
- Kid-facing comedy stays in a network-free playground.
- Room cleaning uses discovered map segment IDs instead of guessing names.
- The transport layer stays replaceable as the upstream API evolves.

This is intentionally not trying to replace Home Assistant or
`python-roborock`; it makes their useful capabilities easier to compose into
agentic, experimental, and playful workflows.

## Who gets value from it

- **Agent builders** get a small JSON contract with a visible plan/execute
  boundary instead of embedding Roborock protocol details in a prompt.
- **Families** get safe “tell the robot to do something funny” interactions
  when they expose the plan-only `ask` interface instead of raw physical
  subcommands.
- **Roborock owners** get useful CLI operations—status, maps, rooms, cleaning,
  dock, locate, and Pin n Go—without standing up a home-automation platform.
- **Python developers** get pure geometry, mocked device traits, and a current
  upstream adapter that can be extended one capability at a time.

## Connect a real Roborock

<details>
<summary>Show setup and authentication</summary>

```bash
cp .env.example .env
# edit .env with ROBO_EMAIL and ROBO_PASSWORD
uv run vacuum-ballet login
uv run vacuum-ballet devices
```

If the account has multiple vacuums, set `ROBO_DUID` or the exact
`ROBO_DEVICE_NAME` reported by `devices`. The session cache lives under
`~/.cache/vacuum-ballet/`, outside the repository, and is written with private
permissions where supported.

Roborock may require an email verification code. `login` prompts locally and
uses the code once. `ROBO_CODE` is supported for one login, but should be
removed afterward. If Roborock reports “too many codes,” stop retrying until
the cooldown passes; repeated requests can invalidate the code you already
have.

</details>

## Commands by risk level

### Offline first

```bash
uv run vacuum-ballet preview circle 300 500
uv run vacuum-ballet play failure
uv run vacuum-ballet --json ask "do a figure eight dance 300 mm 700 ms"
```

### Read-only device operations

After authentication, inspect the device before sending anything:

```bash
uv run vacuum-ballet status
uv run vacuum-ballet where
uv run vacuum-ballet map --save logs/maps/garage.png
uv run vacuum-ballet --json rooms
```

### Physical actions

Every physical action requires `--confirm`:

```bash
uv run vacuum-ballet clean --confirm
uv run vacuum-ballet dock --confirm
uv run vacuum-ballet pause --confirm
uv run vacuum-ballet stop --confirm
uv run vacuum-ballet goto X_MM Y_MM --confirm
uv run vacuum-ballet dance circle 300 700 --confirm
uv run vacuum-ballet clean-rooms 3 7 --repeat 1 --confirm
```

Dance plans are bounded to 200–1200 mm, at least 250 ms between real-vacuum
waypoints, and at most 32 waypoints. The robot still owns localization,
navigation, and obstacle avoidance; clear the garage and verify the map before
approving movement.

### Structured agent interface

Read-only, preview, and simulator intents are JSON-friendly:

```bash
uv run vacuum-ballet --json intent '{"action":"status"}'
uv run vacuum-ballet --json intent '{"action":"play","scenario":"failure"}'
uv run vacuum-ballet --json intent '{"action":"preview","pattern":"square","size":300,"beat_ms":500}'
```

Physical JSON intents must include `"confirm": true`:

```bash
uv run vacuum-ballet --json intent '{"action":"goto","x":32000,"y":27000,"confirm":true}'
```

## Architecture

```text
ask / intent / CLI
        |
        v
reviewable plan -----> playground (offline comedy)
        |
        +-- human confirmation --> RoborockAgent --> python-roborock V1 traits
```

The device layer uses the current upstream flow: `RoborockApiClient` for
login, `UserParams` and `DeviceManager` for discovery, and
`device.v1_properties` for status, maps, rooms, and commands. Movement uses
the high-level `app_goto_target` Pin n Go operation; this project does not
drive motors directly.

## Documentation and examples

- [Kid and agent command examples](examples/kid_commands.md)
- [Technical model and safety boundary](docs/TECH.md)
- [Building and operating](docs/BUILDING.md)
- [Learning path](docs/LEARNING.md)
- [Experiments and map-coordinate notes](docs/EXPERIMENTS.md)
- [Current upstream Python example](https://github.com/Python-roborock/python-roborock/blob/main/examples/example.py)
- [Current upstream V1 command reference](https://github.com/Python-roborock/python-roborock/blob/main/docs/V1_API_COMMANDS.md)

## Development

```bash
uv sync
uv run pytest
uv run vacuum-ballet --help
```

The live connection test is deliberately opt-in. Set
`RUN_ROBOROCK_LIVE_TEST=1` alongside exported `ROBO_EMAIL` and
`ROBO_PASSWORD` to permit it; normal test runs never contact Roborock.

The implementation is organized so the public surface stays small:

```text
src/main.py           CLI, confirmation gates, structured intents
src/intents.py        Narrow kid-language parser and reviewable plans
src/playground.py     Network-free comedy/simulator routines
src/roborock_agent.py Login, selection, capabilities, and device actions
src/patterns.py       Pure waypoint generators
src/safety.py         Physical limits and offline dance planning
tests/                Offline behavior and mocked trait tests
examples/             Copyable family and agent workflows
```
