# sole_ai.envelope_network: continuous organic branch graph for a full sole volume.
"""Grow dense curved branches with no unanchored internal tips."""
from __future__ import annotations

from dataclasses import dataclass
import math
import random

from .config import (
    ENVELOPE_LATTICE_CURVE_RATIO,
    ENVELOPE_LATTICE_CURVE_SAMPLES,
    ENVELOPE_LATTICE_EDGE_MAX_COVERAGE_RADIUS_MM,
    ENVELOPE_LATTICE_INTERIOR_MAX_COVERAGE_RADIUS_MM,
    ENVELOPE_LATTICE_MAX_BRANCH_ANGLE_DEG,
    ENVELOPE_LATTICE_MAX_PARENT_LINKS,
    ENVELOPE_LATTICE_MAX_UNDERLINKED_NODE_RATIO,
    ENVELOPE_LATTICE_MIN_AVERAGE_PARENT_LINKS,
    ENVELOPE_LATTICE_MIN_EFFECTIVE_PARENT_LINKS,
    ENVELOPE_LATTICE_MIN_PARENT_LINKS,
    ENVELOPE_LATTICE_SIDE_CLEARANCE_MM,
    ORGANIC_GROWTH_SEED,
)
from .envelope_density import load_fraction
from .envelope_domain import (
    Domain,
    domain_value,
    points_clear,
    straight_path,
)
from .envelope_nodes import (
    base_layer,
    branch_angle,
    local_layer_count,
    next_layer,
    node_radius,
)


Point = tuple[float, float, float]
Segment = tuple[Point, Point, float]


@dataclass(frozen=True)
class NetworkStats:
    """Small reproducibility record for one generated branch graph."""

    layer_count: int
    node_count: int
    branch_count: int
    internal_dead_end_count: int
    side_clipped_branch_count: int
    maximum_coverage_radius_mm: float
    maximum_edge_coverage_radius_mm: float
    minimum_parent_links: int
    underlinked_node_count: int
    average_parent_links: float
    underlinked_node_ratio: float


def _curved_points(rng, first: Point, second: Point) -> list[Point]:
    """Sample one softly bowed quadratic Bezier branch."""
    direction = tuple(b - a for a, b in zip(first, second))
    length = math.hypot(direction[0], direction[1])
    perpendicular = (
        (-direction[1] / length, direction[0] / length)
        if length > 1e-9
        else (1.0, 0.0)
    )
    midpoint = tuple((a + b) / 2.0 for a, b in zip(first, second))
    offset = (
        abs(direction[2])
        * ENVELOPE_LATTICE_CURVE_RATIO
        * rng.uniform(-1.0, 1.0)
    )
    control = (
        midpoint[0] + offset * perpendicular[0],
        midpoint[1] + offset * perpendicular[1],
        midpoint[2],
    )
    points = []
    for sample in range(ENVELOPE_LATTICE_CURVE_SAMPLES + 1):
        parameter = sample / ENVELOPE_LATTICE_CURVE_SAMPLES
        inverse = 1.0 - parameter
        points.append(
            tuple(
                inverse**2 * first[axis]
                + 2.0 * inverse * parameter * control[axis]
                + parameter**2 * second[axis]
                for axis in range(3)
            )
        )
    if max(
        branch_angle(a, b) for a, b in zip(points, points[1:])
    ) > ENVELOPE_LATTICE_MAX_BRANCH_ANGLE_DEG:
        return [
            tuple(
                a
                + sample / ENVELOPE_LATTICE_CURVE_SAMPLES * (b - a)
                for a, b in zip(first, second)
            )
            for sample in range(ENVELOPE_LATTICE_CURVE_SAMPLES + 1)
        ]
    return points


def _connection_segments(rng, first, second, bounds, domain) -> list[Segment]:
    """Create one tapered organic branch, falling back to its printable chord."""
    curve = _curved_points(rng, first, second)
    radii = [
        node_radius(
            tuple((a + b) / 2.0 for a, b in zip(start, end)),
            bounds,
            domain,
        )
        for start, end in zip(curve, curve[1:])
    ]
    required = max(radii) + ENVELOPE_LATTICE_SIDE_CLEARANCE_MM
    if not points_clear(curve, domain, required):
        curve = straight_path(first, second, ENVELOPE_LATTICE_CURVE_SAMPLES)
        radii = [
            node_radius(
                tuple((a + b) / 2.0 for a, b in zip(start, end)),
                bounds,
                domain,
            )
            for start, end in zip(curve, curve[1:])
        ]
        required = max(radii) + ENVELOPE_LATTICE_SIDE_CLEARANCE_MM
    if not points_clear(curve, domain, required):
        return []
    return [
        (start, end, radius)
        for start, end, radius in zip(curve, curve[1:], radii)
    ]


