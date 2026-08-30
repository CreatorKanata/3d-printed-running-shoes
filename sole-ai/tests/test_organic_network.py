# tests.test_organic_network: stochastic cellular-foam regression coverage.
from __future__ import annotations

from collections import Counter
import math
import unittest

from sole_ai.config import (
    FLASH_STUDIO_BED_MARGIN_MM,
    FLASH_STUDIO_BED_SIZE_MM,
    ORGANIC_DESIGN_BRANCH_DIAMETER_MM,
    ORGANIC_MAX_BRANCH_ANGLE_DEG,
    ORGANIC_MAX_BRANCH_DIAMETER_MM,
    ORGANIC_MAX_NODE_SPACING_MM,
    ORGANIC_MAX_PARENT_LINKS,
    ORGANIC_MIN_BRANCH_DIAMETER_MM,
    ORGANIC_MIN_PARENT_LINKS,
)
from sole_ai.organic_network import _branch_angle, build_network
from sole_ai.organic_strut import (
    _clean_triangles,
    _flash_transform,
    _padded_axes,
    _plate_regions,
)
from sole_ai.stl import MeshBounds


class OrganicNetworkTests(unittest.TestCase):
    """Cellular output must stay dense, non-periodic, printable, and graded."""

    def setUp(self) -> None:
        self.bounds = MeshBounds((-45.0, -120.0, -30.0), (45.0, 120.0, 0.0), 0)
        self.plate = ((100.0, -16.0), (50.0, -18.0), (0.0, -19.0), (-50.0, -16.0), (-100.0, -10.0))

    def test_cells_have_no_dominant_grid_directions(self) -> None:
        segments = build_network(self.bounds, self.plate, "lower")
        directions = []
        for first, second, _ in segments:
            length = math.dist(first, second)
            directions.append(
                tuple(round(abs((second[axis] - first[axis]) / length), 1) for axis in range(3))
            )
        histogram = Counter(directions)

        self.assertGreater(len(histogram), 50)
        self.assertLess(histogram.most_common(1)[0][1] / len(directions), 0.08)

    def test_cellular_network_is_dense_without_large_branch_gaps(self) -> None:
        segments = build_network(self.bounds, self.plate, "lower")

        self.assertGreater(len(segments), 30_000)
        self.assertLessEqual(
            max(math.dist(first, second) for first, second, _ in segments),
            ORGANIC_MAX_NODE_SPACING_MM * 1.10,
        )

    def test_every_branch_is_supported_in_each_halfs_build_direction(self) -> None:
        for half, build_sign in (("lower", 1.0), ("upper", -1.0)):
            segments = build_network(self.bounds, self.plate, half)

            self.assertTrue(segments)
            self.assertTrue(
                all((second[2] - first[2]) * build_sign > 0.0 for first, second, _ in segments)
            )
            self.assertLessEqual(
                max(_branch_angle(first, second) for first, second, _ in segments),
                ORGANIC_MAX_BRANCH_ANGLE_DEG + 1e-7,
            )

    def test_branch_floor_exceeds_requested_minimum(self) -> None:
        segments = build_network(self.bounds, self.plate, "upper")

        self.assertGreaterEqual(ORGANIC_DESIGN_BRANCH_DIAMETER_MM, ORGANIC_MIN_BRANCH_DIAMETER_MM)
        self.assertGreaterEqual(min(radius * 2.0 for _, _, radius in segments), ORGANIC_MIN_BRANCH_DIAMETER_MM)
        self.assertLessEqual(max(radius * 2.0 for _, _, radius in segments), 1.8)
        self.assertLessEqual(ORGANIC_MAX_BRANCH_DIAMETER_MM, 1.8)

    def test_dense_network_uses_redundant_parent_links(self) -> None:
        self.assertGreaterEqual(ORGANIC_MIN_PARENT_LINKS, 3)
        self.assertGreaterEqual(ORGANIC_MAX_PARENT_LINKS, ORGANIC_MIN_PARENT_LINKS)

    def test_plate_faces_and_sidewall_are_supported(self) -> None:
        local_width = (-40.0, 40.0)

        pocket, lower_support = _plate_regions(0.0, 0.0, -1.0, 0.0, local_width, self.plate, "lower")
        _, upper_support = _plate_regions(0.0, 0.0, 1.0, 0.0, local_width, self.plate, "upper")
        _, side_support = _plate_regions(33.0, 0.0, 0.0, 0.0, local_width, self.plate, "lower")

        self.assertFalse(pocket)
        self.assertTrue(lower_support)
        self.assertTrue(upper_support)
        self.assertTrue(side_support)

    def test_flash_copy_is_positive_and_inside_bed(self) -> None:
        triangles = [
            ((-35.0, -110.0, -20.0), (35.0, -110.0, -20.0), (35.0, 110.0, 0.0)),
            ((-35.0, -110.0, -20.0), (35.0, 110.0, 0.0), (-35.0, 110.0, 0.0)),
        ]

        transformed, _, size = _flash_transform(triangles, 220.0, 5.0)
        points = [point for triangle in transformed for point in triangle]

        self.assertGreaterEqual(min(point[0] for point in points), 5.0)
        self.assertGreaterEqual(min(point[1] for point in points), 5.0)
        self.assertEqual(min(point[2] for point in points), 0.0)
        self.assertLessEqual(size[0], 215.0)
        self.assertLessEqual(size[1], 215.0)

        inverted, _, _ = _flash_transform(triangles, 220.0, 5.0, invert=True)
        self.assertEqual(min(point[2] for triangle in inverted for point in triangle), 0.0)
        self.assertGreater(FLASH_STUDIO_BED_SIZE_MM, 2.0 * FLASH_STUDIO_BED_MARGIN_MM)

    def test_mesh_cleanup_removes_degenerate_and_duplicate_faces(self) -> None:
        valid = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0))
        collapsed = ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 1.0, 0.0))

        self.assertEqual(_clean_triangles([valid, valid, collapsed]), [valid])

    def test_scalar_domain_has_a_positive_field_padding_cell(self) -> None:
        axes = _padded_axes(self.bounds, 0.5)

        for axis, values in enumerate(axes):
            self.assertLessEqual(values[0], self.bounds.minimum[axis] - 0.5)
            self.assertGreaterEqual(values[-1], self.bounds.maximum[axis] + 0.5)
