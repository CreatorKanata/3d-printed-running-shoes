# sole_ai.flash_layout: orient closed lattice meshes for the AD5X build plate.
"""Create deterministic Flash Studio copies without changing engineering STLs."""
from __future__ import annotations

import math


def flash_transform(triangles, bed_size: float, margin: float, *, invert: bool = False):
    """Orient a sole half on its skin and fit it inside the configured bed."""
    oriented = [
        tuple((x, -y, -z) if invert else (x, y, z) for x, y, z in triangle)
        for triangle in triangles
    ]
    stride = max(1, len(oriented) // 6000)
    sample = [vertex for triangle in oriented[::stride] for vertex in triangle]
    best = None
    for degrees in range(91):
        radians = math.radians(degrees)
        cosine, sine = math.cos(radians), math.sin(radians)
        rotated = [(x * cosine - y * sine, x * sine + y * cosine) for x, y, _ in sample]
        width = max(x for x, _ in rotated) - min(x for x, _ in rotated)
        depth = max(y for _, y in rotated) - min(y for _, y in rotated)
        score = max(width, depth)
        if best is None or score < best[0]:
            best = (score, degrees)

    radians = math.radians(best[1])
    cosine, sine = math.cos(radians), math.sin(radians)
    rotated_triangles = [
        tuple((x * cosine - y * sine, x * sine + y * cosine, z) for x, y, z in triangle)
        for triangle in oriented
    ]
    points = [point for triangle in rotated_triangles for point in triangle]
    minima = tuple(min(point[axis] for point in points) for axis in range(3))
    transformed = [
        tuple(
            (
                point[0] - minima[0] + margin,
                point[1] - minima[1] + margin,
                point[2] - minima[2],
            )
            for point in triangle
        )
        for triangle in rotated_triangles
    ]
    final_points = [point for triangle in transformed for point in triangle]
    size = tuple(max(point[axis] for point in final_points) for axis in range(3))
    if size[0] + margin > bed_size or size[1] + margin > bed_size:
        raise ValueError("The generated sole cannot fit the configured Flash Studio bed.")
    return transformed, best[1], size
