#!/usr/bin/env python3
"""Tests for basic command functions."""

import asyncio
import os
import sys
import unittest
from unittest.mock import AsyncMock, patch

# Allow importing from the src directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import clean, dock, status as status_cmd  # type: ignore
from roborock.roborock_typing import RoborockCommand
from roborock.containers import Status


class TestCommands(unittest.TestCase):
    def setUp(self) -> None:
        self.client = AsyncMock()
        self.client.send_command = AsyncMock()
        self.client.async_disconnect = AsyncMock()
        self.client.get_status = AsyncMock()

    def test_clean_sends_start(self) -> None:
        with patch('main._client', AsyncMock(return_value=self.client)):
            asyncio.run(clean())
            self.client.send_command.assert_called_with(RoborockCommand.APP_START)
            self.client.async_disconnect.assert_awaited()

    def test_dock_sends_charge(self) -> None:
        with patch('main._client', AsyncMock(return_value=self.client)):
            asyncio.run(dock())
            self.client.send_command.assert_called_with(RoborockCommand.APP_CHARGE)
            self.client.async_disconnect.assert_awaited()

    def test_clean_disconnects_on_error(self) -> None:
        self.client.send_command.side_effect = RuntimeError
        with patch('main._client', AsyncMock(return_value=self.client)):
            with self.assertRaises(RuntimeError):
                asyncio.run(clean())
        self.client.async_disconnect.assert_awaited()

    def test_status_prints(self) -> None:
        st = Status(battery=50)
        self.client.get_status.return_value = st
        with patch('main._client', AsyncMock(return_value=self.client)):
            with patch('builtins.print') as mock_print:
                asyncio.run(status_cmd())
            mock_print.assert_called_with("State: unknown, Battery: 50%")
            self.client.async_disconnect.assert_awaited()


if __name__ == '__main__':  # pragma: no cover - manual execution
    unittest.main()
