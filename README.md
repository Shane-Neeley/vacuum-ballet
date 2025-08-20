# RoboRock Vacuum Ballet Project 🕺🤖

Learn-by-doing control of a Roborock **S4 Max** using Python. This repo stays on the *easy, no-disassembly* path:
- Uses the `python-roborock` SDK with your Roborock app credentials.
- Sends simple **go‑to** waypoints to choreograph circles, squares, figure‑eights, and Lissajous patterns.
- Includes a tiny CLI: `rd`.

> Safety first: test in a clear 2×2 m area, start with small radii, and keep people/pets away.

## Quick start

```bash
# 1) Install dependencies (choose one):
pip install -r requirements.txt
# OR
pip install -e .

# 2) Create .env file with your Roborock credentials
# ROBO_EMAIL=your_email@example.com
# ROBO_PASSWORD=your_password_here

# 3) See devices on your account
python src/main.py devices
# OR
vacuum-ballet devices

# 4) Safe beep test
python src/main.py beep
# OR
vacuum-ballet beep

# 5) Tiny motion (adjust x/y to a near point on your map, units: millimeters)
python src/main.py goto 32500 27500
# OR
vacuum-ballet goto 32500 27500

# 6) Dance!
python src/main.py dance figure8 100 600
# OR
vacuum-ballet dance figure8 100 600
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
```

See **BUILDING.md** for deeper instructions and agent-friendly tasks.