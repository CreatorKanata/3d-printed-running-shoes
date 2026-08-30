# sole_ai.envelope_domain: planform clearance for branch-safe sole volumes.
"""Keep complete branch cross-sections away from every lateral boundary."""
from __future__ import annotations

from collections import Counter
import heapq
import math

from .variable_lattice import _projected_triangles


Point = tuple[float, float, float]
Domain = tuple[
    list[float],
    list[float],
    dict[tuple[int, int], tuple[float, float]],
    dict[tuple[int, int], float],
]


def domain_value(x_mm: float, y_mm: float, domain: Domain, index: int):
    """Read a nearest raster value while tolerating sub-cell branch motion."""
    x_axis, y_axis, columns, clearance = domain
    ix = round((x_mm - x_axis[0]) / (x_axis[1] - x_axis[0]))
    iy = round((y_mm - y_axis[0]) / (y_axis[1] - y_axis[0]))
    source = columns if index == 0 else clearance
    return source.get((ix, iy))


def planform_clearance(columns, step: float) -> dict[tuple[int, int], float]:
    """Measure inward distance from every outer or internal side boundary."""
    distances = {key: math.inf for key in columns}
    queue = []
    neighbours = tuple(
        (dx, dy, step * math.hypot(dx, dy))
        for dx in (-1, 0, 1)
        for dy in (-1, 0, 1)
        if dx or dy
    )
    for key in columns:
        if any(
            (key[0] + dx, key[1] + dy) not in columns
            for dx, dy, _ in neighbours
        ):
            distances[key] = step / 2.0
            heapq.heappush(queue, (step / 2.0, key))
    while queue:
        distance, key = heapq.heappop(queue)
        if distance != distances[key]:
            continue
        for dx, dy, cost in neighbours:
            candidate = (key[0] + dx, key[1] + dy)
            updated = distance + cost
            if candidate in distances and updated < distances[candidate]:
                distances[candidate] = updated
                heapq.heappush(queue, (updated, candidate))
    return distances


def points_clear(points: list[Point], domain: Domain, required: float) -> bool:
    """Require a complete sampled branch path to retain its lateral clearance."""
    return all(
        (clearance := domain_value(point[0], point[1], domain, 1)) is not None
        and clearance >= required
        for point in points
    )


def straight_path(first: Point, second: Point, samples: int) -> list[Point]:
    """Sample a chord for conservative clearance and straight-branch fallback."""
    return [
        tuple(
            start + index / samples * (end - start)
            for start, end in zip(first, second)
        )
        for index in range(samples + 1)
    ]


def _vertical_hits(x_mm: float, y_mm: float, projected) -> list[float]:
    """Return de-duplicated vertical-ray crossings through the source mesh."""
    hits = []
    for triangle, denominator, min_x, max_x, min_y, max_y in projected:
        if not min_x <= x_mm <= max_x or not min_y <= y_mm <= max_y:
            continue
        first, second, third = triangle
        alpha = (
            (second[1] - third[1]) * (x_mm - third[0])
            + (third[0] - second[0]) * (y_mm - third[1])
        ) / denominator
        beta = (
            (third[1] - first[1]) * (x_mm - third[0])
            + (first[0] - third[0]) * (y_mm - third[1])
        ) / denominator
        gamma = 1.0 - alpha - beta
        if min(alpha, beta, gamma) >= -1e-8:
            hits.append(
                alpha * first[2] + beta * second[2] + gamma * third[2]
            )
    unique = []
    for value in sorted(hits):
        if not unique or abs(value - unique[-1]) > 1e-4:
            unique.append(value)
    return unique


def vertical_intervals(x_mm: float, y_mm: float, projected):
    """Pair all vertical crossings, preserving separated solid layers and gaps."""
    offsets = ((0.0, 0.0), (1.1e-5, 1.7e-5), (-1.3e-5, 0.9e-5))
    for dx, dy in offsets:
        hits = _vertical_hits(x_mm + dx, y_mm + dy, projected)
        if len(hits) >= 2 and len(hits) % 2 == 0:
            return tuple(
                (hits[index], hits[index + 1])
                for index in range(0, len(hits), 2)
                if hits[index + 1] - hits[index] > 1e-4
            )
    return ()


def rasterize_intervals(axes, triangles):
    """Rasterize every disjoint vertical solid interval without filling gaps."""
    projected = _projected_triangles(triangles)
    all_columns, bands, histogram = {}, [], Counter()
    for ix, x_mm in enumerate(axes[0]):
        for iy, y_mm in enumerate(axes[1]):
            intervals = vertical_intervals(x_mm, y_mm, projected)
            histogram[len(intervals)] += 1
            if not intervals:
                continue
            all_columns[(ix, iy)] = intervals
            while len(bands) < len(intervals):
                bands.append({})
            for index, interval in enumerate(intervals):
                bands[index][(ix, iy)] = interval
    return all_columns, bands, dict(histogram)
