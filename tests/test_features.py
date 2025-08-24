#!/usr/bin/env python3
"""Tests for auxiliary helpers like env loading, devices and image generation."""

import os
import tempfile
import unittest
from pathlib import Path
from io import StringIO
from unittest.mock import patch

# Add src to path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from main import (
    beep,
    clean,
    devices,
    generate_image,
    load_envs,
    random_dance,
    circle,
    square,
)


class TestHelpers(unittest.TestCase):
    def test_beep_prints(self):
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            beep(2)
            self.assertEqual(mock_stdout.getvalue(), "beep\nbeep\n")

    def test_devices(self):
        devs = devices()
        self.assertIsInstance(devs, list)
        self.assertTrue(all(isinstance(d, str) for d in devs))

    def test_load_envs(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text("FOO=bar\n")
            load_envs(env_file)
            self.assertEqual(os.environ.get("FOO"), "bar")
            os.environ.pop("FOO", None)

    def test_clean_returns_square(self):
        pts = clean(100)
        self.assertEqual(pts, square((0, 0), half_mm=100))

    def test_random_dance_deterministic(self):
        import random
        random.seed(0)
        pts = random_dance(50)
        self.assertEqual(pts, square((0, 0), half_mm=50))

    def test_generate_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            img_path = Path(tmp) / "path.png"
            generate_image(circle((0, 0), 10, steps=4), img_path)
            self.assertTrue(img_path.exists())

    def test_dance_logs(self):
        from main import dance, logger

        with self.assertLogs(logger, level="INFO") as log:
            dance("circle", 10, beat_ms=0)
        self.assertTrue(any("dancing circle" in m for m in log.output))


if __name__ == "__main__":
    unittest.main()
