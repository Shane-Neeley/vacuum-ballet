# TECH.md — Roborock S4 Max: Sensors & Effectors

A quick, practical map of **what hardware the S4 Max has** and **how you can drive it** from our Python project. Where useful, this doc also links the parts to SDK commands you can call.

---

## Hardware overview (what's on the robot)

### Sensor suite

| Sensor                                              | What it does                                                                      | Notes you can rely on                                                                                                     |
| --------------------------------------------------- | --------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| **Laser Distance Sensor (LDS / LiDAR)**             | Spins in the turret to measure ranges for mapping & navigation (SLAM).            | Listed as "Laser distance sensor" in the official manual's labeled diagram.                                               |
| **Cliff sensors (downward IR)**                     | Detect stairs/ledges to prevent falls.                                            | Manual shows "Cliff sensor"; the S4 Max docs (and mirrored manual pages) specify **four** cliff sensors on the underside. |
| **Wall sensor (side IR)**                           | Tracks along walls and edges.                                                     | Labeled "Wall sensor" in the manual diagram.                                                                              |
| **Bumper (front)**                                  | Physical contact switch to detect collisions.                                     | Labeled "Bumper" in the manual diagram.                                                                                   |
| **Vertical bumper**                                 | Prevents getting trapped under low furniture by sensing contact on the top/front. | Roborock's product page calls out a *vertical bumper* as part of the Sensient™ array.                                     |
| **Recharge/dock sensor (IR)**                       | Sees the dock's locator beacon to return home.                                    | Manual labels **Recharge sensor** on the robot and **Locator beacon** on the dock.                                        |
| **Jam/brush sensor**                                | Detects a jammed main brush to protect the motor/gearbox.                         | Mentioned on Roborock's S4 Max page.                                                                                      |
| **System indicators (Wi-Fi / power LEDs, speaker)** | Status feedback & voice/beeps; useful for "find me" beeps in our dances.          | Wi-Fi indicator states and the Speaker are shown in the manual.                                                           |

> The S4 Max is a LiDAR SLAM robot: you **give it coordinates**; it handles localization, obstacle detection, and pathing on-board.

### Effectors (things you can command)

| Effector                      | What it physically is                                | How you'll use it                                                                                                                                 |
| ----------------------------- | ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Drive motors (L/R wheels)** | Two independent DC gearmotors drive the main wheels. | Send **go-to (x, y)** targets; robot plans motion to reach them. (We avoid raw motor commands.)                                                   |
| **Vacuum fan**                | High-speed blower for suction.                       | Adjustable by "mode" (Quiet / Balanced / Strong / MAX) and via **custom** power in SDKs. Manual exposes the modes; SDK exposes `set_custom_mode`. |
| **Main brush motor**          | Spins the center brush to sweep debris.              | Tied to cleaning/spot tasks; indirectly driven when cleaning or moving.                                                                           |
| **Side brush motor**          | Edge sweeping.                                       | As above; used during cleaning and edge-following.                                                                                                |
| **Speaker**                   | Beeper/voice prompts.                                | We use **find-me**/test volume for rhythmic "beats."                                                                                              |

---

## App/firmware behaviors you can lean on

* **Pin n Go / go-to-point:** The official app has "Pin n Go" (tap a map location and it drives there). That's exactly the capability we script via `app_goto_target`.
* **Cleaning modes & Carpet Boost:** The app exposes **Quiet / Balanced / Strong / MAX**, and "Carpet Boost" automatically increases suction on carpeted areas.

---

## Programming hooks (SDK commands that map to the hardware)

These are the core calls you'll reach for from Python (via `python-roborock`) and what they touch on the robot:

* **Go to coordinate (drive motors):** `app_goto_target [x_mm, y_mm]` — this is our dance workhorse.
* **Return to dock (drive + dock sensor):** `app_charge` — heads back and lines up with the dock beacon.
* **Remote control (short velocity bursts):** `app_rc_start/move/stop/end` — optional, firmware-dependent; nice for tiny spins between waypoints.
* **Beep/locate (speaker):** `find_me` or `test_sound_volume` — useful for downbeat cues.
* **Fan power (vacuum blower):** `set_custom_mode` — set a percentage/level beyond the four preset modes (exact maps vary by model).

> Networking tip for local control (HA/integrations): make sure your controller can reach the vacuum on **TCP 58867** on your LAN.

---

## Practical notes you'll feel when dancing

* **Coordinates are in millimeters, in the robot's map frame.** If directions feel "rotated" vs. your room, use our CLI's `--rotate-deg` / `--flipx` / `--flipy` to align.
* **Latency & pacing:** The robot's planner queues work; send waypoints at a rhythm it can satisfy. Our default approach is beat-paced (BPM), and you can upgrade to **near-arrival gating** for smoother motion.
* **Use effects tastefully:** Beeps (speaker) on downbeats and small fan ramps (blower) make routines feel alive without disrupting motion.

---

## Clean, safe API surface (tying it back to our repo)

* `rd goto X Y` → **drive** to a point (uses `app_goto_target`).
* `rd dance` → streams a **series of waypoints** (circle/figure-eight/Lissajous), with optional rotate/flip transforms so frames match reality.
* `rd beep` → **find-me** beep (speaker).
* `rd rc-spin` → tiny flourish via **remote control** (if your firmware exposes `app_rc_*`).
* Fan power tracks (optional): wire `set_custom_mode` for crescendos; presets remain available in the app (Quiet/Balanced/Strong/MAX).

---

## Source references

* **Official S4 Max user manual** (labelled diagram shows sensors; app features list includes Pin n Go, modes, Carpet Boost, dock beacon).
* **Python-Roborock docs** (command list: `app_goto_target`, `app_charge`, `app_rc_*`, `find_me`, `set_custom_mode`).
* **Roborock S4 Max page** (Sensient™ array: cliff sensors, vertical bumper, jam sensor).
* **Home Assistant Roborock integration** (local API port 58867).

---

### TL;DR

* **Sensors**: LiDAR + cliff + wall + bumper + dock IR (+ jam detect).
* **Effectors**: drive motors, vacuum fan, main/side brushes, speaker.
* **You control**: go-to waypoints, dock, optional RC bursts, beeps, and fan levels.
  That's everything you need to reason about the robot like a mobile base—and choreograph it with confidence.
