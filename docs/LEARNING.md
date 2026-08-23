# Learning path

The useful mental model is “intent -> capability -> robot planner”:

- An agent chooses an explicit intent such as status, dock, or goto.
- RoborockAgent translates it to a supported V1 trait operation.
- The vacuum performs navigation using its own map and safety systems.

Start with read-only commands:

    uv run vacuum-ballet devices
    uv run vacuum-ballet status
    uv run vacuum-ballet where
    uv run vacuum-ballet map --save logs/maps/garage.png

Then preview waypoint geometry in tests or import src/patterns.py. Only after
checking the map and physical clearance should a small goto or dance be run
with --confirm. Keep the first target close, keep people and pets clear, and
use dock --confirm to stop a session.

For agent and kid-facing development, use the offline boundary first:

    uv run vacuum-ballet preview figure8 300 500
    uv run vacuum-ballet play failure
    uv run vacuum-ballet ask "make it go too fast"

The parser is intentionally narrow. It produces a plan for real requests and
routes comedy to the playground, where fake failure and speed never become
physical commands.
