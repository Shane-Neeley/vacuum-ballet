#!/usr/bin/env python3
"""
Standard-library tests (no pytest required).
"""

import unittest
import sys
import os

# Add the src directory to the Python path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from main import circle, square, figure_eight, lissajous, spin_crazy


class TestPatterns(unittest.TestCase):
    def test_circle(self):
        pts = list(circle((0, 0), 100, steps=4))
        self.assertEqual(len(pts), 4)
        self.assertEqual(pts[0], (100, 0))  # right
        self.assertEqual(pts[1], (0, 100))  # up (map mm positive)
        self.assertEqual(pts[2], (-100, 0))  # left
        self.assertEqual(pts[3], (0, -100))  # down

    def test_square(self):
        pts = list(square((0, 0), half_mm=50))
        self.assertEqual(pts[0], (-50, -50))
        self.assertEqual(pts[1], (50, -50))
        self.assertEqual(pts[2], (50, 50))
        self.assertEqual(pts[3], (-50, 50))
        self.assertEqual(pts[4], (-50, -50))  # closed

    def test_figure_eight(self):
        pts = list(figure_eight((0, 0), 800, steps=24))
        self.assertEqual(len(pts), 24)
        xs = [x for x, _ in pts]
        ys = [y for _, y in pts]
        self.assertTrue(max(xs) <= 900 and min(xs) >= -900)
        self.assertTrue(max(ys) <= 900 and min(ys) >= -900)

    def test_lissajous(self):
        pts = list(lissajous((0, 0), ax=100, ay=50, steps=4))
        self.assertEqual(len(pts), 4)

    def test_circle_with_different_centers(self):
        """Test circle generation with different center points."""
        pts = list(circle((1000, 2000), 50, steps=4))
        self.assertEqual(len(pts), 4)
        # First point should be at center + radius in x direction
        self.assertEqual(pts[0], (1050, 2000))

    def test_circle_minimum_steps(self):
        """Test circle with minimum step count."""
        pts = list(circle((0, 0), 100, steps=1))
        self.assertEqual(len(pts), 1)
        self.assertEqual(pts[0], (100, 0))

    def test_square_is_closed(self):
        """Test that square returns to starting point."""
        pts = list(square((0, 0), half_mm=100))
        self.assertEqual(pts[0], pts[-1])  # closed path
        self.assertEqual(len(pts), 5)  # 4 corners + closing point

    def test_figure_eight_bounds(self):
        """Test that figure-eight stays within expected bounds."""
        pts = list(figure_eight((0, 0), 500, steps=20))
        xs = [x for x, _ in pts]
        ys = [y for _, y in pts]

        # Should stay roughly within 2 * radius
        self.assertTrue(all(-600 <= x <= 600 for x in xs))
        self.assertTrue(all(-600 <= y <= 600 for y in ys))

    def test_lissajous_with_custom_params(self):
        """Test lissajous with custom frequency parameters."""
        pts = list(lissajous((100, 200), ax=300, ay=400, a=2, b=3, steps=6))
        self.assertEqual(len(pts), 6)

        # All points should be offset by center
        xs = [x for x, _ in pts]
        ys = [y for _, y in pts]

        # Should be centered around (100, 200) with amplitude bounds
        self.assertTrue(all(-200 <= x <= 400 for x in xs))  # 100 ± 300
        self.assertTrue(all(-200 <= y <= 600 for y in ys))  # 200 ± 400

    def test_patterns_return_integers(self):
        """Test that all pattern functions return integer coordinates."""
        circle_pts = list(circle((0, 0), 100.7, steps=3))
        square_pts = list(square((0, 0), half_mm=50.3))
        fig8_pts = list(figure_eight((0, 0), 100.9, steps=3))
        liss_pts = list(lissajous((0, 0), ax=100.1, ay=50.2, steps=3))
        crazy_pts = list(spin_crazy((0, 0), 100.5, steps=3))

        for pts in [circle_pts, square_pts, fig8_pts, liss_pts, crazy_pts]:
            for x, y in pts:
                self.assertIsInstance(x, int, f"x coordinate {x} is not integer")
                self.assertIsInstance(y, int, f"y coordinate {y} is not integer")

    def test_spin_crazy(self):
        """Test spin_crazy pattern generation."""
        pts = list(spin_crazy((1000, 2000), 300, steps=10))
        self.assertEqual(len(pts), 10)

        # Check that points are within reasonable bounds (should stay roughly near center)
        # Allow for some variance due to the 'crazy' nature
        max_distance = 300 * 2  # Allow up to 2x radius for crazy movements
        for x, y in pts:
            distance = ((x - 1000) ** 2 + (y - 2000) ** 2) ** 0.5
            self.assertLessEqual(
                distance,
                max_distance,
                f"Point ({x}, {y}) too far from center (1000, 2000)",
            )

    def test_spin_crazy_reproducible(self):
        """Test that spin_crazy produces reproducible results due to seeded random."""
        pts1 = list(spin_crazy((0, 0), 400, steps=5))
        pts2 = list(spin_crazy((0, 0), 400, steps=5))

        # Should be identical due to fixed random seed
        self.assertEqual(pts1, pts2)

    def test_spin_crazy_different_centers(self):
        """Test spin_crazy with different center points."""
        center1 = (500, 1000)
        center2 = (1500, 2000)

        pts1 = list(spin_crazy(center1, 200, steps=5))
        pts2 = list(spin_crazy(center2, 200, steps=5))

        # Points should be offset by the difference in centers
        offset_x = center2[0] - center1[0]  # 1000
        offset_y = center2[1] - center1[1]  # 1000

        for (x1, y1), (x2, y2) in zip(pts1, pts2):
            # Due to randomness, we can't expect exact offset, but should be roughly correct
            expected_x2 = x1 + offset_x
            expected_y2 = y1 + offset_y

            # Allow some variance due to random jitter
            self.assertLess(abs(x2 - expected_x2), 400, "X offset not roughly correct")
            self.assertLess(abs(y2 - expected_y2), 400, "Y offset not roughly correct")

    def test_spin_crazy_minimum_steps(self):
        """Test spin_crazy with minimum step count."""
        pts = list(spin_crazy((0, 0), 200, steps=1))
        self.assertEqual(len(pts), 1)

        # Single point should be near center
        x, y = pts[0]
        distance = (x**2 + y**2) ** 0.5
        self.assertLessEqual(distance, 400)  # Should be within 2x radius


if __name__ == "__main__":
    unittest.main()
