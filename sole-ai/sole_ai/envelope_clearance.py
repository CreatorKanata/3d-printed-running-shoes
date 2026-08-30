# sole_ai.envelope_clearance: verify free branches remain inside lateral walls.
"""Measure centreline and branch-surface clearance for one lattice band."""
from __future__ import annotations

from .config import (
    ENVELOPE_LATTICE_SIDE_CLEARANCE_MM,
    MESH_INTERSECTION_EPSILON_MM,
)
from .envelope_domain import Domain, domain_value
from .envelope_network import Segment


def measure_side_clearance(
    segments: list[Segment],
    domain: Domain,
) -> tuple[float, float]:
    """Return minimum centreline/surface margins and reject lateral clipping."""
    samples = [
        (domain_value(point[0], point[1], domain, 1), radius)
        for first, second, radius in segments
        for point in (first, second)
    ]
    if any(clearance is None for clearance, _ in samples):
        raise ValueError("A branch endpoint lies outside the sampled planform.")
    centreline = min(clearance for clearance, _ in samples)
    surface = min(clearance - radius for clearance, radius in samples)
    if surface < (
        ENVELOPE_LATTICE_SIDE_CLEARANCE_MM - MESH_INTERSECTION_EPSILON_MM
    ):
        raise ValueError("A branch violates the required lateral surface margin.")
    return centreline, surface
