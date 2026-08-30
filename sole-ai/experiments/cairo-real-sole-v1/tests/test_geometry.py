# tests.test_geometry: small gates for the real-sole pentagonal cell field.
"""Check shared walls, open cells, and deterministic independent-foot layouts."""
from __future__ import annotations

import unittest

from cairo_real_sole.config import SoleCellConfig
from cairo_real_sole.geometry import make_layout, solid_value


class RealSoleGeometryTests(unittest.TestCase):
    """The field must express thin connected arches before expensive STL builds."""

    def setUp(self) -> None:
        self.config = SoleCellConfig()
        self.layout = make_layout(0.0, 100.0, self.config)
        self.interval = ((0.0, 20.0),)

    def test_cell_centre_is_open_below_its_roof(self) -> None:
        left, right = self.layout.boundaries_mm[:2]
        y_mm = (left + right) / 2.0
        self.assertGreater(
            solid_value(y_mm, 8.0, self.interval, self.layout, self.config),
            0.0,
        )

    def test_shared_boundary_is_a_solid_vertical_rib(self) -> None:
        y_mm = self.layout.boundaries_mm[1]
        self.assertLess(
            solid_value(y_mm, 6.0, self.interval, self.layout, self.config),
            0.0,
        )

    def test_leg_and_apex_are_the_only_surface_anchors(self) -> None:
        left, right = self.layout.boundaries_mm[:2]
        centre = (left + right) / 2.0
        self.assertLess(solid_value(left, 0.1, self.interval, self.layout, self.config), 0.0)
        self.assertLess(solid_value(centre, 19.9, self.interval, self.layout, self.config), 0.0)
        self.assertGreater(solid_value(centre, 0.1, self.interval, self.layout, self.config), 0.0)


if __name__ == "__main__":
    unittest.main()
