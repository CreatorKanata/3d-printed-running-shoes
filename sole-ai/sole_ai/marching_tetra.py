# sole_ai.marching_tetra: conforming implicit-surface polygonisation.
"""Polygonise scalar grids with shared face diagonals for manifold STL output."""
from __future__ import annotations


Point = tuple[float, float, float]
Triangle = tuple[Point, Point, Point]
_ZERO_BIAS = 1e-9

_CORNERS = (
    (0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),
    (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1),
)
# Freudenthal/Kuhn triangulation uses the same diagonal on every shared cube face.
_TETRAHEDRA = (
    (0, 1, 2, 6), (0, 1, 5, 6), (0, 3, 2, 6),
    (0, 3, 7, 6), (0, 4, 5, 6), (0, 4, 7, 6),
)


def _interpolate(first: Point, second: Point, first_value: float, second_value: float) -> Point:
    fraction = 0.5 if abs(first_value - second_value) < 1e-12 else first_value / (
        first_value - second_value
    )
    return tuple(a + (b - a) * fraction for a, b in zip(first, second))


def _tetra_triangles(points, values) -> list[Triangle]:
    """Polygonise one tetrahedron into zero, one, or two consistently joined faces."""
    # A field sample exactly on the isosurface can collapse several adjacent
    # faces onto one point. Classifying zero consistently inside preserves the
    # shared Freudenthal topology and prevents open/non-manifold mesh edges.
    values = tuple(-_ZERO_BIAS if abs(value) < _ZERO_BIAS else value for value in values)
    inside = [index for index, value in enumerate(values) if value <= 0.0]
    outside = [index for index, value in enumerate(values) if value > 0.0]
    if len(inside) in (0, 4):
        return []
    if len(inside) == 1:
        inner = inside[0]
        cuts = [_interpolate(points[inner], points[out], values[inner], values[out]) for out in outside]
        return [(cuts[0], cuts[1], cuts[2])]
    if len(inside) == 3:
        outer = outside[0]
        cuts = [_interpolate(points[outer], points[inner], values[outer], values[inner]) for inner in inside]
        return [(cuts[0], cuts[2], cuts[1])]
    inner_a, inner_b = inside
    outer_a, outer_b = outside
    cut_ac = _interpolate(points[inner_a], points[outer_a], values[inner_a], values[outer_a])
    cut_ad = _interpolate(points[inner_a], points[outer_b], values[inner_a], values[outer_b])
    cut_bc = _interpolate(points[inner_b], points[outer_a], values[inner_b], values[outer_a])
    cut_bd = _interpolate(points[inner_b], points[outer_b], values[inner_b], values[outer_b])
    return [(cut_ac, cut_bc, cut_bd), (cut_ac, cut_bd, cut_ad)]


def march_tetrahedra(axes: list[list[float]], field) -> list[Triangle]:
    """Polygonise one complete scalar grid using a conforming tetrahedralisation."""
    triangles: list[Triangle] = []
    for ix in range(len(axes[0]) - 1):
        for iy in range(len(axes[1]) - 1):
            for iz in range(len(axes[2]) - 1):
                points = tuple(
                    (axes[0][ix + dx], axes[1][iy + dy], axes[2][iz + dz])
                    for dx, dy, dz in _CORNERS
                )
                values = tuple(field[ix + dx][iy + dy][iz + dz] for dx, dy, dz in _CORNERS)
                for tetrahedron in _TETRAHEDRA:
                    triangles.extend(
                        _tetra_triangles(
                            tuple(points[index] for index in tetrahedron),
                            tuple(values[index] for index in tetrahedron),
                        )
                    )
    return triangles
