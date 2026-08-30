# tests.test_variable_lattice: density-field regression coverage.
from __future__ import annotations

import unittest

from sole_ai.variable_lattice import _solid_gyroid_value, relative_density


class VariableDensityTests(unittest.TestCase):
    """Load-path zones should be denser while remaining smooth and bounded."""

    def test_forefoot_is_denser_than_central_heel(self) -> None:
        heel = relative_density(0.12, 0.0, 12.0)
        forefoot = relative_density(0.76, 0.0, 1.0)

        self.assertGreater(forefoot, heel)

    def test_density_changes_smoothly_and_stays_bounded(self) -> None:
        first = relative_density(0.50, 0.25, 3.0)
        nearby = relative_density(0.51, 0.25, 3.0)

        self.assertLess(abs(first - nearby), 0.02)
        self.assertTrue(0.18 <= first <= 0.55)

    def test_higher_density_expands_the_solid_phase(self) -> None:
        point = (1.0, 2.0, 3.0)

        self.assertLess(_solid_gyroid_value(point, 0.50), _solid_gyroid_value(point, 0.20))
