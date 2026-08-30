# tests.test_geometry: gates for the self-supporting V3.1 honeycomb field.
"""Check print angles, smooth grading, skins, ties, and mesh cleanup."""
from __future__ import annotations

from collections import Counter
import math
import unittest

from cairo_real_sole.config import SoleCellConfig
from cairo_real_sole.geometry import graded_wall_mm, make_layout, solid_value
from cairo_real_sole.generate import (
    _cap_microscopic_boundary_loops,
    _clean_at_export_tolerance,
    _guard_isosurface_samples,
)


class RealSoleGeometryTests(unittest.TestCase):
    """The sampled field must contain a connected, short-member honeycomb."""

    def setUp(self) -> None:
        self.config = SoleCellConfig()
        self.layout = make_layout(0.0, 100.0, 0.0, 40.0, self.config)
        self.interval = ((0.0, 20.0),)

    def test_hexagon_centre_is_open(self) -> None:
        centre_y = 2.0 * self.config.honeycomb_half_width_mm
        centre_z = self.config.honeycomb_half_height_mm
        self.assertGreater(
            solid_value(
                5.0,
                centre_y,
                centre_z,
                self.interval,
                (0.0, 30.0),
                self.layout,
                self.config,
            ),
            0.0,
        )

    def test_honeycomb_has_no_horizontal_edges(self) -> None:
        self.assertEqual(self.layout.horizontal_edge_count, 0)
        self.assertTrue(all(
            abs(first[1] - second[1]) > 1e-8
            for first, second in self.layout.segments
        ))

    def test_honeycomb_contains_vertical_edges(self) -> None:
        self.assertTrue(any(
            abs(first[0] - second[0]) < 1e-8
            for first, second in self.layout.segments
        ))

    def test_every_diagonal_rises_at_least_45_degrees(self) -> None:
        angles = [
            math.degrees(math.atan2(abs(second[1] - first[1]), abs(second[0] - first[0])))
            for first, second in self.layout.segments
            if abs(second[0] - first[0]) > 1e-8
        ]
        self.assertTrue(angles)
        self.assertGreaterEqual(min(angles), 45.0)

    def test_real_height_has_about_four_rows(self) -> None:
        layout = make_layout(0.0, 218.06, 0.0, 40.0, self.config)
        self.assertGreaterEqual(layout.row_count, 4)
        self.assertLessEqual(layout.row_count, 5)

    def test_no_unbraced_member_exceeds_designed_cell_edge(self) -> None:
        lengths = [math.dist(first, second) for first, second in self.layout.segments]
        expected = max(
            2.0 * self.config.honeycomb_vertical_half_edge_mm,
            math.hypot(
                self.config.honeycomb_half_width_mm,
                self.config.honeycomb_half_height_mm
                - self.config.honeycomb_vertical_half_edge_mm,
            ),
        )
        self.assertLessEqual(max(lengths), expected + 1e-6)

    def test_interior_honeycomb_nodes_have_three_edges(self) -> None:
        incidence = Counter(
            tuple(round(value, 6) for value in point)
            for segment in self.layout.segments
            for point in segment
        )
        margin = 2.0 * self.config.honeycomb_half_height_mm
        interior = [
            count
            for (y_mm, z_mm), count in incidence.items()
            if margin < y_mm < self.layout.y_max - margin
            and margin < z_mm < self.layout.z_max - margin
        ]
        self.assertTrue(interior)
        self.assertTrue(all(count == 3 for count in interior))

    def test_wall_density_grades_smoothly_from_arch_to_ends(self) -> None:
        heel = graded_wall_mm(0.0, self.layout, self.config)
        arch = graded_wall_mm(50.0, self.layout, self.config)
        forefoot = graded_wall_mm(100.0, self.layout, self.config)
        self.assertAlmostEqual(heel, self.config.dense_wall_mm)
        self.assertAlmostEqual(arch, self.config.wall_mm)
        self.assertAlmostEqual(forefoot, self.config.dense_wall_mm)

    def test_top_and_bottom_are_continuous_skins(self) -> None:
        self.assertLess(solid_value(5.0, 50.0, 0.1, self.interval, (0.0, 30.0), self.layout, self.config), 0.0)
        self.assertLess(solid_value(5.0, 50.0, 19.9, self.interval, (0.0, 30.0), self.layout, self.config), 0.0)

    def test_material_stays_inside_lateral_envelope(self) -> None:
        self.assertGreater(
            solid_value(0.0, 50.0, 10.0, self.interval, (0.0, 30.0), self.layout, self.config),
            0.0,
        )

    def test_material_stays_inside_longitudinal_envelope(self) -> None:
        for y_mm in (-0.1, 100.1):
            self.assertGreater(
                solid_value(5.0, y_mm, 10.0, self.interval, (0.0, 30.0), self.layout, self.config),
                0.0,
            )

    def test_two_internal_rails_are_solid(self) -> None:
        for x_mm in (10.0, 20.0):
            self.assertLess(
                solid_value(x_mm, 50.0, 10.0, self.interval, (0.0, 30.0), self.layout, self.config),
                0.0,
            )

    def test_internal_rails_have_no_floating_underside(self) -> None:
        for z_mm in (1.6, 10.0, 18.4):
            for x_mm in (10.0, 20.0):
                self.assertLess(
                    solid_value(x_mm, 50.0, z_mm, self.interval, (0.0, 30.0), self.layout, self.config),
                    0.0,
                )

    def test_isosurface_guard_preserves_material_sign(self) -> None:
        field = [[[-0.0001, 0.0, 0.0001, -1.0, 1.0]]]
        adjusted = _guard_isosurface_samples(field, 0.005)
        self.assertEqual(adjusted, 3)
        self.assertEqual(field[0][0], [-0.005, -0.005, 0.005, -1.0, 1.0])

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
