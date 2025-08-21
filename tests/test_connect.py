#!/usr/bin/env python3
"""Connectivity test for a Roborock S4 Max.

Instructions
------------
1. Copy ``.env.example`` to ``.env`` and populate ``ROBO_EMAIL`` and
   ``ROBO_PASSWORD`` with the credentials used in the Roborock mobile app.
2. Ensure the computer running this test and the robot are on the same
   network.  The test logs in to the Roborock cloud then establishes an
   MQTT connection directly to the vacuum.
3. Verify that the device can be reached with::

       uv run vacuum-ballet devices

   The S4 Max should appear in the list.  If the connection fails, double
   check the credentials, confirm the robot is online in the mobile app and
   that no firewall is blocking the MQTT port.
4. Once connectivity works, you can "load" choreography onto the robot
   by sending commands such as::

       uv run vacuum-ballet dance square 600

   or use ``beep``/``goto`` for simpler tests.

Troubleshooting
---------------
* ``RuntimeError: ROBO_EMAIL and ROBO_PASSWORD must be set`` – the
  environment variables were not found; ensure ``.env`` is created and the
  values are exported.
* ``RuntimeError: No Roborock S4 Max found on this account`` – the account
  has no S4 Max; verify the device model or adjust ``src/main.py`` to target a
  different model.
* Connectivity errors may indicate that the robot is offline or the
  network is blocking the connection.  Confirm the robot appears online in
  the Roborock app and try again.
"""

import asyncio
import os
import sys
import unittest

# Allow importing from the src directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from main import _client  # type: ignore


class TestRoborockConnection(unittest.TestCase):
    """Attempt a real connection to the first S4 Max on the account."""

    def test_can_connect(self) -> None:
        email = os.getenv("ROBO_EMAIL")
        password = os.getenv("ROBO_PASSWORD")
        if not email or not password:
            self.skipTest("ROBO_EMAIL and ROBO_PASSWORD must be set in .env")

        async def _run() -> None:
            client = await _client()
            await client.async_disconnect()

        try:
            asyncio.run(_run())
        except Exception as exc:  # pragma: no cover - network dependent
            self.fail(f"Could not connect to Roborock: {exc}")


if __name__ == "__main__":  # pragma: no cover - manual execution
    unittest.main()
