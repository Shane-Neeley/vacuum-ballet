# Building and operating

The project uses uv and Python 3.12+.

    uv sync
    cp .env.example .env
    uv run pytest
    uv run vacuum-ballet --help

The runtime boundary is src/roborock_agent.py. It authenticates through
RoborockApiClient, creates the upstream DeviceManager, selects a V1 vacuum by
DUID/name, and exposes status, map, rooms, cleaning, dock, Pin n Go, and
waypoint operations. src/main.py is only the CLI/intent adapter;
src/patterns.py, src/safety.py, src/intents.py, and src/playground.py contain
no network or device code.

For a first live check, use vacuum-ballet devices, then status and where. Do
not start with movement: map coordinates are robot-map millimetres and need to
be verified against the saved map image and the physical garage. The live test
remains skipped unless explicitly enabled with `RUN_ROBOROCK_LIVE_TEST=1` and
exported credentials; normal `uv run pytest` never contacts Roborock.

For family experiments, start with `preview`, `play`, or plan-only `ask`.
Only an intentional `--execute --confirm` crosses from an ask plan into a
physical action.
