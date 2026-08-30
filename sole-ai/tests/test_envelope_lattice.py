# tests.test_envelope_lattice: full-volume organic-lattice regression coverage.
from __future__ import annotations

import math
import random
import unittest

from sole_ai.config import (
    ENVELOPE_LATTICE_EDGE_MAX_COVERAGE_RADIUS_MM,
    ENVELOPE_LATTICE_INTERIOR_MAX_COVERAGE_RADIUS_MM,
    ENVELOPE_LATTICE_MAX_BRANCH_DIAMETER_MM,
    ENVELOPE_LATTICE_MAX_NODE_SPACING_MM,
    ENVELOPE_LATTICE_MAX_UNDERLINKED_NODE_RATIO,
    ENVELOPE_LATTICE_MIN_AVERAGE_PARENT_LINKS,
    ENVELOPE_LATTICE_MIN_BRANCH_DIAMETER_MM,
    ENVELOPE_LATTICE_MIN_NODE_SPACING_MM,
    ENVELOPE_LATTICE_NETWORK_DENSITY_RATIO,
    ENVELOPE_LATTICE_NODE_FACTOR,
)
from sole_ai.envelope_density import load_fraction
from sole_ai.envelope_clearance import measure_side_clearance
from sole_ai.envelope_domain import points_clear, rasterize_intervals, straight_path
from sole_ai.envelope_lattice import _field, _interval_field, _planform_clearance
from sole_ai.envelope_network import build_fill_network
from sole_ai.envelope_nodes import (
    base_layer,
    local_layer_count,
    next_layer,
    node_radius,
    node_spacing,
)
from sole_ai.stl import MeshBounds


