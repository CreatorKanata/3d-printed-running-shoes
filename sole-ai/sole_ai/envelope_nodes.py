# sole_ai.envelope_nodes: coverage-guaranteed nodes for designer-volume lattices.
"""Fill every build layer densely, with an extra reinforced perimeter band."""
from __future__ import annotations

from collections import defaultdict
import math

from .config import (
    ENVELOPE_LATTICE_ANCHOR_SKIN_MM,
    ENVELOPE_LATTICE_CELL_SIZE_MM,
    ENVELOPE_LATTICE_CURVE_SAMPLES,
    ENVELOPE_LATTICE_DIAMETER_LOAD_FLOOR,
    ENVELOPE_LATTICE_EDGE_BAND_MM,
    ENVELOPE_LATTICE_EDGE_COVERAGE_TARGET_RADIUS_MM,
    ENVELOPE_LATTICE_EDGE_DIAMETER_GAIN,
    ENVELOPE_LATTICE_EDGE_NODE_SPACING_MM,
    ENVELOPE_LATTICE_INTERIOR_MAX_COVERAGE_RADIUS_MM,
    ENVELOPE_LATTICE_LAYER_HEIGHT_MM,
    ENVELOPE_LATTICE_LAYER_JITTER_MM,
    ENVELOPE_LATTICE_MAX_BRANCH_ANGLE_DEG,
    ENVELOPE_LATTICE_MAX_BRANCH_DIAMETER_MM,
    ENVELOPE_LATTICE_MAX_NODE_SPACING_MM,
    ENVELOPE_LATTICE_MIN_BRANCH_DIAMETER_MM,
    ENVELOPE_LATTICE_MIN_NODE_SPACING_MM,
    ENVELOPE_LATTICE_NODE_FACTOR,
    ENVELOPE_LATTICE_SIDE_CLEARANCE_MM,
    ENVELOPE_LATTICE_THIN_SOLID_THRESHOLD_MM,
)
from .envelope_density import load_fraction
from .envelope_domain import Domain, domain_value, points_clear, straight_path


Point = tuple[float, float, float]


def branch_angle(first: Point, second: Point) -> float:
    """Measure a branch angle from the vertical build direction."""
    horizontal = math.dist(first[:2], second[:2])
    vertical = abs(second[2] - first[2])
    return math.degrees(math.atan2(horizontal, vertical))


def _required_clearance() -> float:
    return (
        ENVELOPE_LATTICE_MAX_BRANCH_DIAMETER_MM / 2.0
        + ENVELOPE_LATTICE_SIDE_CLEARANCE_MM
    )


def _edge_fraction(point: Point, domain: Domain) -> float:
    clearance = domain_value(point[0], point[1], domain, 1)
    if clearance is None:
        return 0.0
    inward = max(0.0, clearance - _required_clearance())
    return max(0.0, 1.0 - inward / ENVELOPE_LATTICE_EDGE_BAND_MM)


def node_spacing(point: Point, bounds, domain: Domain) -> float:
    """Use small cells throughout and the smallest cells around the perimeter."""
    blend = load_fraction(point, bounds)
    interior = ENVELOPE_LATTICE_MAX_NODE_SPACING_MM - blend * (
        ENVELOPE_LATTICE_MAX_NODE_SPACING_MM
        - ENVELOPE_LATTICE_MIN_NODE_SPACING_MM
    )
    edge = _edge_fraction(point, domain)
    return interior * (1.0 - edge) + ENVELOPE_LATTICE_EDGE_NODE_SPACING_MM * edge


def node_radius(point: Point, bounds, domain: Domain) -> float:
    """Grade branches from 1.5 to 2.0 mm without solidifying the perimeter."""
    raw_load = load_fraction(point, bounds)
    graded_load = max(
        0.0,
        min(
            1.0,
            (raw_load - ENVELOPE_LATTICE_DIAMETER_LOAD_FLOOR)
            / (1.0 - ENVELOPE_LATTICE_DIAMETER_LOAD_FLOOR),
        ),
    )
    edge_reinforcement = (
        ENVELOPE_LATTICE_EDGE_DIAMETER_GAIN * _edge_fraction(point, domain)
    )
    blend = max(graded_load, edge_reinforcement)
    diameter = ENVELOPE_LATTICE_MIN_BRANCH_DIAMETER_MM + blend * (
        ENVELOPE_LATTICE_MAX_BRANCH_DIAMETER_MM
        - ENVELOPE_LATTICE_MIN_BRANCH_DIAMETER_MM
    )
    return diameter / 2.0


