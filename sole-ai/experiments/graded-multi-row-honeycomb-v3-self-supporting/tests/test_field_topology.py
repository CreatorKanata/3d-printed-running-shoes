# tests.test_field_topology: regression gates for isolated-material removal.
"""Protect the running sole from tiny printable islands and large disconnections."""
from __future__ import annotations

import unittest

from cairo_real_sole.field_topology import prune_tiny_components


class FieldTopologyTests(unittest.TestCase):
    """Only tiny noise may be removed; the load-bearing body must stay connected."""

    def test_tiny_island_is_removed(self) -> None:
        field = [[[1.0 for _ in range(4)] for _ in range(4)] for _ in range(4)]
        for ix in range(3):
            for iy in range(3):
                for iz in range(3):
                    field[ix][iy][iz] = -1.0
        field[3][3][3] = -1.0
        report = prune_tiny_components(field)
        self.assertEqual(report["removed_components"], 1)
        self.assertGreater(field[3][3][3], 0.0)


if __name__ == "__main__":
    unittest.main()