class EnvelopeLatticeTests(unittest.TestCase):
    """The designer-volume generator must stay smooth, graded, and bounded."""

    def setUp(self) -> None:
        self.bounds = MeshBounds((-45.0, 0.0, -40.0), (45.0, 220.0, 0.0), 0)

    def test_density_is_smooth_and_high_on_propulsion_and_heel_paths(self) -> None:
        heel = load_fraction((0.0, 198.0, -20.0), self.bounds)
        arch = load_fraction((0.0, 119.0, -20.0), self.bounds)
        forefoot = load_fraction((0.0, 55.0, -20.0), self.bounds)

        self.assertGreater(forefoot, arch)
        self.assertGreater(heel, 0.40)
        values = [
            load_fraction((0.0, y, -20.0), self.bounds)
            for y in range(0, 221)
        ]
        self.assertLess(
            max(abs(first - second) for first, second in zip(values, values[1:])),
            0.03,
        )

    def test_branch_diameter_bounds_match_the_requested_range(self) -> None:
        self.assertEqual(ENVELOPE_LATTICE_MIN_BRANCH_DIAMETER_MM, 1.5)
        self.assertEqual(ENVELOPE_LATTICE_MAX_BRANCH_DIAMETER_MM, 2.0)

    def test_network_density_is_fifty_percent_of_v8(self) -> None:
        self.assertEqual(ENVELOPE_LATTICE_NETWORK_DENSITY_RATIO, 0.50)
        self.assertEqual(ENVELOPE_LATTICE_MAX_UNDERLINKED_NODE_RATIO, 0.09)
        self.assertAlmostEqual(ENVELOPE_LATTICE_NODE_FACTOR, 1.10 * 0.50)
        spacing_scale = 1.0 / math.sqrt(0.50)
        self.assertAlmostEqual(
            ENVELOPE_LATTICE_MIN_NODE_SPACING_MM,
            3.0 * spacing_scale,
        )
        self.assertAlmostEqual(
            ENVELOPE_LATTICE_MAX_NODE_SPACING_MM,
            4.2 * spacing_scale,
        )

    def test_edge_radius_stays_below_the_requested_diameter_ceiling(self) -> None:
        axes = [float(value) for value in range(21)]
        columns = {(ix, iy): (0.0, 20.0) for ix in range(21) for iy in range(21)}
        clearance = _planform_clearance(columns, 1.0)
        domain = (axes, axes, columns, clearance)
        bounds = MeshBounds((0.0, 0.0, 0.0), (20.0, 20.0, 20.0), 0)

        diameter = 2.0 * node_radius((1.0, 10.0, 0.0), bounds, domain)

        self.assertGreaterEqual(diameter, ENVELOPE_LATTICE_MIN_BRANCH_DIAMETER_MM)
        self.assertLessEqual(diameter, ENVELOPE_LATTICE_MAX_BRANCH_DIAMETER_MM)
        self.assertLess(diameter, ENVELOPE_LATTICE_MAX_BRANCH_DIAMETER_MM)

    def test_low_load_interior_reaches_the_requested_minimum_diameter(self) -> None:
        x_axis, y_axis = [-45.0, 45.0], [0.0, 220.0]
        columns = {(ix, iy): (-40.0, 0.0) for ix in range(2) for iy in range(2)}
        clearance = {key: 45.0 for key in columns}
        domain = (x_axis, y_axis, columns, clearance)
        diameter = 2.0 * node_radius((0.0, 147.0, -20.0), self.bounds, domain)

        self.assertAlmostEqual(
            diameter,
            ENVELOPE_LATTICE_MIN_BRANCH_DIAMETER_MM,
        )

    def test_layer_count_uses_local_band_thickness(self) -> None:
        axes = [float(value) for value in range(21)]
        columns = {(ix, iy): (0.0, 20.0) for ix in range(21) for iy in range(21)}
        clearance = {key: 10.0 for key in columns}

        count = local_layer_count((axes, axes, columns, clearance))

        self.assertEqual(count, 4)
        self.assertLess(count, 15)

    def test_perimeter_spacing_and_coverage_are_denser(self) -> None:
        axes = [float(value) for value in range(21)]
        columns = {(ix, iy): (0.0, 20.0) for ix in range(21) for iy in range(21)}
        clearance = _planform_clearance(columns, 1.0)
        domain = (axes, axes, columns, clearance)
        bounds = MeshBounds((0.0, 0.0, 0.0), (20.0, 20.0, 20.0), 0)

        edge = node_spacing((1.0, 10.0, 0.0), bounds, domain)
        interior = node_spacing((10.0, 10.0, 0.0), bounds, domain)
        _, (maximum, edge_maximum) = base_layer(
            random.Random(1234),
            bounds,
            domain,
        )

        self.assertLess(edge, interior)
        self.assertLessEqual(maximum, ENVELOPE_LATTICE_INTERIOR_MAX_COVERAGE_RADIUS_MM)
        self.assertLessEqual(
            edge_maximum,
            ENVELOPE_LATTICE_EDGE_MAX_COVERAGE_RADIUS_MM,
        )

    def test_colonized_layer_contains_non_vertical_attractor_growth(self) -> None:
        axes = [float(value) for value in range(21)]
        columns = {(ix, iy): (0.0, 20.0) for ix in range(21) for iy in range(21)}
        domain = (axes, axes, columns, _planform_clearance(columns, 1.0))
        bounds = MeshBounds((0.0, 0.0, 0.0), (20.0, 20.0, 20.0), 0)
        rng = random.Random(4321)
        previous, _ = base_layer(rng, bounds, domain)

        nodes, primary, _ = next_layer(rng, previous, 1.0 / 3.0, bounds, domain)
        lateral_shifts = [
            math.dist(node[:2], previous[parent_index][:2])
            for node, parent_index in zip(nodes, primary)
        ]

        self.assertEqual(len(nodes), len(primary))
        self.assertGreater(max(lateral_shifts), 0.75)

    def test_thin_source_intervals_remain_solid(self) -> None:
        self.assertLess(_interval_field(3.0, (0.0, 6.0), 1.0), 0.0)
        self.assertGreater(_interval_field(3.05, (0.0, 6.1), 1.0), 0.0)

    def test_reinforced_network_meets_coverage_and_link_gates(self) -> None:
        axes = [float(value) for value in range(21)]
        columns = {(ix, iy): (0.0, 20.0) for ix in range(21) for iy in range(21)}
        domain = (axes, axes, columns, _planform_clearance(columns, 1.0))
        bounds = MeshBounds((0.0, 0.0, 0.0), (20.0, 20.0, 20.0), 0)

        segments, stats = build_fill_network(bounds, domain, "left")

        self.assertTrue(segments)
        self.assertLessEqual(
            stats.maximum_edge_coverage_radius_mm,
            ENVELOPE_LATTICE_EDGE_MAX_COVERAGE_RADIUS_MM,
        )
        self.assertGreaterEqual(
            stats.average_parent_links,
            ENVELOPE_LATTICE_MIN_AVERAGE_PARENT_LINKS,
        )
        self.assertLessEqual(
            stats.underlinked_node_ratio,
            ENVELOPE_LATTICE_MAX_UNDERLINKED_NODE_RATIO,
        )
        self.assertEqual(stats.internal_dead_end_count, 0)
        self.assertEqual(stats.side_clipped_branch_count, 0)

    def test_planform_clearance_grows_inward_from_every_boundary(self) -> None:
        columns = {
            (ix, iy): (-10.0, 10.0)
            for ix in range(5)
            for iy in range(5)
        }
        clearance = _planform_clearance(columns, 1.0)

        self.assertEqual(clearance[(0, 0)], 0.5)
        self.assertGreater(clearance[(2, 2)], clearance[(0, 0)])
        self.assertTrue(math.isfinite(clearance[(2, 2)]))

    def test_a_branch_crossing_a_side_clearance_hole_is_rejected(self) -> None:
        axes = [0.0, 1.0, 2.0, 3.0, 4.0]
        columns = {(ix, iy): (-10.0, 10.0) for ix in range(5) for iy in range(5)}
        clearance = {key: 3.0 for key in columns}
        clearance[(2, 2)] = 0.5
        domain = (axes, axes, columns, clearance)

        path = straight_path((0.0, 2.0, 0.0), (4.0, 2.0, 4.0), 8)
        self.assertFalse(points_clear(path, domain, 1.35))

    def test_branch_surface_clearance_is_measured_and_enforced(self) -> None:
        axes = [0.0, 1.0]
        columns = {(ix, iy): (-1.0, 1.0) for ix in range(2) for iy in range(2)}
        clearances = {key: 1.25 for key in columns}
        domain = (axes, axes, columns, clearances)
        segment = [((0.25, 0.25, 0.0), (0.75, 0.75, 0.5), 1.0)]

        centreline, surface = measure_side_clearance(segment, domain)

        self.assertAlmostEqual(centreline, 1.25)
        self.assertAlmostEqual(surface, 0.25)
        clipped = [((0.25, 0.25, 0.0), (0.75, 0.75, 0.5), 1.01)]
        with self.assertRaises(ValueError):
            measure_side_clearance(clipped, domain)

    def test_separated_vertical_solids_remain_separate(self) -> None:
        """Do not fill the air gap between stacked parts of the input volume."""
        triangles = []
        for z_mm in (0.0, 1.0, 3.0, 4.0):
            triangles.extend(
                [
                    ((0.0, 0.0, z_mm), (1.0, 0.0, z_mm), (1.0, 1.0, z_mm)),
                    ((0.0, 0.0, z_mm), (1.0, 1.0, z_mm), (0.0, 1.0, z_mm)),
                ]
            )
        axes = ([0.25], [0.40], [0.0, 0.5, 1.0, 2.0, 3.0, 3.5, 4.0])

        columns, bands, histogram = rasterize_intervals(axes, triangles)

        self.assertEqual(columns[(0, 0)], ((0.0, 1.0), (3.0, 4.0)))
        self.assertEqual(len(bands), 2)
        self.assertEqual(histogram, {2: 1})
        clearances = [{(0, 0): 1.0}, {(0, 0): 1.0}]
        field = _field(axes, columns, clearances, {}, 0.2)
        self.assertGreater(field[0][0][3], 0.0)


if __name__ == "__main__":
    unittest.main()
