# fusion_addin.structure_plan: pure sizing math for solid TPU support regions.
"""Calculate cradle dimensions without importing Fusion so tests can verify them."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlateCradlePlan:
    """Dimensions for a closed solid-TPU shell around the plate pocket."""

    outer_thickness_mm: float
    transverse_scale: float
    longitudinal_scale: float
    heel_cap_radius_mm: float


def build_plate_cradle_plan(
    source_width_mm: float,
    source_length_mm: float,
    pocket_thickness_mm: float,
    pocket_transverse_scale: float,
    pocket_longitudinal_scale: float,
    pocket_heel_cap_radius_mm: float,
    support_thickness_mm: float,
) -> PlateCradlePlan:
    """Expand the pocket by the requested support thickness in all directions."""
    if min(source_width_mm, source_length_mm, pocket_thickness_mm, support_thickness_mm) <= 0.0:
        raise ValueError("Cradle dimensions and source dimensions must be positive.")
    transverse_scale = pocket_transverse_scale + 2.0 * support_thickness_mm / source_width_mm
    longitudinal_scale = pocket_longitudinal_scale + 2.0 * support_thickness_mm / source_length_mm
    if transverse_scale >= 1.0 or longitudinal_scale >= 1.0:
        raise ValueError("The plate cradle would reach the exterior sidewall.")
    return PlateCradlePlan(
        outer_thickness_mm=pocket_thickness_mm + 2.0 * support_thickness_mm,
        transverse_scale=transverse_scale,
        longitudinal_scale=longitudinal_scale,
        heel_cap_radius_mm=pocket_heel_cap_radius_mm + support_thickness_mm,
    )
