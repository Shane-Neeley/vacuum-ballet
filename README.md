# Vacuum Ballet

Minimal helpers to choreograph a vacuum robot using simple waypoints.
The project now focuses on three easy dance patterns:

- **circle** – move in a circle of a given radius
- **square** – trace a square and return to the start
- **spin** – a tight circle that makes the robot appear to spin in place

`src/main.py` contains the geometry helpers and a tiny CLI which prints the
waypoints for a selected pattern. The code is intentionally small and free of
robot‑specific dependencies so it can be studied or extended easily.

Additional helpers are provided for common tasks:

- load environment variables from a ``.env`` file
- list available devices (placeholder implementation)
- emit simple ``beep`` messages
- generate random or cleaning patterns
- save a plotted path to an image file

## Quick start

```bash
# Run a circle with 400 mm radius, pausing 500 ms between points
uv run python src/main.py dance circle 400 500

# Trace a square with half-size 200 mm using default beat (500 ms)
uv run python src/main.py dance square 200
```

## Development

```bash
# Run tests
uv run pytest
```

## Repo layout

```
vacuum-ballet/
  README.md
  src/
    main.py          # geometry and CLI
  tests/
    test_cli.py
    test_dance.py
    test_features.py
    test_main.py
```

Enjoy experimenting with simple dance moves!
