#!/usr/bin/env python3
"""Tests for the ``dance`` helper."""

import os
import sys
from io import StringIO
from unittest import TestCase
from unittest.mock import patch

# Ensure src is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from main import dance, circle


class TestDance(TestCase):
    def test_invalid_pattern_raises(self):
        with self.assertRaises(ValueError):
            dance("triangle", 100, beat_ms=0)

    def test_prints_and_sleeps(self):
        with patch("sys.stdout", new_callable=StringIO) as stdout:
            with patch("time.sleep") as mock_sleep:
                pts = dance("circle", 50, beat_ms=100)
        # ensure output printed for each point
        lines = stdout.getvalue().strip().splitlines()
        expected = [f"goto {x} {y}" for x, y in circle((0, 0), 50)]
        self.assertEqual(lines, expected)
        # sleep called len(points) times
        self.assertEqual(mock_sleep.call_count, len(pts))


if __name__ == "__main__":  # pragma: no cover
    import unittest
    unittest.main()
