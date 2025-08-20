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

# install dependencies (choose one):
pip install -r requirements.txt
# OR install as editable package
pip install -e .
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

Create a `.env` file with your Roborock credentials:

```bash
ROBO_EMAIL=your_email@example.com
ROBO_PASSWORD=your_password_here
DEFAULT_CENTER_X=32000
DEFAULT_CENTER_Y=27000
DEFAULT_RADIUS=800
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## 5) Secrets & config

Create `.env` file with your Roborock credentials and dance defaults.

---

## 6) Run it

```bash
# Direct Python execution:
python src/main.py devices
python src/main.py beep
python src/main.py goto 32500 27500
python src/main.py dance figure8 100 600

# OR using the installed command:
vacuum-ballet devices
vacuum-ballet beep
vacuum-ballet goto 32500 27500
vacuum-ballet dance figure8 100 600
```

---

## 7) Tests (offline-safe)

```bash
python tests/test_main.py
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
3. Verify `python src/main.py devices` lists a device.
4. Verify `python src/main.py beep`.
5. Verify `python src/main.py goto` small move.
6. Verify `python src/main.py dance` with small radius.
7. Run unit tests.
8. Keep docs in sync.
