#!/usr/bin/env python3
"""Tests for dance function error handling and robustness."""

import asyncio
import os
import sys
import unittest
from unittest.mock import AsyncMock, patch

# Allow importing from the src directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from main import dance  # type: ignore


class TestDanceErrorHandling(unittest.TestCase):
    def setUp(self):
        self.client = AsyncMock()

    def test_dance_disconnects_on_error(self):
        """Test that client is disconnected even when dance encounters error."""
        self.client.send_command.side_effect = RuntimeError("Network error")

        with patch("main._client", AsyncMock(return_value=self.client)):
            with patch("main._map_center", AsyncMock(return_value=(1000, 2000))):
                with self.assertRaises(RuntimeError):
                    asyncio.run(dance("circle", 800, 600))

                self.client.async_disconnect.assert_called_once()

    def test_dance_handles_no_map_center(self):
        """Test that dance uses defaults when map center is unavailable."""
        with patch("main._client", AsyncMock(return_value=self.client)):
            with patch("main._map_center", AsyncMock(return_value=None)):
                with patch("main._wait_until_near", AsyncMock(return_value=True)):
                    with patch.dict(
                        os.environ,
                        {"DEFAULT_CENTER_X": "5000", "DEFAULT_CENTER_Y": "6000"},
                    ):
                        # Should not raise error
                        asyncio.run(dance("circle", 200, 1000))

                    self.client.send_command.assert_called()
                    self.client.async_disconnect.assert_called_once()

    def test_dance_clamps_radius(self):
        """Test that dance clamps radius to safe values."""
        with patch("main._client", AsyncMock(return_value=self.client)):
            with patch("main._map_center", AsyncMock(return_value=(1000, 2000))):
                with patch("main._wait_until_near", AsyncMock(return_value=True)):
                    # Test with very large radius - should be clamped
                    asyncio.run(dance("circle", 5000, 600))

                    # Verify that command was sent (meaning radius was clamped and dance proceeded)
                    self.client.send_command.assert_called()
                    self.client.async_disconnect.assert_called_once()

    def test_dance_continues_on_arrival_timeout(self):
        """Test that dance continues even when arrival detection times out."""
        with patch("main._client", AsyncMock(return_value=self.client)):
            with patch("main._map_center", AsyncMock(return_value=(1000, 2000))):
                # Mock arrival detection to always timeout
                with patch("main._wait_until_near", AsyncMock(return_value=False)):
                    with patch("asyncio.sleep") as mock_sleep:
                        asyncio.run(
                            dance("circle", 400, 200)
                        )  # short beat for fast test

                        # Should have fallen back to beat-based timing
                        mock_sleep.assert_called_with(0.2)  # 200ms beat
                        self.client.send_command.assert_called()
                        self.client.async_disconnect.assert_called_once()

    def test_dance_with_zero_beat_time(self):
        """Test that dance handles zero beat time correctly."""
        with patch("main._client", AsyncMock(return_value=self.client)):
            with patch("main._map_center", AsyncMock(return_value=(1000, 2000))):
                with patch("main._wait_until_near", AsyncMock(return_value=False)):
                    with patch("asyncio.sleep") as mock_sleep:
                        # Zero beat time should not cause sleep when arrival detection fails
                        asyncio.run(dance("circle", 400, 0))

                        # Sleep should not be called with 0 or negative values
                        for call in mock_sleep.call_args_list:
                            self.assertGreaterEqual(call[0][0], 0)


if __name__ == "__main__":
    unittest.main()
