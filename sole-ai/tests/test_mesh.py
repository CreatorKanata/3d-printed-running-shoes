# tests.test_mesh: regression coverage for closed, locally generated split STL solids.
from __future__ import annotations

import unittest

from sole_ai.mesh import is_watertight, split_solid_at_z


def cube_triangles() -> list[tuple[tuple[float, float, float], ...]]:
    """Return a unit cube as twelve consistently connected surface triangles."""
    vertices = (
        (0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0),
        (0.0, 0.0, 1.0), (1.0, 0.0, 1.0), (1.0, 1.0, 1.0), (0.0, 1.0, 1.0),
    )
    faces = ((0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
             (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7))
    return [tuple(vertices[index] for index in face) for face in faces]


class MeshSplitTests(unittest.TestCase):
    """A horizontal split must create two independently watertight solids."""

    def test_splits_and_caps_a_cube(self) -> None:
        lower, upper = split_solid_at_z(cube_triangles(), 0.5)

        self.assertTrue(is_watertight(lower))
        self.assertTrue(is_watertight(upper))
        self.assertTrue(all(vertex[2] <= 0.5 for triangle in lower for vertex in triangle))
        self.assertTrue(all(vertex[2] >= 0.5 for triangle in upper for vertex in triangle))
