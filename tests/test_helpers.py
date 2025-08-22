#!/usr/bin/env python3
"""Tests for helper functions in main.py."""

import asyncio
import os
import sys
import unittest
from unittest.mock import AsyncMock, patch

# Allow importing from the src directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from main import _clamp_radius, _wait_until_near, _vacuum_position, _parse_map_data  # type: ignore


class TestClampRadius(unittest.TestCase):
    def test_clamps_to_default_range(self):
        """Test that radius is clamped to default 200-1200mm range."""
        self.assertEqual(_clamp_radius(100), 200)  # too small
        self.assertEqual(_clamp_radius(500), 500)  # in range
        self.assertEqual(_clamp_radius(1500), 1200)  # too large

    def test_respects_env_vars(self):
        """Test that environment variables override defaults."""
        with patch.dict(
            os.environ, {"MIN_DANCE_RADIUS_MM": "300", "MAX_DANCE_RADIUS_MM": "1000"}
        ):
            self.assertEqual(_clamp_radius(200), 300)  # clamped to env min
            self.assertEqual(_clamp_radius(500), 500)  # in range
            self.assertEqual(_clamp_radius(1200), 1000)  # clamped to env max

    def test_handles_negative_values(self):
        """Test that negative values are clamped to minimum."""
        self.assertEqual(_clamp_radius(-100), 200)

    def test_handles_zero(self):
        """Test that zero is clamped to minimum."""
        self.assertEqual(_clamp_radius(0), 200)


class TestWaitUntilNear(unittest.TestCase):
    def setUp(self):
        self.client = AsyncMock()
        self.target = (1000, 2000)
        self.threshold = 250

    def test_returns_true_when_near_target(self):
        """Test that function returns True when robot is within threshold."""
        # Mock vacuum position close to target
        with patch("main._vacuum_position", AsyncMock(return_value=(1100, 2100))):
            result = asyncio.run(
                _wait_until_near(
                    self.client, self.target, self.threshold, timeout_s=1.0
                )
            )
            self.assertTrue(result)

    def test_returns_false_on_timeout(self):
        """Test that function returns False when timeout is reached."""
        # Mock vacuum position far from target
        with patch("main._vacuum_position", AsyncMock(return_value=(5000, 6000))):
            result = asyncio.run(
                _wait_until_near(
                    self.client, self.target, self.threshold, timeout_s=0.1
                )
            )
            self.assertFalse(result)

    def test_handles_no_position_data(self):
        """Test that function handles missing position data gracefully."""
        with patch("main._vacuum_position", AsyncMock(return_value=None)):
            result = asyncio.run(
                _wait_until_near(
                    self.client, self.target, self.threshold, timeout_s=0.1
                )
            )
            self.assertFalse(result)

    def test_exact_threshold_distance(self):
        """Test behavior when robot is exactly at threshold distance."""
        # Position exactly 250mm away (threshold distance)
        with patch("main._vacuum_position", AsyncMock(return_value=(1250, 2000))):
            result = asyncio.run(
                _wait_until_near(
                    self.client, self.target, self.threshold, timeout_s=1.0
                )
            )
            self.assertTrue(result)


class TestParseMapData(unittest.TestCase):
    def setUp(self):
        self.client = AsyncMock()

    def test_returns_none_on_no_raw_data(self):
        """Test that function returns None when no raw map data is available."""
        self.client.get_map_v1.return_value = None
        result = asyncio.run(_parse_map_data(self.client))
        self.assertIsNone(result)

    def test_returns_none_on_empty_data(self):
        """Test that function returns None when raw data is empty."""
        self.client.get_map_v1.return_value = b""
        result = asyncio.run(_parse_map_data(self.client))
        self.assertIsNone(result)

    def test_returns_none_on_import_error(self):
        """Test that function returns None when map parser imports fail."""
        self.client.get_map_v1.return_value = b"some_data"
        with patch("builtins.__import__", side_effect=ImportError):
            result = asyncio.run(_parse_map_data(self.client))
            self.assertIsNone(result)


class TestVacuumPosition(unittest.TestCase):
    def setUp(self):
        self.client = AsyncMock()

    def test_returns_vacuum_position_when_available(self):
        """Test that function returns vacuum position when available."""
        from vacuum_map_parser_base.map_data import MapData, Point

        mock_data = MapData()
        mock_data.vacuum_position = Point(1234, 5678)

        with patch("main._parse_map_data", AsyncMock(return_value=mock_data)):
            result = asyncio.run(_vacuum_position(self.client))
            self.assertEqual(result, (1234, 5678))

    def test_returns_none_when_no_vacuum_position(self):
        """Test that function returns None when vacuum position is not available."""
        from vacuum_map_parser_base.map_data import MapData

        mock_data = MapData()
        mock_data.vacuum_position = None

        with patch("main._parse_map_data", AsyncMock(return_value=mock_data)):
            result = asyncio.run(_vacuum_position(self.client))
            self.assertIsNone(result)

    def test_returns_none_when_parse_fails(self):
        """Test that function returns None when map parsing fails."""
        with patch("main._parse_map_data", AsyncMock(return_value=None)):
            result = asyncio.run(_vacuum_position(self.client))
            self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
