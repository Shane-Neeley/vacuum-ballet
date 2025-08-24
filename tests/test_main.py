#!/usr/bin/env python3
"""Unit tests for basic dance patterns."""

import unittest
import os
import sys

# Add the src directory to the Python path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from main import circle, square, spin


class TestPatterns(unittest.TestCase):
    def test_circle(self):
        pts = circle((0, 0), 100, steps=4)
        self.assertEqual(pts, [(100, 0), (0, 100), (-100, 0), (0, -100)])

    def test_square(self):
        pts = square((0, 0), half_mm=50)
        self.assertEqual(
            pts,
            [(-50, -50), (50, -50), (50, 50), (-50, 50), (-50, -50)],
        )

    def test_spin(self):
        pts = spin((0, 0), radius_mm=200, steps=4)
        self.assertEqual(pts, [(200, 0), (0, 200), (-200, 0), (0, -200)])


if __name__ == "__main__":
    unittest.main()
