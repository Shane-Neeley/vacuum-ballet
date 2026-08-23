# Experiments and observations

The original implementation polled and reparsed raw V1 map bytes after every
waypoint. That made dances slow and prone to “could not reach target” timeouts.
The rewritten version uses the upstream parsed map_content trait and keeps
waypoint pacing deterministic; the robot still reports the result through its
normal status channel.

Useful experiments:

    uv run vacuum-ballet --json status
    uv run vacuum-ballet --json where
    uv run vacuum-ballet map --save logs/maps/garage.png
    uv run vacuum-ballet dance circle 200 800 --confirm

Record the returned status and map image before changing radius, centre, or
beat. A map-frame coordinate is not a room-relative coordinate, and its axes
may not match the orientation a person expects from the garage.
