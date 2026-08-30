# sole_ai.mesh: dependency-free binary-STL splitting with planar caps for local baseline output.
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import math
import struct

from .config import (
    MESH_INTERSECTION_EPSILON_MM,
    MESH_VERTEX_QUANTISATION_MM,
    STL_HEADER_BYTES,
    STL_TRIANGLE_BYTES,
)
from .stl import StlValidationError

Point = tuple[float, float, float]
Triangle = tuple[Point, Point, Point]


def read_binary_stl_triangles(path: Path) -> list[Triangle]:
    """Read vertices from one complete binary STL without relying on third-party mesh tools."""
    with path.open("rb") as mesh_file:
        mesh_file.read(80)
        count_data = mesh_file.read(4)
        if len(count_data) != 4:
            raise StlValidationError(f"STL has no triangle count: {path}")
        triangle_count = struct.unpack("<I", count_data)[0]
        if path.stat().st_size != STL_HEADER_BYTES + triangle_count * STL_TRIANGLE_BYTES:
            raise StlValidationError(f"STL size does not match its triangle count: {path}")
        triangle_format = struct.Struct("<12fH")
        triangles: list[Triangle] = []
        for _ in range(triangle_count):
            values = triangle_format.unpack(mesh_file.read(STL_TRIANGLE_BYTES))
            triangles.append((values[3:6], values[6:9], values[9:12]))
    return triangles


def write_binary_stl(path: Path, triangles: list[Triangle], name: str) -> None:
    """Write a binary STL with normals recalculated from the supplied triangle vertices."""
    header = name.encode("ascii", errors="replace")[:80].ljust(80, b" ")
    with path.open("wb") as mesh_file:
        mesh_file.write(header)
        mesh_file.write(struct.pack("<I", len(triangles)))
        triangle_format = struct.Struct("<12fH")
        for triangle in triangles:
            normal = _normal(*triangle)
            mesh_file.write(triangle_format.pack(*normal, *triangle[0], *triangle[1], *triangle[2], 0))


def split_solid_at_z(triangles: list[Triangle], split_z_mm: float) -> tuple[list[Triangle], list[Triangle]]:
    """Split a watertight solid into lower and upper capped STL triangle sets.

    The original triangle orientation is retained. Newly created caps face outward:
    +Z for the lower midsole and -Z for the upper midsole.
    """
    lower: list[Triangle] = []
    upper: list[Triangle] = []
    segments: list[tuple[Point, Point]] = []
    for triangle in triangles:
        lower.extend(_clip_triangle(triangle, split_z_mm, keep_above=False))
        upper.extend(_clip_triangle(triangle, split_z_mm, keep_above=True))
        segment = _intersection_segment(triangle, split_z_mm)
        if segment:
            segments.append(segment)

    loops = _stitch_loops(segments)
    if not loops:
        raise StlValidationError("Split plane does not intersect the source solid.")
    lower.extend(_cap_loops(loops, normal_up=True))
    upper.extend(_cap_loops(loops, normal_up=False))
    return lower, upper


def is_watertight(triangles: list[Triangle]) -> bool:
    """Check whether every quantised undirected edge belongs to exactly two triangles."""
    edges: Counter[tuple[tuple[int, int, int], tuple[int, int, int]]] = Counter()
    for triangle in triangles:
        keys = [_point_key(point) for point in triangle]
        for first, second in zip(keys, keys[1:] + keys[:1]):
            edges[tuple(sorted((first, second)))] += 1
    return bool(edges) and all(count == 2 for count in edges.values())


def _clip_triangle(triangle: Triangle, z: float, keep_above: bool) -> list[Triangle]:
    polygon: list[Point] = []
    previous = triangle[-1]
    previous_inside = _inside(previous, z, keep_above)
    for current in triangle:
        current_inside = _inside(current, z, keep_above)
        if current_inside != previous_inside:
            polygon.append(_plane_intersection(previous, current, z))
        if current_inside:
            polygon.append(current)
        previous = current
        previous_inside = current_inside
    if len(polygon) < 3:
        return []
    return [(polygon[0], polygon[index], polygon[index + 1]) for index in range(1, len(polygon) - 1)]


def _inside(point: Point, z: float, keep_above: bool) -> bool:
    return point[2] >= z - MESH_INTERSECTION_EPSILON_MM if keep_above else point[2] <= z + MESH_INTERSECTION_EPSILON_MM


