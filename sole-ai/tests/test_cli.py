# tests.test_cli: command-surface regression tests for reproducible geometry jobs.
from __future__ import annotations

import unittest
from unittest.mock import patch

from sole_ai.cli import build_parser


class CommandLineTests(unittest.TestCase):
    """The organic generator must remain directly reproducible from the CLI."""

    def test_organic_lattice_command_accepts_each_independent_side(self) -> None:
        parser = build_parser()
        with patch("sys.argv", ["sole-ai", "generate-organic-lattice", "--side", "left"]):
            arguments = parser.parse_args()

        self.assertEqual(arguments.command, "generate-organic-lattice")
        self.assertEqual(arguments.side, "left")
        self.assertFalse(arguments.preview)

    def test_designer_volume_command_accepts_each_independent_side(self) -> None:
        parser = build_parser()
        with patch(
            "sys.argv",
            ["sole-ai", "generate-envelope-lattice", "--side", "right"],
        ):
            arguments = parser.parse_args()

        self.assertEqual(arguments.command, "generate-envelope-lattice")
        self.assertEqual(arguments.side, "right")
        self.assertFalse(arguments.preview)


if __name__ == "__main__":
    unittest.main()
