# sole_ai.organic_network: support-free stochastic cellular topology for FFF TPU.
"""Build curved non-periodic cells whose branches follow the local build direction."""
from __future__ import annotations

from collections import defaultdict
import math
import random

from .config import (
    GROUND_SKIN_THICKNESS_MM,
    ORGANIC_CELL_SIZE_MM,
    ORGANIC_CURVE_RATIO,
    ORGANIC_CURVE_SAMPLES,
    ORGANIC_DESIGN_BRANCH_DIAMETER_MM,
    ORGANIC_GROWTH_SEED,
    ORGANIC_LAYER_HEIGHT_MM,
    ORGANIC_LAYER_JITTER_MM,
    ORGANIC_MAX_BRANCH_ANGLE_DEG,
    ORGANIC_MAX_BRANCH_DIAMETER_MM,
    ORGANIC_MAX_LATERAL_SHIFT_MM,
    ORGANIC_MAX_NODE_SPACING_MM,
    ORGANIC_MAX_PARENT_LINKS,
    ORGANIC_MIN_NODE_SPACING_MM,
    ORGANIC_MIN_LATERAL_SHIFT_MM,
    ORGANIC_MIN_PARENT_LINKS,
    ORGANIC_NODE_FACTOR,
    PLATE_CRADLE_THICKNESS_MM,
    PLATE_POCKET_CLEARANCE_MM,
    PLATE_THICKNESS_MM,
    TOP_SKIN_THICKNESS_MM,
)
from .variable_lattice import _interpolate_path, relative_density


Point = tuple[float, float, float]
Segment = tuple[Point, Point, float]
Domain = tuple[list[float], list[float], dict[tuple[int, int], tuple[float, float]]]


def _density_fraction(point: Point, bounds, plate_points) -> float:
    """Normalize the smooth biomechanical load field to zero through one."""
    x_mm, y_mm, z_mm = point
    longitudinal = (bounds.maximum[1] - y_mm) / bounds.dimensions[1]
    middle_x = (bounds.minimum[0] + bounds.maximum[0]) / 2.0
    transverse = 2.0 * (x_mm - middle_x) / bounds.dimensions[0]
    density = relative_density(
        max(0.0, min(1.0, longitudinal)),
        max(-1.0, min(1.0, transverse)),
        z_mm - _interpolate_path(y_mm, plate_points),
    )
    return max(0.0, min(1.0, (density - 0.18) / (0.55 - 0.18)))


def _local_spacing(point: Point, bounds, plate_points, terminal: bool) -> float:
    """Shrink cells smoothly on load paths and beside the plate support roof."""
    blend = _density_fraction(point, bounds, plate_points)
    spacing = ORGANIC_MAX_NODE_SPACING_MM - blend * (
        ORGANIC_MAX_NODE_SPACING_MM - ORGANIC_MIN_NODE_SPACING_MM
    )
    return spacing * (0.68 if terminal else 1.0)


def _radius(point: Point, bounds, plate_points) -> float:
    """Thicken branches continuously along inferred load-bearing paths."""
    minimum = ORGANIC_DESIGN_BRANCH_DIAMETER_MM / 2.0
    maximum = ORGANIC_MAX_BRANCH_DIAMETER_MM / 2.0
    return minimum + _density_fraction(point, bounds, plate_points) * (maximum - minimum)


def _domain_limits(x_mm: float, y_mm: float, bounds, domain: Domain | None):
    """Return local sole surfaces from the rasterized source envelope."""
    if domain is None:
        return bounds.minimum[2], bounds.maximum[2]
    x_axis, y_axis, columns = domain
    x_step = x_axis[1] - x_axis[0]
    y_step = y_axis[1] - y_axis[0]
    ix = round((x_mm - x_axis[0]) / x_step)
    iy = round((y_mm - y_axis[0]) / y_step)
    for radius in range(3):
        candidates = [
            (dx * dx + dy * dy, columns[(ix + dx, iy + dy)])
            for dx in range(-radius, radius + 1)
            for dy in range(-radius, radius + 1)
            if (ix + dx, iy + dy) in columns
        ]
        if candidates:
            return min(candidates, key=lambda item: item[0])[1]
    return None