def build_fill_network(bounds, domain: Domain, side: str) -> tuple[list[Segment], NetworkStats]:
    """Build one bottom-to-top redundant graph with all endpoints anchored."""
    seed = ORGANIC_GROWTH_SEED ^ round(sum(bounds.minimum + bounds.maximum) * 1000)
    rng = random.Random(seed ^ (0x1357 if side == "left" else 0x2468))
    layer_count = local_layer_count(domain)
    if layer_count == 0:
        return [], NetworkStats(0, 0, 0, 0, 0, 0.0, 0.0, 0, 0, 0.0, 0.0)
    first, coverage = base_layer(rng, bounds, domain)
    if not first:
        return [], NetworkStats(
            layer_count, 0, 0, 0, 0, 0.0, 0.0, 0, 0, 0.0, 0.0
        )
    layers, parents = [first], []
    coverage_values = [coverage]
    for index in range(1, layer_count):
        layer, primary, coverage = next_layer(
            rng,
            layers[-1],
            index / (layer_count - 1),
            bounds,
            domain,
        )
        layers.append(layer)
        parents.append(primary)
        coverage_values.append(coverage)
    open_layer_coverage = (
        coverage_values[1:-1] if len(coverage_values) > 2 else coverage_values
    )
    maximum_coverage = max(value[0] for value in open_layer_coverage)
    maximum_edge_coverage = max(value[1] for value in open_layer_coverage)
    if maximum_coverage > ENVELOPE_LATTICE_INTERIOR_MAX_COVERAGE_RADIUS_MM:
        raise ValueError("A lattice layer exceeds the maximum interior pore radius.")
    if maximum_edge_coverage > ENVELOPE_LATTICE_EDGE_MAX_COVERAGE_RADIUS_MM:
        raise ValueError("A lattice layer exceeds the reinforced-edge pore radius.")
    segments, branch_count, minimum_links, underlinked = [], 0, None, []
    internal_dead_ends = 0
    for previous, current, primary in zip(layers, layers[1:], parents):
        child_parents = [set() for _ in current]
        parent_children = [set() for _ in previous]

        def connect(parent_index: int, child_index: int) -> bool:
            nonlocal branch_count
            if parent_index in child_parents[child_index]:
                return False
            branch = _connection_segments(
                rng,
                previous[parent_index],
                current[child_index],
                bounds,
                domain,
            )
            if not branch:
                return False
            segments.extend(branch)
            child_parents[child_index].add(parent_index)
            parent_children[parent_index].add(child_index)
            branch_count += 1
            return True

        for child_index, child in enumerate(current):
            candidates = sorted(
                (math.dist(parent, child), parent_index)
                for parent_index, parent in enumerate(previous)
                if branch_angle(parent, child)
                <= ENVELOPE_LATTICE_MAX_BRANCH_ANGLE_DEG
            )
            ordered = [primary[child_index]] + [
                index for _, index in candidates if index != primary[child_index]
            ]
            target = ENVELOPE_LATTICE_MIN_PARENT_LINKS + round(
                load_fraction(child, bounds)
                * (
                    ENVELOPE_LATTICE_MAX_PARENT_LINKS
                    - ENVELOPE_LATTICE_MIN_PARENT_LINKS
                )
            )
            for parent_index in ordered:
                connect(parent_index, child_index)
                if len(child_parents[child_index]) == target:
                    break

        # Space-colonization growth must leave no unanchored parent tip.
        for parent_index, children in enumerate(parent_children):
            if children:
                continue
            candidates = sorted(
                (math.dist(previous[parent_index], child), child_index)
                for child_index, child in enumerate(current)
                if branch_angle(previous[parent_index], child)
                <= ENVELOPE_LATTICE_MAX_BRANCH_ANGLE_DEG
            )
            if not any(connect(parent_index, child_index) for _, child_index in candidates):
                internal_dead_ends += 1

        for child_index, child in enumerate(current):
            selected = len(child_parents[child_index])
            minimum_links = selected if minimum_links is None else min(
                minimum_links,
                selected,
            )
            if selected < ENVELOPE_LATTICE_MIN_EFFECTIVE_PARENT_LINKS:
                limits = domain_value(child[0], child[1], domain, 0)
                clearance = domain_value(child[0], child[1], domain, 1)
                underlinked.append(
                    (
                        selected,
                        0.0 if limits is None else limits[1] - limits[0],
                        clearance,
                    )
                )
    if internal_dead_ends:
        raise ValueError(
            f"Biological growth left {internal_dead_ends} unanchored internal tips."
        )
    linked_nodes = sum(len(layer) for layer in layers[1:])
    average_links = branch_count / linked_nodes
    underlinked_ratio = len(underlinked) / linked_nodes
    if underlinked_ratio > ENVELOPE_LATTICE_MAX_UNDERLINKED_NODE_RATIO:
        raise ValueError(
            f"Underlinked-node ratio {underlinked_ratio:.3f} exceeds the limit."
        )
    if average_links < ENVELOPE_LATTICE_MIN_AVERAGE_PARENT_LINKS:
        raise ValueError(f"Average parent links {average_links:.3f} is too low.")
    return segments, NetworkStats(
        layer_count,
        sum(map(len, layers)),
        branch_count,
        internal_dead_ends,
        0,
        maximum_coverage,
        maximum_edge_coverage,
        minimum_links or 0,
        len(underlinked),
        average_links,
        underlinked_ratio,
    )
