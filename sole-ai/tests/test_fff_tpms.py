# tests.test_fff_tpms: FFF graded-Gyroid field regression coverage.
from __future__ import annotations

import unittest

from sole_ai.config import TPMS_WALL_MAX_MM, TPMS_WALL_MIN_MM
from sole_ai.fff_tpms import _gyroid_and_gradient, _tpms_field, _wall_thickness
from sole_ai.stl import MeshBounds


class FffTpmsTests(unittest.TestCase):
    """The selected FFF field must remain continuous, warped, and load graded."""

    def setUp(self) -> None:
        self.bounds = MeshBounds((-45.0, -120.0, -30.0), (45.0, 120.0, 0.0), 0)
        self.plate = ((100.0, -16.0), (50.0, -18.0), (0.0, -19.0), (-50.0, -16.0), (-100.0, -10.0))

    def test_wall_thickness_is_bounded_and_load_graded(self) -> None:
        heel = _wall_thickness((0.0, 90.0, -10.0), self.bounds, self.plate)
        forefoot = _wall_thickness((0.0, -70.0, -12.0), self.bounds, self.plate)

        self.assertTrue(TPMS_WALL_MIN_MM <= heel <= TPMS_WALL_MAX_MM)
        self.assertTrue(TPMS_WALL_MIN_MM <= forefoot <= TPMS_WALL_MAX_MM)
        self.assertGreater(forefoot, heel)

    def test_field_is_continuous_and_has_a_safe_gradient(self) -> None:
        point = (4.0, 7.0, -11.0)
        nearby = (4.01, 7.0, -11.0)

        _, gradient = _gyroid_and_gradient(point)
        self.assertGreaterEqual(gradient, 0.15)
        self.assertLess(
            abs(_tpms_field(point, self.bounds, self.plate) - _tpms_field(nearby, self.bounds, self.plate)),
            0.05,
        )
