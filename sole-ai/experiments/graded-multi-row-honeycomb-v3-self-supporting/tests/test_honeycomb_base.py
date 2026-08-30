# tests.test_honeycomb_base: gates for the rail-free base-derived sole.
"""Verify skins, exposed sides, and absence of stiff reinforcement rails."""
from __future__ import annotations

import unittest

from cairo_real_sole.geometry import make_layout, solid_value
from cairo_real_sole.honeycomb_base import honeycomb_base_config


class HoneycombBaseTests(unittest.TestCase):
    """The full sole must use only honeycomb plus upper and lower skins."""

    def setUp(self) -> None:
        self.config = honeycomb_base_config()
        self.layout = make_layout(0.0, 100.0, 0.0, 20.0, self.config)
        self.intervals = ((0.0, 20.0),)

    def test_requested_skin_thickness_and_no_rails(self) -> None:
        self.assertEqual(self.config.anchor_skin_mm, 1.5)
        self.assertEqual(self.config.longitudinal_rail_count, 0)
        self.assertFalse(self.config.merge_vertical_source_intervals)
        self.assertTrue(self.config.plate_slot_enabled)
        self.assertEqual(self.config.plate_slot_expected_mm, 2.2)
        self.assertEqual(self.config.plate_slot_wall_mm, 1.5)

    def test_upper_and_ground_skins_are_continuous(self) -> None:
        for z_mm in (0.1, 1.4, 18.6, 19.9):
            self.assertLess(
                solid_value(
                    5.0,
                    50.0,
                    z_mm,
                    self.intervals,
                    (0.0, 30.0),
                    self.layout,
                    self.config,
                ),
                0.0,
            )

    def test_former_rail_planes_remain_open_inside_a_cell(self) -> None:
        centre_y = 2.0 * self.config.honeycomb_half_width_mm
        centre_z = self.config.honeycomb_half_height_mm
        for x_mm in (10.0, 20.0):
            self.assertGreater(
                solid_value(
                    x_mm,
                    centre_y,
                    centre_z,
                    self.intervals,
                    (0.0, 30.0),
                    self.layout,
                    self.config,
                ),
                0.0,
            )

    def test_no_solid_lateral_skin_is_introduced(self) -> None:
        centre_y = 2.0 * self.config.honeycomb_half_width_mm
        centre_z = self.config.honeycomb_half_height_mm
        self.assertGreater(
            solid_value(
                0.21,
                centre_y,
                centre_z,
                self.intervals,
                (0.0, 30.0),
                self.layout,
                self.config,
            ),
            0.0,
        )


if __name__ == "__main__":
    unittest.main()
