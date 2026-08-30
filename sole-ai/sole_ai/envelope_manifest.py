# sole_ai.envelope_manifest: reproducibility record for designer-volume lattices.
"""Describe density, attachment surfaces, topology, and lateral clearance."""
from __future__ import annotations

from collections import Counter

from .config import (
    ENVELOPE_LATTICE_ANCHOR_SKIN_MM,
    ENVELOPE_LATTICE_CELL_SIZE_MM,
    ENVELOPE_LATTICE_EDGE_BAND_MM,
    ENVELOPE_LATTICE_EDGE_COVERAGE_TARGET_RADIUS_MM,
    ENVELOPE_LATTICE_EDGE_MAX_COVERAGE_RADIUS_MM,
    ENVELOPE_LATTICE_INTERIOR_MAX_COVERAGE_RADIUS_MM,
    ENVELOPE_LATTICE_MAX_BRANCH_DIAMETER_MM,
    ENVELOPE_LATTICE_MAX_UNDERLINKED_NODE_RATIO,
    ENVELOPE_LATTICE_MIN_AVERAGE_PARENT_LINKS,
    ENVELOPE_LATTICE_MIN_EFFECTIVE_PARENT_LINKS,
    ENVELOPE_LATTICE_MIN_BRANCH_DIAMETER_MM,
    ENVELOPE_LATTICE_NETWORK_DENSITY_RATIO,
    ENVELOPE_LATTICE_SIDE_CLEARANCE_MM,
    ENVELOPE_LATTICE_THIN_SOLID_THRESHOLD_MM,
)
from .envelope_network import Segment, branch_angle


def _edge_multiplicity(triangles) -> dict[int, int]:
    """Summarize edge sharing for the final independent topology record."""
    edges = Counter()
    for triangle in triangles:
        points = [tuple(round(value, 5) for value in point) for point in triangle]
        for first, second in zip(points, points[1:] + points[:1]):
            edges[tuple(sorted((first, second)))] += 1
    return dict(Counter(edges.values()))


def build_manifest(
    side,
    source_stl,
    step,
    triangles,
    segments: list[Segment],
    stats,
    flash_record,
    minimum_side_clearance,
    interval_histogram,
    band_records,
):
    """Return the complete, reproducible geometry record."""
    return {
        "side": side,
        "source_stl": str(source_stl),
        "source_step": str(source_stl.with_suffix(".step")),
        "type": "space_colonized_orthotropic_knn_biological_network",
        "algorithm": {
            "attractor_growth": "space-colonization-inspired",
            "connections": "anisotropic k-nearest with anastomosis",
            "junction_geometry": "curved implicit smooth union",
        },
        "density_zones": {
            "toe_forefoot": "high",
            "arch": "medium",
            "heel_perimeter": "high",
            "transitions": "Gaussian smooth",
        },
        "cell_size_mm": ENVELOPE_LATTICE_CELL_SIZE_MM,
        "relative_network_density_target": (
            ENVELOPE_LATTICE_NETWORK_DENSITY_RATIO
        ),
        "branch_diameter_mm": [
            ENVELOPE_LATTICE_MIN_BRANCH_DIAMETER_MM,
            ENVELOPE_LATTICE_MAX_BRANCH_DIAMETER_MM,
        ],
        "measured_free_branch_diameter_mm": [
            min(2.0 * radius for _, _, radius in segments),
            max(2.0 * radius for _, _, radius in segments),
        ],
        "anchor_skin_mm": ENVELOPE_LATTICE_ANCHOR_SKIN_MM,
        "anchor_surfaces": {"top": True, "bottom": True, "sides": False},
        "reinforced_edge_band_mm": ENVELOPE_LATTICE_EDGE_BAND_MM,
        "maximum_allowed_edge_coverage_radius_mm": (
            ENVELOPE_LATTICE_EDGE_MAX_COVERAGE_RADIUS_MM
        ),
        "edge_coverage_target_radius_mm": (
            ENVELOPE_LATTICE_EDGE_COVERAGE_TARGET_RADIUS_MM
        ),
        "maximum_allowed_interior_coverage_radius_mm": (
            ENVELOPE_LATTICE_INTERIOR_MAX_COVERAGE_RADIUS_MM
        ),
        "thin_interval_solid_threshold_mm": (
            ENVELOPE_LATTICE_THIN_SOLID_THRESHOLD_MM
        ),
        "minimum_required_parent_links": (
            ENVELOPE_LATTICE_MIN_EFFECTIVE_PARENT_LINKS
        ),
        "minimum_average_parent_links": (
            ENVELOPE_LATTICE_MIN_AVERAGE_PARENT_LINKS
        ),
        "maximum_underlinked_node_ratio": (
            ENVELOPE_LATTICE_MAX_UNDERLINKED_NODE_RATIO
        ),
        "maximum_radius_centerline_side_clearance_mm": (
            ENVELOPE_LATTICE_MAX_BRANCH_DIAMETER_MM / 2.0
            + ENVELOPE_LATTICE_SIDE_CLEARANCE_MM
        ),
        "required_branch_surface_side_clearance_mm": (
            ENVELOPE_LATTICE_SIDE_CLEARANCE_MM
        ),
        "minimum_measured_centerline_side_clearance_mm": minimum_side_clearance,
        "minimum_measured_branch_surface_side_clearance_mm": min(
            record["minimum_branch_surface_side_clearance_mm"]
            for record in band_records
        ),
        "vertical_interval_histogram": interval_histogram,
        "vertical_band_networks": band_records,
        "grid_step_mm": step,
        "triangle_count": len(triangles),
        "curved_branch_segments": len(segments),
        "branch_count": stats.branch_count,
        "layer_count": stats.layer_count,
        "node_count": stats.node_count,
        "internal_dead_end_count": stats.internal_dead_end_count,
        "side_clipped_branch_count": stats.side_clipped_branch_count,
        "maximum_coverage_radius_mm": stats.maximum_coverage_radius_mm,
        "maximum_edge_coverage_radius_mm": stats.maximum_edge_coverage_radius_mm,
        "minimum_parent_links": stats.minimum_parent_links,
        "underlinked_node_count": stats.underlinked_node_count,
        "average_parent_links": stats.average_parent_links,
        "underlinked_node_ratio": stats.underlinked_node_ratio,
        "maximum_measured_branch_angle_deg": max(
            branch_angle(a, b) for a, b, _ in segments
        ),
        "closed_two_manifold": True,
        "edge_multiplicity": _edge_multiplicity(triangles),
        "flash_studio": flash_record,
    }
