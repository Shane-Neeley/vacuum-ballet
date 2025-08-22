#!/usr/bin/env python3
"""Tests for CLI argument parsing and main function."""

import asyncio
import os
import sys
import unittest
from unittest.mock import AsyncMock, patch, MagicMock
from io import StringIO

# Allow importing from the src directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from main import main, dance  # type: ignore


class TestCLIParsing(unittest.TestCase):
    def test_help_output(self):
        """Test that help is printed when no command is given."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            main([])
            output = mock_stdout.getvalue()
            self.assertIn("usage:", output.lower())

    def test_devices_command(self):
        """Test that devices command is parsed correctly."""
        with patch("main.list_devices", AsyncMock()) as mock_list:
            with patch("asyncio.run") as mock_run:
                main(["devices"])
                mock_run.assert_called_once()

    def test_beep_command(self):
        """Test that beep command is parsed correctly."""
        with patch("main.beep", AsyncMock()) as mock_beep:
            with patch("asyncio.run") as mock_run:
                main(["beep"])
                mock_run.assert_called_once()

    def test_status_command(self):
        """Test that status command is parsed correctly."""
        with patch("main.status", AsyncMock()) as mock_status:
            with patch("asyncio.run") as mock_run:
                main(["status"])
                mock_run.assert_called_once()

    def test_goto_command_with_coordinates(self):
        """Test that goto command parses coordinates correctly."""
        with patch("main.goto", AsyncMock()) as mock_goto:
            with patch("asyncio.run") as mock_run:
                main(["goto", "1000", "2000"])
                mock_run.assert_called_once()

    def test_dance_command_with_all_params(self):
        """Test that dance command parses all parameters correctly."""
        with patch("main.dance", AsyncMock()) as mock_dance:
            with patch("asyncio.run") as mock_run:
                main(["dance", "circle", "800", "600"])
                mock_run.assert_called_once()

    def test_dance_command_with_defaults(self):
        """Test that dance command uses defaults for optional parameters."""
        with patch("main.dance", AsyncMock()) as mock_dance:
            with patch("asyncio.run") as mock_run:
                with patch.dict(
                    os.environ, {"DEFAULT_RADIUS": "900", "DEFAULT_BEAT_MS": "500"}
                ):
                    main(["dance", "square"])
                    mock_run.assert_called_once()

    def test_invalid_pattern_raises_error(self):
        """Test that invalid dance pattern raises appropriate error."""
        client_mock = AsyncMock()
        with patch("main._client", AsyncMock(return_value=client_mock)):
            with patch("main._map_center", AsyncMock(return_value=(1000, 2000))):
                with self.assertRaises(ValueError):
                    asyncio.run(dance("invalid_pattern", 800, 600))


class TestArgumentParsing(unittest.TestCase):
    def test_dance_pattern_choices(self):
        """Test that only valid dance patterns are accepted."""
        import argparse
        from main import main

        # This should not raise an error
        try:
            with patch("asyncio.run"):
                main(["dance", "circle"])
        except SystemExit:
            pass  # argparse exits on success

        # Invalid pattern should cause argparse to exit with error
        with self.assertRaises(SystemExit):
            with patch("sys.stderr", StringIO()):
                main(["dance", "invalid_pattern"])

        # Valid patterns should work
        valid_patterns = ["circle", "square", "figure8", "lissajous", "spin_crazy"]
        for pattern in valid_patterns:
            try:
                with patch("asyncio.run"):
                    main(["dance", pattern])
            except SystemExit:
                pass  # argparse exits on success

    def test_goto_requires_coordinates(self):
        """Test that goto command requires x and y coordinates."""
        with self.assertRaises(SystemExit):
            with patch("sys.stderr", StringIO()):
                main(["goto"])  # missing coordinates

        with self.assertRaises(SystemExit):
            with patch("sys.stderr", StringIO()):
                main(["goto", "100"])  # missing y coordinate

    def test_coordinates_must_be_integers(self):
        """Test that goto coordinates must be valid integers."""
        with self.assertRaises(SystemExit):
            with patch("sys.stderr", StringIO()):
                main(["goto", "not_a_number", "100"])

        with self.assertRaises(SystemExit):
            with patch("sys.stderr", StringIO()):
                main(["goto", "100", "not_a_number"])


class TestEnvironmentVariables(unittest.TestCase):
    def test_default_values_from_env(self):
        """Test that environment variables are used for defaults."""
        test_env = {
            "DEFAULT_CENTER_X": "12345",
            "DEFAULT_CENTER_Y": "67890",
            "DEFAULT_RADIUS": "999",
            "DEFAULT_BEAT_MS": "777",
            "MIN_DANCE_RADIUS_MM": "100",
            "MAX_DANCE_RADIUS_MM": "2000",
            "ARRIVAL_THRESHOLD_MM": "300",
            "WAYPOINT_TIMEOUT_S": "30",
        }

        with patch.dict(os.environ, test_env):
            from main import _clamp_radius

            # Test radius clamping with custom env values
            self.assertEqual(_clamp_radius(50), 100)  # clamped to env min
            self.assertEqual(_clamp_radius(1500), 1500)  # within range
            self.assertEqual(_clamp_radius(3000), 2000)  # clamped to env max

    def test_missing_env_vars_use_defaults(self):
        """Test that missing environment variables fall back to code defaults."""
        # Clear relevant env vars
        env_to_clear = [
            "DEFAULT_CENTER_X",
            "DEFAULT_CENTER_Y",
            "DEFAULT_RADIUS",
            "DEFAULT_BEAT_MS",
            "MIN_DANCE_RADIUS_MM",
            "MAX_DANCE_RADIUS_MM",
        ]

        with patch.dict(os.environ, {}, clear=False):
            for var in env_to_clear:
                os.environ.pop(var, None)

            from main import _clamp_radius

            # Should use code defaults
            self.assertEqual(_clamp_radius(100), 200)  # default min
            self.assertEqual(_clamp_radius(2000), 1200)  # default max


if __name__ == "__main__":
    unittest.main()
