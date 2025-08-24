"""Tests for CLI argument parsing and main function."""

import unittest
from unittest.mock import patch
from io import StringIO
import os
import sys

# Allow importing from the src directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from main import main


class TestCLI(unittest.TestCase):
    def test_help_output(self):
        """Help text is shown when no command is given."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            main([])
            self.assertIn("usage", mock_stdout.getvalue().lower())

    def test_dance_command(self):
        """Dance command parses arguments and calls dance()."""
        with patch("main.dance") as mock_dance:
            main(["dance", "circle", "800", "600"])
            mock_dance.assert_called_once_with("circle", 800, 600)

    def test_dance_defaults(self):
        """Dance command uses default size and beat when omitted."""
        with patch("main.dance") as mock_dance:
            main(["dance", "spin"])
            mock_dance.assert_called_once_with("spin", 100, 500)

    def test_beep_command(self):
        """Beep command invokes beep with default times."""
        with patch("main.beep") as mock_beep:
            main(["beep"])
            mock_beep.assert_called_once_with(1)

    def test_invalid_pattern_raises_error(self):
        """Invalid patterns cause argparse to exit."""
        with self.assertRaises(SystemExit):
            with patch("sys.stderr", StringIO()):
                main(["dance", "hexagon", "100"])


if __name__ == "__main__":
    unittest.main()
