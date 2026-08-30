# tests.test_plate_slot: geometry gates for the pause-and-insert plate pocket.
"""Check the preserved solid upper, lower skin, void, and perimeter wall."""
from __future__ import annotations

import unittest

from cairo_real_sole.geometry import make_layout
from cairo_real_sole.honeycomb_base import honeycomb_base_config
from cairo_real_sole.plate_slot import _inside_clearance, _plate_value, _slot_levels


class PlateSlotTests(unittest.TestCase):
    """The nested cutter must remain a closed 2.2 mm insertion pocket."""

    def setUp(self) -> None:
        self.config = honeycomb_base_config()
        self.layout = make_layout(0.0, 30.0, 0.0, 30.0, self.config)
        self.outer = (0.0, 30.0)
        self.plan = (0.0, 30.0)

    def value(self, z_mm: float, clearance):
        """Sample a cell centre through the lower, pocket, and upper zones."""
        return _plate_value(
            5.0,
            8.0,
            z_mm,
            self.outer,
            self.plan,
            self.layout,
            self.config,
            10.0,
            12.2,
            clearance,
        )

    def test_detects_the_nested_2_2_mm_slot(self) -> None:
        columns = {
            (0, 0): ((0.0, 10.0), (12.2, 20.0)),
            (1, 0): ((0.0, 10.0), (12.2, 21.0)),
        }
        self.assertEqual(_slot_levels(columns, 2.2), (10.0, 12.2))

    def test_clearance_grows_from_the_slot_perimeter(self) -> None:
        keys = {(x, y) for x in range(5) for y in range(5)}
        clearance = _inside_clearance(keys, 0.7, 0.7)
        self.assertLess(clearance[(0, 0)], self.config.plate_slot_wall_mm)
        self.assertGreater(clearance[(2, 2)], clearance[(0, 0)])

    def test_upper_region_remains_solid(self) -> None:
        self.assertLess(self.value(20.0, 5.0), 0.0)

    def test_pocket_centre_remains_empty(self) -> None:
        self.assertGreater(self.value(11.0, 5.0), 0.0)

    def test_pocket_perimeter_is_solid(self) -> None:
        self.assertLess(self.value(11.0, 0.4), 0.0)

    def test_lower_pocket_floor_is_solid(self) -> None:
        self.assertLess(self.value(9.5, 5.0), 0.0)

    def test_lower_cell_centre_remains_open(self) -> None:
        self.assertGreater(self.value(6.5, 5.0), 0.0)


if __name__ == "__main__":
    unittest.main()
