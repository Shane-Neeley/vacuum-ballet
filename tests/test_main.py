#!/usr/bin/env python3
"""
Standard-library tests (no pytest required).
"""
import unittest
import sys
import os

# Add the src directory to the Python path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import circle, square, figure_eight, lissajous

class TestPatterns(unittest.TestCase):
    def test_circle(self):
        pts = list(circle((0, 0), 100, steps=4))
        self.assertEqual(len(pts), 4)
        self.assertEqual(pts[0], (100, 0))   # right
        self.assertEqual(pts[1], (0, 100))   # up (map mm positive)
        self.assertEqual(pts[2], (-100, 0))  # left
        self.assertEqual(pts[3], (0, -100))  # down

    def test_square(self):
        pts = list(square((0,0), half_mm=50))
        self.assertEqual(pts[0], (-50, -50))
        self.assertEqual(pts[1], ( 50, -50))
        self.assertEqual(pts[2], ( 50,  50))
        self.assertEqual(pts[3], (-50,  50))
        self.assertEqual(pts[4], (-50, -50))  # closed

    def test_figure_eight(self):
        pts = list(figure_eight((0,0), 800, steps=24))
        self.assertEqual(len(pts), 24)
        xs = [x for x,_ in pts]; ys = [y for _,y in pts]
        self.assertTrue(max(xs) <= 900 and min(xs) >= -900)
        self.assertTrue(max(ys) <= 900 and min(ys) >= -900)

    def test_lissajous(self):
        pts = list(lissajous((0, 0), ax=100, ay=50, steps=4))
        self.assertEqual(len(pts), 4)

if __name__ == "__main__":
    unittest.main()
