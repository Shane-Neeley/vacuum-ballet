# LEARNING.md — Learn Robotics by Dancing Your RoboRock S4 Max

This repo is a **learn-by-doing** path: you'll program a real mobile robot (your S4 Max) using Python, build intuition for **coordinates, timing, and motion**, and keep everything **simple and safe**. We stay on the *no-disassembly* path and use the official account-based control (via the `python-roborock` SDK).

> TL;DR: You generate waypoints (in **map millimeters**), pace them to beats, and the robot's own planner/localization handles the low-level magic.

---

## 1) Why learn with a vacuum robot?

* It's already a **differential-drive robot** with encoders, IMU, LIDAR, and a map.
* You get the *real* robotics experiences—frames, transforms, waypoint vs. velocity control—**without** building a drivetrain or writing motor drivers.
* The skills transfer: the same ideas power AMRs, warehouse bots, and future home robots.

---

## 2) Mental model (keep this in your head)

* **You don't micromanage motors.** You ask: "go to (x, y)" or "spin a bit," and the onboard planner/localization executes.
* **Coordinates live in the robot's map frame**, measured in millimeters. The map might be rotated/flipped vs. your room; use helpers to align.
* **Timing matters.** If you send points too fast, the planner may queue or ignore; if too slow, the motion looks choppy. Our CLI exposes `--bpm` to tune pacing.

---

## 3) A tiny curriculum (2 weeks)

Each block is \~30–45 minutes. Run commands with `python src/main.py ...`.

**Day 1–2: Liveness + coordinates**

* `python src/main.py devices` → see your robot.
* `python src/main.py beep` → wake and confirm connectivity.
* `python src/main.py goto <x> <y>` → tiny move (0.3–0.5 m). Verify **axes**; if needed, adjust center coordinates in `.env` later.

**Day 3–4: First choreography**

* `python src/main.py dance figure8 100 600`
* Try `circle`, `square`, `liss`. Change BPM and radius to see the effect.

**Day 5–6: Multi-channel effects**

* Add **beeps on downbeats** and **fan sweeps** (already wired in `client.py`).
* Learn to think in **tracks**: motion, sound, airflow.

**Day 7–8: Status-paced motion (upgrade)**

* Replace fixed `sleep()` with **near-arrival gating** (advance when within N mm of the target). This yields smoother motion under Wi-Fi jitter.

**Day 9–10: Visualization**

* Write a small `visualize.py` that plots waypoints (and optionally a map screenshot). Preview before you roll to catch orientation mistakes.

**Day 11–14: Your routine**

* Compose a 30–60s dance that combines shapes, beeps, and fan sweeps. Save the parameters in a JSON/YAML "preset."

---

## 4) Python patterns that make this solid

**Wake-before-work**
Always "nudge" the robot (beep/wake) before your first motion:

```python
dev.wake()
time.sleep(0.5)
```

**Near-arrival gating (pseudo-code)**

```python
TARGET_MM = 150  # when considered close enough
for x, y in path:
    dev.goto(x, y)
    while True:
        # Pseudocode: your SDK call may differ; poll until within threshold.
        st = dev.device_status()     # e.g., pose or distance remaining
        if st.distance_to_goal_mm <= TARGET_MM:
            break
        time.sleep(0.2)
```

*Why:* smoother motion than fixed beats; resilient to network hiccups.

**Bounded retries**

```python
for attempt in range(2):
    try:
        dev.goto(x, y)
        break
    except Exception:
        time.sleep(0.5)
else:
    raise RuntimeError("Failed to send command after retries")
```

**Config over constants**
Use `.env` for credentials and defaults (center/radius) so you tweak without changing code.

**Keep geometry testable**
All math lives in `patterns.py` with small unit tests in `tests/`—you can verify shapes without moving the robot.

---

## 5) Coordinates, frames, and orientation

* Start with two nearby test points. If the robot moves "the wrong way," your **map axes** are rotated or flipped relative to your expectation.
* Use `--rotate-deg`, `--flipx`, `--flipy` (CLI) or `map_tools.rotate/flip` in code to align. Once aligned, save those as defaults in `.env`.

---

## 6) Visualization ideas (optional but powerful)

* Plot **planned** points (Matplotlib/Plotly). Draw arrows to show facing (even if you don't directly command heading).
* Overlay a **map screenshot**: estimate scale/rotation with two known points; then draw the planned path over it.
* Record timestamps when you send each waypoint; draw a **timeline** under the plot to debug pacing decisions.

---

## 7) Safety checklist (every time)

* Clear a \~2×2 m area (no cords, rugs, pets, or curious toes).
* Start small (**radius ≤ 800 mm**, **80–110 BPM**).
* Prefer waypoints; try RC spins only for brief effects and only if your firmware supports it.
* Keep the battery charged; low battery may refuse motion.

---

## 8) Where this fits in the bigger picture

* You're already learning **frames & transforms**, **planning** (as waypoints), and **timing/jitter**—the same ideas behind larger AMRs.
* As robot APIs open up, programming keeps moving **up the stack** (describe behaviors, not motor steps). Your habit of composing routines from primitives will carry over to more capable platforms.
* If you ever want fully local control later, the community route is a rooted firmware with a local UI and MQTT. This repo doesn't require that; it's here to teach fundamentals first.

---

## 9) Stretch tasks

* **Pose logger & replay**: save `(t, x, y)` during a dance; plot actual vs. planned.
* **Interactive editor**: tiny web UI (FastAPI/HTMX or React) with sliders for radius/BPM and a "Preview → Execute" button.
* **Dance DSL**: define routines in YAML/JSON and compile to waypoints.
* **Metronome channel**: beep only on downbeats and pulse fan on upbeats.

---

## 10) What to read next (short list)

These are *quick, practical* resources to deepen the exact skills you're using here:

* Differential-drive basics (any short intro): look for "v/ω control" and "unicycle model".
* A beginner's PWM primer and a DC motor/servo overview (to understand why timing and fan speed behave as they do).
* Your SDK's command surface (goto, sound/volume, fan/custom modes, segment/zone). Browsing the code examples helps you see what's available.

---

## 11) FAQ

**Why millimeters?** The internal map uses mm; it's standard for vacuums.
**Do I need the vendor app?** Yes to authenticate and enumerate devices. After that you can operate locally on your LAN.
**Can I draw big shapes across the garage?** Yes—start small, verify orientation, then scale up. Use near-arrival gating for smoothness.
**What if RC moves don't work?** Some firmwares don't expose RC; stick to waypoints (they work great for choreography).

---

## 12) Checklist for mastery

* [ ] I can list devices, beep the robot, and send a safe waypoint.
* [ ] I ran **three** dances (different shapes) with small radii.
* [ ] I calibrated orientation (rotate/flip) so preview ≈ reality.
* [ ] I implemented near-arrival gating.
* [ ] I plotted my planned path before executing.
* [ ] I saved a favorite routine as a preset (JSON/YAML).

Ship small, iterate daily—each dance step is a robotics lesson in disguise.
