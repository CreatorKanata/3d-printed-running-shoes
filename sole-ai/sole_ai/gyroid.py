# sole_ai.gyroid: dependency-free open-sheet Gyroid mesh generation.
"""Generate a closed, crack-free Gyroid box that Fusion trims to the sole."""
from __future__ import annotations

import math
from pathlib import Path
import struct

from .config import GYROID_CELL_SIZE_MM, GYROID_GRID_STEP_MM, GYROID_SHEET_LEVEL, OUTPUT_DIR
from .pipeline import validate_envelope


Point = tuple[float, float, float]
Triangle = tuple[Point, Point, Point]

_CORNERS = (
    (0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),
    (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1),
)
_EDGES = (
    (0, 1), (1, 2), (2, 3), (3, 0),
    (4, 5), (5, 6), (6, 7), (7, 4),
    (0, 4), (1, 5), (2, 6), (3, 7),
)


def _axis_values(minimum: float, maximum: float, step: float) -> list[float]:
    """Return a padded uniform axis so the implicit mesh closes inside the box."""
    start = math.floor(minimum / step) * step - step
    end = math.ceil(maximum / step) * step + step
    count = int(round((end - start) / step)) + 1
    return [start + index * step for index in range(count)]


def _gyroid_value(point: Point, cell_size_mm: float, sheet_level: float) -> float:
    """Negative values are printable material around the Gyroid zero surface."""
    x, y, z = point
    wave = 2.0 * math.pi / cell_size_mm
    gx, gy, gz = wave * x, wave * y, wave * z
    gyroid = (
        math.sin(gx) * math.cos(gy)
        + math.sin(gy) * math.cos(gz)
        + math.sin(gz) * math.cos(gx)
    )
    return abs(gyroid) - sheet_level


def _interpolate(point_a: Point, point_b: Point, value_a: float, value_b: float) -> Point:
    """Linearly locate one implicit zero crossing."""
    fraction = 0.5 if abs(value_a - value_b) < 1e-12 else value_a / (value_a - value_b)
    return tuple(a + (b - a) * fraction for a, b in zip(point_a, point_b))


def _normal(triangle: Triangle) -> Point:
    """Return a unit face normal for orientation and binary STL output."""
    a, b, c = triangle
    ab = tuple(bv - av for av, bv in zip(a, b))
    ac = tuple(cv - av for av, cv in zip(a, c))
    cross = (
        ab[1] * ac[2] - ab[2] * ac[1],
        ab[2] * ac[0] - ab[0] * ac[2],
        ab[0] * ac[1] - ab[1] * ac[0],
    )
    length = math.sqrt(sum(value * value for value in cross))
    return tuple(value / length for value in cross) if length else (0.0, 0.0, 0.0)


def _orient_direction(triangle: Triangle, outside_direction: Point) -> Triangle:
    """Orient one triangle toward the locally positive implicit-field direction."""
    if sum(a * b for a, b in zip(_normal(triangle), outside_direction)) < 0.0:
        return (triangle[0], triangle[2], triangle[1])
    return triangle


