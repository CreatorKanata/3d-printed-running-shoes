# tests.test_marching_tetra: manifold implicit-mesh regression coverage.
from __future__ import annotations

from collections import Counter
import unittest

from sole_ai.marching_tetra import march_tetrahedra


class MarchingTetraTests(unittest.TestCase):
    """A closed negative voxel must produce only two-face manifold edges."""

    def test_closed_field_is_manifold(self) -> None:
        axes = [[0.0, 1.0, 2.0]] * 3
        field = [
            [
                [-1.0 if (ix, iy, iz) == (1, 1, 1) else 1.0 for iz in range(3)]
                for iy in range(3)
            ]
            for ix in range(3)
        ]
        triangles = march_tetrahedra(axes, field)
        edges = Counter()
        for triangle in triangles:
            for first, second in zip(triangle, triangle[1:] + triangle[:1]):
                edges[tuple(sorted((first, second)))] += 1

        self.assertTrue(triangles)
        self.assertTrue(all(count == 2 for count in edges.values()))
