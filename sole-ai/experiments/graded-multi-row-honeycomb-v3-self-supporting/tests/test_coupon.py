# tests.test_coupon: fast gates for the 30 mm V3.2 rail-free box.
"""Check nominal size, source closure, and inherited self-supporting cells."""
from __future__ import annotations

from collections import Counter
import unittest

from cairo_real_sole.config import CouponConfig, SoleCellConfig
from cairo_real_sole.coupon import coupon_sole_config, cube_triangles
from cairo_real_sole.geometry import make_layout, solid_value


class CouponTests(unittest.TestCase):
    """The coupon source and cell layout must match the print request."""

    def test_source_cube_is_30_mm_and_closed(self) -> None:
        coupon = CouponConfig()
        triangles = cube_triangles(coupon.size_mm)
        points = [point for triangle in triangles for point in triangle]
        self.assertEqual(len(triangles), 12)
        for axis in range(3):
            self.assertEqual(min(point[axis] for point in points), 0.0)
            self.assertEqual(max(point[axis] for point in points), 30.0)
        edges = Counter(
            tuple(sorted((first, second)))
            for triangle in triangles
            for first, second in zip(triangle, triangle[1:] + triangle[:1])
        )
        self.assertTrue(edges)
        self.assertTrue(all(count == 2 for count in edges.values()))

    def test_coupon_inherits_self_supporting_cell_angles(self) -> None:
        config = coupon_sole_config(CouponConfig())
        layout = make_layout(0.0, 30.0, 0.0, 30.0, config)
        self.assertEqual(layout.horizontal_edge_count, 0)
        self.assertGreaterEqual(layout.minimum_rising_angle_deg, 45.0)
        self.assertEqual(layout.row_count, 3)
        self.assertEqual(config.longitudinal_rail_count, 0)

    def test_production_grid_resolves_the_wall(self) -> None:
        coupon = CouponConfig()
        coupon.validate()
        self.assertGreaterEqual(
            SoleCellConfig().wall_mm / coupon.production_step_mm,
            3.0,
        )

    def test_coupon_has_no_material_on_former_rail_planes(self) -> None:
        config = coupon_sole_config(CouponConfig())
        layout = make_layout(0.0, 30.0, 0.0, 30.0, config)
        interval = ((0.0, 30.0),)
        centre_y = 2.0 * config.honeycomb_half_width_mm
        centre_z = config.honeycomb_half_height_mm
        for x_mm in (10.0, 20.0):
            self.assertGreater(
                solid_value(
                    x_mm,
                    centre_y,
                    centre_z,
                    interval,
                    (0.0, 30.0),
                    layout,
                    config,
                ),
                0.0,
            )


if __name__ == "__main__":
    unittest.main()