def point_at(x_mm, y_mm, fraction, bounds, domain, jitter=0.0) -> Point | None:
    """Map a plan point into one local bottom-to-top solid interval."""
    limits = domain_value(x_mm, y_mm, domain, 0)
    clearance = domain_value(x_mm, y_mm, domain, 1)
    if limits is None or clearance is None or clearance < _required_clearance():
        return None
    low_z, high_z = limits
    if high_z - low_z <= ENVELOPE_LATTICE_THIN_SOLID_THRESHOLD_MM:
        return None
    start = low_z + ENVELOPE_LATTICE_ANCHOR_SKIN_MM * 0.55
    end = high_z - ENVELOPE_LATTICE_ANCHOR_SKIN_MM * 0.55
    if end - start <= 2.0 * ENVELOPE_LATTICE_MAX_BRANCH_DIAMETER_MM:
        return None
    z_mm = start + fraction * (end - start) + jitter
    return x_mm, y_mm, max(start, min(end, z_mm))


def local_layer_count(domain: Domain) -> int:
    """Derive layers from this band's real thickness, not the full 40 mm sole."""
    values = sorted(
        high_z - low_z - 1.1 * ENVELOPE_LATTICE_ANCHOR_SKIN_MM
        for low_z, high_z in domain[2].values()
        if high_z - low_z
        > 2.0 * ENVELOPE_LATTICE_MAX_BRANCH_DIAMETER_MM
        + 1.1 * ENVELOPE_LATTICE_ANCHOR_SKIN_MM
    )
    if not values:
        return 0
    thickness = values[round(0.50 * (len(values) - 1))]
    return max(2, round(thickness / ENVELOPE_LATTICE_LAYER_HEIGHT_MM))


def _bin_key(point: Point) -> tuple[int, int]:
    size = ENVELOPE_LATTICE_MAX_NODE_SPACING_MM
    return math.floor(point[0] / size), math.floor(point[1] / size)


def _append(node, nodes, bins) -> None:
    bins[_bin_key(node)].append(len(nodes))
    nodes.append(node)


def _nearest(candidate, nodes, bins) -> tuple[float, int | None]:
    key = _bin_key(candidate)
    best, best_index = math.inf, None
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for index in bins.get((key[0] + dx, key[1] + dy), ()):
                distance = math.dist(candidate[:2], nodes[index][:2])
                if distance < best:
                    best, best_index = distance, index
    return best, best_index


def _clear(candidate, nodes, bins, spacing) -> bool:
    return _nearest(candidate, nodes, bins)[0] >= spacing


def _coverage_limit(point: Point, domain: Domain) -> float:
    clearance = domain_value(point[0], point[1], domain, 1)
    if clearance is not None and clearance <= (
        _required_clearance() + ENVELOPE_LATTICE_EDGE_BAND_MM
    ):
        return ENVELOPE_LATTICE_EDGE_COVERAGE_TARGET_RADIUS_MM
    return ENVELOPE_LATTICE_INTERIOR_MAX_COVERAGE_RADIUS_MM


def _valid_parent(candidate, previous, domain) -> int | None:
    ordered = sorted(
        (math.dist(parent, candidate), index)
        for index, parent in enumerate(previous)
        if branch_angle(parent, candidate) <= ENVELOPE_LATTICE_MAX_BRANCH_ANGLE_DEG
    )
    for _, index in ordered:
        path = straight_path(previous[index], candidate, ENVELOPE_LATTICE_CURVE_SAMPLES)
        if points_clear(path, domain, _required_clearance()):
            return index
    return None


def _repair_coverage(
    rng,
    nodes,
    bins,
    fraction,
    bounds,
    domain,
    primary=None,
    previous=None,
):
    """Add nodes until every eligible grid column is within its pore-radius cap."""
    keys = list(domain[2])
    rng.shuffle(keys)
    for ix, iy in keys:
        candidate = point_at(domain[0][ix], domain[1][iy], fraction, bounds, domain)
        if candidate is None or _nearest(candidate, nodes, bins)[0] <= (
            _coverage_limit(candidate, domain)
        ):
            continue
        parent = None if previous is None else _valid_parent(candidate, previous, domain)
        if previous is not None and parent is None:
            continue
        _append(candidate, nodes, bins)
        if primary is not None:
            primary.append(parent)