def _point_at(x_mm, y_mm, fraction, bounds, plate_points, half, domain, jitter=0.0) -> Point | None:
    """Map an XY point to a curved build layer between a solid skin and plate."""
    limits = _domain_limits(x_mm, y_mm, bounds, domain)
    if limits is None:
        return None
    low_z, high_z = limits
    split = max(low_z, min(high_z, _interpolate_path(y_mm, plate_points)))
    pocket_half = PLATE_THICKNESS_MM / 2.0 + PLATE_POCKET_CLEARANCE_MM
    if half == "lower":
        start = low_z + GROUND_SKIN_THICKNESS_MM * 0.55
        end = split - pocket_half - PLATE_CRADLE_THICKNESS_MM * 0.55
    else:
        start = high_z - TOP_SKIN_THICKNESS_MM * 0.55
        end = split + pocket_half + PLATE_CRADLE_THICKNESS_MM * 0.55
    if (end - start) * (1.0 if half == "lower" else -1.0) <= 2.0:
        return None
    z_mm = start + fraction * (end - start) + jitter
    return x_mm, y_mm, max(min(start, end), min(max(start, end), z_mm))


def _clear(candidate, nodes, bins, spacing, bin_size) -> bool:
    """Check a 2D Poisson-disc neighbourhood without quadratic global scans."""
    key = (math.floor(candidate[0] / bin_size), math.floor(candidate[1] / bin_size))
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for index in bins.get((key[0] + dx, key[1] + dy), ()):
                if math.dist(candidate[:2], nodes[index][:2]) < spacing:
                    return False
    return True


def _base_layer(rng, bounds, plate_points, half, domain) -> list[Point]:
    """Fill the first solid-skin layer with irregular, well-spaced roots."""
    area = bounds.dimensions[0] * bounds.dimensions[1]
    target = round(area / ORGANIC_CELL_SIZE_MM**2 * ORGANIC_NODE_FACTOR)
    nodes: list[Point] = []
    bins: dict[tuple[int, int], list[int]] = defaultdict(list)
    attempts = 0
    while len(nodes) < target and attempts < target * 100:
        x_mm = rng.uniform(bounds.minimum[0], bounds.maximum[0])
        y_mm = rng.uniform(bounds.minimum[1], bounds.maximum[1])
        candidate = _point_at(x_mm, y_mm, 0.0, bounds, plate_points, half, domain)
        if candidate is not None:
            spacing = 0.82 * _local_spacing(candidate, bounds, plate_points, False)
            if _clear(candidate, nodes, bins, spacing, ORGANIC_MAX_NODE_SPACING_MM):
                key = (math.floor(x_mm / ORGANIC_MAX_NODE_SPACING_MM), math.floor(y_mm / ORGANIC_MAX_NODE_SPACING_MM))
                bins[key].append(len(nodes))
                nodes.append(candidate)
        attempts += 1
    return nodes


def _next_layer(rng, previous, fraction, bounds, plate_points, half, domain) -> list[Point]:
    """Grow a supported irregular node layer from the preceding build layer."""
    terminal = fraction > 0.999
    multiplier = 1.55 if terminal else 1.08
    target = max(len(previous), round(len(previous) * multiplier))
    nodes: list[Point] = []
    bins: dict[tuple[int, int], list[int]] = defaultdict(list)
    attempts = 0
    while len(nodes) < target and attempts < target * 120:
        parent = rng.choice(previous)
        angle = rng.uniform(0.0, 2.0 * math.pi)
        radial = rng.uniform(ORGANIC_MIN_LATERAL_SHIFT_MM, ORGANIC_MAX_LATERAL_SHIFT_MM)
        x_mm = parent[0] + radial * math.cos(angle)
        y_mm = parent[1] + radial * math.sin(angle)
        jitter = 0.0 if terminal else rng.uniform(-ORGANIC_LAYER_JITTER_MM, ORGANIC_LAYER_JITTER_MM)
        candidate = _point_at(x_mm, y_mm, fraction, bounds, plate_points, half, domain, jitter)
        if candidate is not None and _branch_angle(parent, candidate) <= ORGANIC_MAX_BRANCH_ANGLE_DEG:
            spacing = 0.80 * _local_spacing(candidate, bounds, plate_points, terminal)
            if _clear(candidate, nodes, bins, spacing, ORGANIC_MAX_NODE_SPACING_MM):
                key = (math.floor(x_mm / ORGANIC_MAX_NODE_SPACING_MM), math.floor(y_mm / ORGANIC_MAX_NODE_SPACING_MM))
                bins[key].append(len(nodes))
                nodes.append(candidate)
        attempts += 1
    return nodes


