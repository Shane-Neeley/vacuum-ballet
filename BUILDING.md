# BUILDING.md — RoboRock Vacuum Ballet Project

A crisp, **agent-friendly build guide** for the *easy* path (no disassembly, no rooting). This sets up a clean `uv` Python project, a `src/` package, and a CLI you can drive from Cursor or a terminal.

---

## 0) What we're building

A small Python package **`roborock_dance`** that logs into your Roborock account and sends movement "dance" commands (go-to points, optional RC spins) to an **S4 Max** using the `python-roborock` SDK. You'll choreograph paths (square, circle, figure-eight, Lissajous) in **map millimeters** and pace them to beats.

> We're **not** rooting the robot here. This is the quickest way to learn and ship.

---

## 1) Prereqs (local dev)

- macOS or Linux with **Python 3.10+**
- **uv** package manager: `brew install uv` (or curl installer from Astral)
- A Roborock account (same one you use in the app)
- Your S4 Max powered on and on the same LAN

---

## 2) Project bootstrap

```bash
# create project directory
mkdir vacuum-ballet
cd vacuum-ballet

# install dependencies and create a .venv
uv sync
```

---

## 3) Repo layout (final)

```
vacuum-ballet/
  pyproject.toml     # Project configuration
  requirements.txt   # Alternative dependencies
  README.md
  BUILDING.md  ← this file
  src/
    main.py          # All the code in one simple file!
  tests/
    test_main.py
```

---

## 4) Simple setup

Create a `.env` file with your Roborock credentials and default dance centre:

```bash
ROBO_EMAIL=your_email@example.com
ROBO_PASSWORD=your_password_here
DEFAULT_CENTER_X=32000
DEFAULT_CENTER_Y=27000
DEFAULT_RADIUS=800
```
---

## 5) Secrets & config

Create `.env` file with your Roborock credentials and dance defaults.

---

## 6) Run it

```bash
# Using the installed command (selects the first S4 Max / `roborock.vacuum.a19`):
uv run vacuum-ballet devices
uv run vacuum-ballet beep
uv run vacuum-ballet goto 32500 27500
uv run vacuum-ballet dance figure8 100 600

# Or run directly with Python:
uv run python src/main.py devices
uv run python src/main.py beep
uv run python src/main.py goto 32500 27500
uv run python src/main.py dance figure8 100 600
```

---

## 7) Tests (offline-safe)

```bash
uv run pytest
```

---

## 8) Troubleshooting

- **Auth error** → check `.env` email/password; log in once in the app.
- **No devices found** → ensure you're using the **Roborock app** account.
- **No motion** → try a closer target; ensure the robot is awake (beep first).
- **Map axes flipped** → use `--rotate-deg`, `--flipx`, `--flipy`.
- **RC ignored** → your firmware may not support it; stick to `goto` dances.

---

## 9) Agent task list

1. Bootstrap repo and dependencies.
2. Create `src/main.py` with all functionality.
3. Verify `uv run vacuum-ballet devices` lists a device.
4. Verify `uv run vacuum-ballet beep`.
5. Verify `uv run vacuum-ballet goto` small move.
6. Verify `uv run vacuum-ballet dance` with small radius.
7. Run `uv run pytest`.
8. Keep docs in sync.
