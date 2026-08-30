# tests.test_structure_plan: regression coverage for the plate's solid TPU cradle.
from __future__ import annotations

import pathlib
import sys
import unittest

FUSION_ADDIN_DIRECTORY = pathlib.Path(__file__).resolve().parents[1] / "fusion_addin"
sys.path.insert(0, str(FUSION_ADDIN_DIRECTORY))

from structure_plan import build_plate_cradle_plan


class PlateCradlePlanTests(unittest.TestCase):
    """The 2 mm shell must remain inside the locked outer sole envelope."""

    def test_expands_the_pocket_by_two_millimetres_per_side(self) -> None:
        plan = build_plate_cradle_plan(91.0, 238.0, 1.63, 0.8844, 0.9217, 40.2, 2.0)

        self.assertAlmostEqual(plan.outer_thickness_mm, 5.63)
        self.assertAlmostEqual(plan.transverse_scale, 0.928356, places=6)
        self.assertAlmostEqual(plan.longitudinal_scale, 0.938507, places=6)
        self.assertAlmostEqual(plan.heel_cap_radius_mm, 42.2)

    def test_rejects_a_cradle_that_reaches_the_sidewall(self) -> None:
        with self.assertRaises(ValueError):
            build_plate_cradle_plan(20.0, 30.0, 2.0, 0.90, 0.90, 8.0, 2.0)