def _branch_angle(first: Point, second: Point) -> float:
    """Measure a member angle from the build direction, where vertical is zero."""
    vertical = abs(second[2] - first[2])
    horizontal = math.dist(first[:2], second[:2])
    return math.degrees(math.atan2(horizontal, vertical))


def _layer_edges(rng, previous, current) -> set[tuple[int, int]]:
    """Give each new node three or four printable parents for dense load sharing."""
    edges = set()
    for child_index, child in enumerate(current):
        candidates = sorted(
            (math.dist(parent, child), parent_index)
            for parent_index, parent in enumerate(previous)
            if _branch_angle(parent, child) <= ORGANIC_MAX_BRANCH_ANGLE_DEG
        )
        parent_count = (
            ORGANIC_MIN_PARENT_LINKS
            if rng.random() < 0.55
            else ORGANIC_MAX_PARENT_LINKS
        )
        for _, parent_index in candidates[:parent_count]:
            edges.add((parent_index, child_index))
    return edges


def _unit_xy(vector: Point) -> tuple[float, float]:
    """Return an XY perpendicular used to give straight members a soft bow."""
    length = math.hypot(vector[0], vector[1])
    return (-vector[1] / length, vector[0] / length) if length > 1e-9 else (1.0, 0.0)


def _curved_points(rng, first: Point, second: Point) -> list[Point]:
    """Sample a monotonic quadratic Bezier and preserve the FFF angle limit."""
    direction = tuple(b - a for a, b in zip(first, second))
    perpendicular = _unit_xy(direction)
    horizontal = math.hypot(direction[0], direction[1])
    curve_room = 0.45 * math.sqrt(max(0.0, direction[2] ** 2 - horizontal**2))
    offset = min(abs(direction[2]) * ORGANIC_CURVE_RATIO, curve_room) * rng.uniform(-1.0, 1.0)
    midpoint = tuple((a + b) / 2.0 for a, b in zip(first, second))
    control = (midpoint[0] + 2.0 * offset * perpendicular[0], midpoint[1] + 2.0 * offset * perpendicular[1], midpoint[2])
    points = []
    for sample in range(ORGANIC_CURVE_SAMPLES + 1):
        parameter = sample / ORGANIC_CURVE_SAMPLES
        inverse = 1.0 - parameter
        points.append(tuple(inverse * inverse * first[axis] + 2.0 * inverse * parameter * control[axis] + parameter * parameter * second[axis] for axis in range(3)))
    if max(_branch_angle(a, b) for a, b in zip(points, points[1:])) > ORGANIC_MAX_BRANCH_ANGLE_DEG:
        return [tuple(a + sample / ORGANIC_CURVE_SAMPLES * (b - a) for a, b in zip(first, second)) for sample in range(ORGANIC_CURVE_SAMPLES + 1)]
    return points


def build_network(bounds, plate_points, half: str, domain: Domain | None = None) -> list[Segment]:
    """Build a support-free, connected-to-skins, non-periodic FFF cell network."""
    side_seed = round(sum(bounds.minimum + bounds.maximum) * 1000)
    rng = random.Random(ORGANIC_GROWTH_SEED ^ side_seed ^ (0 if half == "lower" else 0x5A5A))
    layer_count = max(4, math.ceil(bounds.dimensions[2] / 2.0 / ORGANIC_LAYER_HEIGHT_MM) + 1)
    layers = [_base_layer(rng, bounds, plate_points, half, domain)]
    for index in range(1, layer_count):
        layers.append(_next_layer(rng, layers[-1], index / (layer_count - 1), bounds, plate_points, half, domain))
    segments: list[Segment] = []
    for previous, current in zip(layers, layers[1:]):
        for parent_index, child_index in _layer_edges(rng, previous, current):
            curve = _curved_points(rng, previous[parent_index], current[child_index])
            middle = curve[len(curve) // 2]
            radius = _radius(middle, bounds, plate_points)
            segments.extend((curve[index], curve[index + 1], radius) for index in range(len(curve) - 1))
    return segments