def coverage_radii(nodes, fraction, bounds, domain) -> tuple[float, float]:
    """Measure the largest overall and reinforced-edge plan-view void radii."""
    bins = defaultdict(list)
    for index, node in enumerate(nodes):
        bins[_bin_key(node)].append(index)
    maximum = edge_maximum = 0.0
    for ix, iy in domain[2]:
        point = point_at(domain[0][ix], domain[1][iy], fraction, bounds, domain)
        if point is None:
            continue
        distance, _ = _nearest(point, nodes, bins)
        maximum = max(maximum, distance)
        if _coverage_limit(point, domain) == (
            ENVELOPE_LATTICE_EDGE_COVERAGE_TARGET_RADIUS_MM
        ):
            edge_maximum = max(edge_maximum, distance)
    return maximum, edge_maximum


def base_layer(rng, bounds, domain):
    """Create organic roots, then deterministically repair every sparse region."""
    step_x = domain[0][1] - domain[0][0]
    step_y = domain[1][1] - domain[1][0]
    sampled_area = len(domain[2]) * step_x * step_y
    target = round(
        sampled_area / ENVELOPE_LATTICE_CELL_SIZE_MM**2
        * ENVELOPE_LATTICE_NODE_FACTOR
    )
    nodes, bins, attempts = [], defaultdict(list), 0
    while len(nodes) < target and attempts < target * 160:
        node = point_at(
            rng.uniform(bounds.minimum[0], bounds.maximum[0]),
            rng.uniform(bounds.minimum[1], bounds.maximum[1]),
            0.0,
            bounds,
            domain,
        )
        if node is not None and _clear(
            node,
            nodes,
            bins,
            0.80 * node_spacing(node, bounds, domain),
        ):
            _append(node, nodes, bins)
        attempts += 1
    _repair_coverage(rng, nodes, bins, 0.0, bounds, domain)
    return nodes, coverage_radii(nodes, 0.0, bounds, domain)


def next_layer(rng, previous, fraction, bounds, domain):
    """Colonize independent attractors so branches naturally split and merge."""
    nodes, bins, primary = [], defaultdict(list), []
    step_x = domain[0][1] - domain[0][0]
    step_y = domain[1][1] - domain[1][0]
    sampled_area = len(domain[2]) * step_x * step_y
    target = round(
        sampled_area / ENVELOPE_LATTICE_CELL_SIZE_MM**2
        * ENVELOPE_LATTICE_NODE_FACTOR
    )
    attempts = 0
    while len(nodes) < target and attempts < target * 180:
        candidate = point_at(
            rng.uniform(bounds.minimum[0], bounds.maximum[0]),
            rng.uniform(bounds.minimum[1], bounds.maximum[1]),
            fraction,
            bounds,
            domain,
            rng.uniform(
                -ENVELOPE_LATTICE_LAYER_JITTER_MM,
                ENVELOPE_LATTICE_LAYER_JITTER_MM,
            ),
        )
        parent = (
            None if candidate is None else _valid_parent(candidate, previous, domain)
        )
        if (
            candidate is not None
            and parent is not None
            and _clear(
                candidate,
                nodes,
                bins,
                0.78 * node_spacing(candidate, bounds, domain),
            )
        ):
            _append(candidate, nodes, bins)
            primary.append(parent)
        attempts += 1
    _repair_coverage(rng, nodes, bins, fraction, bounds, domain, primary, previous)
    for parent_index, parent in enumerate(previous):
        if any(_valid_parent(node, [parent], domain) == 0 for node in nodes):
            continue
        rescue = point_at(parent[0], parent[1], fraction, bounds, domain)
        if rescue is not None:
            _append(rescue, nodes, bins)
            primary.append(parent_index)
    if not nodes:
        raise ValueError("No biological attractor could reach the next build layer.")
    return nodes, primary, coverage_radii(nodes, fraction, bounds, domain)