def _intersection_segment(triangle: Triangle, z: float) -> tuple[Point, Point] | None:
    points: list[Point] = []
    for first, second in zip(triangle, triangle[1:] + triangle[:1]):
        first_distance = first[2] - z
        second_distance = second[2] - z
        if first_distance * second_distance < -(MESH_INTERSECTION_EPSILON_MM ** 2):
            points.append(_plane_intersection(first, second, z))
    unique = { _point_key(point): point for point in points }
    values = list(unique.values())
    return (values[0], values[1]) if len(values) == 2 else None


def _plane_intersection(first: Point, second: Point, z: float) -> Point:
    fraction = (z - first[2]) / (second[2] - first[2])
    return (
        first[0] + (second[0] - first[0]) * fraction,
        first[1] + (second[1] - first[1]) * fraction,
        z,
    )


def _stitch_loops(segments: list[tuple[Point, Point]]) -> list[list[Point]]:
    points: dict[tuple[int, int, int], Point] = {}
    neighbours: dict[tuple[int, int, int], set[tuple[int, int, int]]] = defaultdict(set)
    for first, second in segments:
        first_key, second_key = _point_key(first), _point_key(second)
        if first_key == second_key:
            continue
        points[first_key] = first
        points[second_key] = second
        neighbours[first_key].add(second_key)
        neighbours[second_key].add(first_key)
    if any(len(items) != 2 for items in neighbours.values()):
        raise StlValidationError("Cannot cap a non-manifold split contour.")

    unused = {tuple(sorted((first, second))) for first, values in neighbours.items() for second in values}
    loops: list[list[Point]] = []
    while unused:
        first_edge = next(iter(unused))
        start, current = first_edge
        previous = start
        unused.discard(first_edge)
        loop = [start, current]
        while True:
            choices = neighbours[current] - {previous}
            following = next(iter(choices))
            unused.discard(tuple(sorted((current, following))))
            previous, current = current, following
            if current == start:
                break
            loop.append(current)
            if len(loop) > len(neighbours):
                raise StlValidationError("Could not close the split contour.")
        # Keep intermediate collinear intersections. They preserve the exact edge
        # segmentation of the clipped side faces, which makes the output mesh
        # topologically watertight instead of only visually closed.
        loops.append([points[key] for key in loop])
    return loops


def _cap_loops(loops: list[list[Point]], normal_up: bool) -> list[Triangle]:
    caps: list[Triangle] = []
    for loop in loops:
        for triangle in _ear_clip(loop):
            caps.append(triangle if normal_up else (triangle[0], triangle[2], triangle[1]))
    return caps


def _ear_clip(points: list[Point]) -> list[Triangle]:
    indices = list(range(len(points)))
    if _signed_area(points) < 0.0:
        indices.reverse()
    triangles: list[Triangle] = []
    while len(indices) > 3:
        for index, current in enumerate(indices):
            previous = indices[index - 1]
            following = indices[(index + 1) % len(indices)]
            triangle = (points[previous], points[current], points[following])
            if _cross_2d(*triangle) <= MESH_INTERSECTION_EPSILON_MM:
                continue
            others = (points[item] for item in indices if item not in (previous, current, following))
            if any(_in_triangle(point, triangle) for point in others):
                continue
            triangles.append(triangle)
            indices.pop(index)
            break
        else:
            raise StlValidationError("Cannot triangulate the split contour.")
    triangles.append((points[indices[0]], points[indices[1]], points[indices[2]]))
    return triangles


def _in_triangle(point: Point, triangle: Triangle) -> bool:
    signs = [_cross_2d(triangle[index], triangle[(index + 1) % 3], point) for index in range(3)]
    return min(signs) >= -MESH_INTERSECTION_EPSILON_MM


def _signed_area(points: list[Point]) -> float:
    return sum(first[0] * second[1] - second[0] * first[1] for first, second in zip(points, points[1:] + points[:1])) / 2.0


def _cross_2d(first: Point, second: Point, third: Point) -> float:
    return (second[0] - first[0]) * (third[1] - first[1]) - (second[1] - first[1]) * (third[0] - first[0])


def _point_key(point: Point) -> tuple[int, int, int]:
    return tuple(round(value / MESH_VERTEX_QUANTISATION_MM) for value in point)


def _normal(first: Point, second: Point, third: Point) -> Point:
    left = (second[0] - first[0], second[1] - first[1], second[2] - first[2])
    right = (third[0] - first[0], third[1] - first[1], third[2] - first[2])
    normal = (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )
    magnitude = math.sqrt(sum(value * value for value in normal))
    return tuple(value / magnitude for value in normal) if magnitude else (0.0, 0.0, 0.0)
