# tests.test_pipeline: regression coverage for the project configuration contract.
from __future__ import annotations

import unittest

from sole_ai.config import DEFAULT_CONFIG_PATH
from sole_ai.pipeline import load_config


class ConfigurationTests(unittest.TestCase):
    """The checked-in baseline must remain a usable constraint source."""

    def test_baseline_uses_millimetres_and_complete_bounds(self) -> None:
        config = load_config(DEFAULT_CONFIG_PATH)

        self.assertEqual(config["manufacturing"]["units"], "mm")
        self.assertEqual(config["outer_envelope"]["mode"], "locked_from_input_mesh")
        self.assertNotIn("heel_stack_mm", config["design_bounds"])
        self.assertIn("bottom_density", config["design_bounds"])
        self.assertIn("plate_corner_radius_mm", config["design_bounds"])