def _surface_net_triangles(axes: list[list[float]], values) -> list[Triangle]:
    """Create a shared-vertex Surface Nets mesh with no cube-face diagonal cracks."""
    nx, ny, nz = (len(axis) for axis in axes)
    cell_vertices: dict[tuple[int, int, int], Point] = {}
    for ix in range(nx - 1):
        for iy in range(ny - 1):
            for iz in range(nz - 1):
                points = tuple(
                    (axes[0][ix + dx], axes[1][iy + dy], axes[2][iz + dz])
                    for dx, dy, dz in _CORNERS
                )
                corner_values = tuple(values[ix + dx][iy + dy][iz + dz] for dx, dy, dz in _CORNERS)
                if all(value <= 0.0 for value in corner_values) or all(
                    value > 0.0 for value in corner_values
                ):
                    continue
                crossings = []
                for first, second in _EDGES:
                    if (corner_values[first] <= 0.0) != (corner_values[second] <= 0.0):
                        crossings.append(
                            _interpolate(
                                points[first], points[second], corner_values[first], corner_values[second]
                            )
                        )
                cell_vertices[(ix, iy, iz)] = tuple(
                    sum(point[axis] for point in crossings) / len(crossings) for axis in range(3)
                )

    triangles: list[Triangle] = []

    def add_quad(keys, direction):
        if not all(key in cell_vertices for key in keys):
            return
        a, b, c, d = (cell_vertices[key] for key in keys)
        triangles.append(_orient_direction((a, b, c), direction))
        triangles.append(_orient_direction((a, c, d), direction))

    for ix in range(nx - 1):
        for iy in range(1, ny - 1):
            for iz in range(1, nz - 1):
                first, second = values[ix][iy][iz], values[ix + 1][iy][iz]
                if (first <= 0.0) != (second <= 0.0):
                    sign = 1.0 if second > first else -1.0
                    add_quad(
                        ((ix, iy - 1, iz - 1), (ix, iy, iz - 1),
                         (ix, iy, iz), (ix, iy - 1, iz)),
                        (sign, 0.0, 0.0),
                    )
    for ix in range(1, nx - 1):
        for iy in range(ny - 1):
            for iz in range(1, nz - 1):
                first, second = values[ix][iy][iz], values[ix][iy + 1][iz]
                if (first <= 0.0) != (second <= 0.0):
                    sign = 1.0 if second > first else -1.0
                    add_quad(
                        ((ix - 1, iy, iz - 1), (ix, iy, iz - 1),
                         (ix, iy, iz), (ix - 1, iy, iz)),
                        (0.0, sign, 0.0),
                    )
    for ix in range(1, nx - 1):
        for iy in range(1, ny - 1):
            for iz in range(nz - 1):
                first, second = values[ix][iy][iz], values[ix][iy][iz + 1]
                if (first <= 0.0) != (second <= 0.0):
                    sign = 1.0 if second > first else -1.0
                    add_quad(
                        ((ix - 1, iy - 1, iz), (ix, iy - 1, iz),
                         (ix, iy, iz), (ix - 1, iy, iz)),
                        (0.0, 0.0, sign),
                    )
    return triangles


def _write_binary_stl(path: Path, triangles: list[Triangle]) -> None:
    """Write triangles in the compact binary STL used elsewhere in this project."""
    with path.open("wb") as output:
        output.write(b"Sole AI crack-free Gyroid".ljust(80, b"\0"))
        output.write(struct.pack("<I", len(triangles)))
        for triangle in triangles:
            values = _normal(triangle) + triangle[0] + triangle[1] + triangle[2]
            output.write(struct.pack("<12fH", *values, 0))


def generate_gyroid_box(
    minimum_mm: Point,
    maximum_mm: Point,
    output_path: Path,
    *,
    cell_size_mm: float = GYROID_CELL_SIZE_MM,
    sheet_level: float = GYROID_SHEET_LEVEL,
    grid_step_mm: float = GYROID_GRID_STEP_MM,
) -> int:
    """Sample a padded field and write a closed, shared-vertex Gyroid sheet solid."""
    if cell_size_mm <= 0.0 or grid_step_mm <= 0.0:
        raise ValueError("Gyroid cell size and grid step must be positive.")
    if not 0.0 < sheet_level < 1.0:
        raise ValueError("Gyroid sheet level must be between 0 and 1.")
    axes = [_axis_values(low, high, grid_step_mm) for low, high in zip(minimum_mm, maximum_mm)]
    nx, ny, nz = (len(axis) for axis in axes)
    values = []
    for ix in range(nx):
        x_slice = []
        for iy in range(ny):
            column = []
            for iz in range(nz):
                if ix in (0, nx - 1) or iy in (0, ny - 1) or iz in (0, nz - 1):
                    column.append(1.0)
                else:
                    column.append(
                        _gyroid_value((axes[0][ix], axes[1][iy], axes[2][iz]), cell_size_mm, sheet_level)
                    )
            x_slice.append(column)
        values.append(x_slice)
    triangles = _surface_net_triangles(axes, values)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _write_binary_stl(output_path, triangles)
    return len(triangles)


def generate_side_gyroid(side: str) -> tuple[Path, int]:
    """Generate the untrimmed Gyroid source box for one validated sole side."""
    bounds = validate_envelope(side)
    output_path = OUTPUT_DIR / side / "lattice" / "raw-gyroid.stl"
    triangle_count = generate_gyroid_box(bounds.minimum, bounds.maximum, output_path)
    return output_path, triangle_count
