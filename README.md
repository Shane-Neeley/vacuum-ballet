# RoboRock Vacuum Ballet Project 🕺🤖

Learn-by-doing control of a Roborock **S4 Max** using Python. This repo stays on the *easy, no-disassembly* path:
- Uses the `python-roborock` SDK with your Roborock app credentials.
- Sends simple **go‑to** waypoints to choreograph circles, squares, figure‑eights, and Lissajous patterns.
- Includes a tiny CLI: `vacuum-ballet` for beeps, status, cleaning and docking.

> Safety first: test in a clear 2×2 m area, start with small radii, and keep people/pets away.

## Quick start

```bash
# 1) Sync dependencies (creates a .venv)
uv sync

# 2) Create .env file with your Roborock credentials and dance defaults
# ROBO_EMAIL=your_email@example.com
# ROBO_PASSWORD=your_password_here
# DEFAULT_CENTER_X=32000
# DEFAULT_CENTER_Y=27000
# DEFAULT_RADIUS=800
# DEFAULT_BEAT_MS=600

# 3) See devices on your account (S4 Max is model roborock.vacuum.a19)
uv run vacuum-ballet devices

# 4) Check status and battery
uv run vacuum-ballet status

# 5) Start cleaning
uv run vacuum-ballet clean

# 6) Return to dock
uv run vacuum-ballet dock

# 7) Tiny motion (adjust x/y to a near point on your map, units: millimetres)
uv run vacuum-ballet goto 32500 27500

# 8) Dance! (pattern radius_mm beat_ms)
uv run vacuum-ballet dance figure8 100 600

# 9) Run tests
uv run pytest
```

## What you'll learn
- Differential-drive motion by **waypoints**
- Basic timing & beats (BPM)
- Simple Python robotics programming
- All in one clean, readable file!

## Repo layout

```
vacuum-ballet/
  pyproject.toml     # Project configuration
  requirements.txt   # Alternative dependencies
  README.md
  BUILDING.md
  src/
    main.py          # All the code in one simple file!
  tests/
    test_main.py
    test_commands.py
```

See **BUILDING.md** for deeper instructions and agent-friendly tasks.
