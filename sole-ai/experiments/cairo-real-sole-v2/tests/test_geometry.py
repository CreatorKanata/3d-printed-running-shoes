# tests.test_geometry: small gates for the real-sole pentagonal cell field.
"""Check shared walls, open cells, and deterministic independent-foot layouts."""
from __future__ import annotations

import unittest

from cairo_real_sole.config import SoleCellConfig
from cairo_real_sole.geometry import make_layout, solid_value
from cairo_real_sole.generate import (
    _cap_microscopic_boundary_loops,
    _clean_at_export_tolerance,
    _guard_isosurface_samples,
)


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
            solid_value(5.0, y_mm, 8.0, self.interval, (0.0, 30.0), self.layout, self.config),
            0.0,
        )

    def test_shared_boundary_is_a_solid_vertical_rib(self) -> None:
        y_mm = self.layout.boundaries_mm[1]
        self.assertLess(
            solid_value(10.0, y_mm, 6.0, self.interval, (0.0, 30.0), self.layout, self.config),
            0.0,
        )

    def test_top_and_bottom_are_continuous_load_spreading_skins(self) -> None:
        left, right = self.layout.boundaries_mm[:2]
        centre = (left + right) / 2.0
        self.assertLess(solid_value(5.0, left, 0.1, self.interval, (0.0, 30.0), self.layout, self.config), 0.0)
        self.assertLess(solid_value(5.0, centre, 19.9, self.interval, (0.0, 30.0), self.layout, self.config), 0.0)
        self.assertLess(solid_value(5.0, centre, 0.1, self.interval, (0.0, 30.0), self.layout, self.config), 0.0)

    def test_full_length_sole_has_about_thirty_cells(self) -> None:
        layout = make_layout(0.0, 218.06, self.config)
        self.assertEqual(len(layout.shoulders), 30)

    def test_surface_bias_is_negligible_beside_the_wall(self) -> None:
        self.assertLess(self.config.surface_bias_mm, self.config.wall_mm / 100.0)

    def test_isosurface_guard_preserves_material_sign(self) -> None:
        field = [[[-0.0001, 0.0, 0.0001, -1.0, 1.0]]]
        adjusted = _guard_isosurface_samples(field, 0.005)
        self.assertEqual(adjusted, 3)
        self.assertEqual(field[0][0], [-0.005, -0.005, 0.005, -1.0, 1.0])

    def test_two_longitudinal_rails_are_solid(self) -> None:
        left, right = self.layout.boundaries_mm[1:3]
        centre = (left + right) / 2.0
        self.assertLess(
            solid_value(10.0, centre, 8.0, self.interval, (0.0, 30.0), self.layout, self.config),
            0.0,
        )
        self.assertLess(
            solid_value(20.0, centre, 8.0, self.interval, (0.0, 30.0), self.layout, self.config),
            0.0,
        )

    def test_export_cleaner_removes_quantised_micro_triangle(self) -> None:
        triangles = [
            ((0.0, 0.0, 0.0), (0.000001, 0.0, 0.0), (0.0, 1.0, 0.0)),
            ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        ]
        self.assertEqual(len(_clean_at_export_tolerance(triangles)), 1)

    def test_only_microscopic_closed_boundary_is_capped(self) -> None:
        size = 0.001
        open_tetrahedron = [
            ((0.0, 0.0, 0.0), (size, 0.0, 0.0), (0.0, 0.0, size)),
            ((size, 0.0, 0.0), (0.0, size, 0.0), (0.0, 0.0, size)),
            ((0.0, size, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, size)),
        ]
        repaired, report = _cap_microscopic_boundary_loops(open_tetrahedron)
        self.assertEqual(report["capped_loops"], 1)
        self.assertGreater(len(repaired), len(open_tetrahedron))


if __name__ == "__main__":
    unittest.main()
