# Technical model

Roborock does not provide this project with a public motor-control API. The
upstream python-roborock library reverse-engineers the account/cloud and
device protocols. Current upstream v7 uses a DeviceManager with optional
capability sets; standard vacuums expose device.v1_properties.

The important flow is:

1. RoborockApiClient.pass_login() obtains UserData.
2. create_device_manager(UserParams(...)) discovers and connects devices.
3. device.v1_properties.status.refresh() reads status.
4. device.v1_properties.map_content.refresh() fetches and parses map data.
5. device.v1_properties.command.send(...) sends an explicit V1 command.

Movement is high-level app_goto_target([x, y]), equivalent to the app's Pin n
Go feature. The robot's own localization, planning, and obstacle avoidance
remain in charge. local_connected reports whether the adaptive transport
currently has a local connection; cloud MQTT remains an available fallback.

The agent layer rejects ambiguous device selection and requires confirmation
before writes. It does not expose arbitrary raw commands to the CLI, although
the Python send() method is available for future, reviewed capabilities.

## Safety and agent boundary

The code has three distinct paths:

```text
natural language -> narrow intent parser -> reviewable plan -> optional confirmation -> device trait
                                           \-> playground (always offline)
```

`src/safety.py` builds the same integer waypoint plan used by previews and
real execution. Physical dances currently require a radius of 200–1200 mm, a
beat of at least 250 ms, and no more than 32 waypoints. Invalid requests are
rejected rather than silently clamped. The robot still owns navigation and
obstacle avoidance, so a human should preview the map position and clear the
garage before confirming a dance.

`src/playground.py` is the home for theatrical behavior: failure, confusion,
victory, and “too fast.” These routines return deterministic event records and
explicitly report `executed_on_robot: false`. This keeps a child’s joke from
turning into unsafe speed or raw motor control.

## Rooms and current upstream examples

The `rooms` command refreshes `device.v1_properties.rooms`, exposing the
upstream `segment_id`, `iot_id`, and optional room name. `clean-rooms` sends
the reviewed V1 `app_segment_clean` payload with a bounded segment count and
repeat count. Segment IDs are discovered from the robot; the agent does not
infer them from words such as “kitchen.”

The implementation follows the current upstream library shape and examples:

- [python-roborock README](https://github.com/Python-roborock/python-roborock)
  documents `RoborockApiClient`, `UserParams`, `create_device_manager`, and
  V1 traits.
- [upstream Python example](https://github.com/Python-roborock/python-roborock/blob/main/examples/example.py)
  demonstrates discovery, status refresh, and command sending.
- [upstream V1 command reference](https://github.com/Python-roborock/python-roborock/blob/main/docs/V1_API_COMMANDS.md)
  records the segment-clean payload and other app commands.
