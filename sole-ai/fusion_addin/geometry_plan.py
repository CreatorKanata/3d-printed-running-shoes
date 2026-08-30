# fusion_addin.geometry_plan: pure geometry calculations used by the Fusion script and tests.
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from config import (
    PLATE_HEEL_RELIEF_PERCENT,
    PLATE_HEEL_CAP_RADIUS_MM,
    PLATE_LONGITUDINAL_MARGIN_RATIO,
    PLATE_LONGITUDINAL_SCALE,
    PLATE_POCKET_CLEARANCE_MM,
    PLATE_ROCKER_FOLLOW_RATIO,
    PLATE_TOE_END_PERCENT,
    PLATE_TRANSVERSE_MARGIN_RATIO,
    PLATE_TRANSVERSE_SCALE,
    ROCKER_PROFILE_SAMPLE_COUNT,
)


@dataclass(frozen=True)
class BoundsMm:
    """An axis-aligned B-Rep bounding box expressed in project millimetres."""

    minimum: tuple[float, float, float]
    maximum: tuple[float, float, float]

    @property
    def dimensions(self) -> tuple[float, float, float]:
        return tuple(high - low for low, high in zip(self.minimum, self.maximum))


@dataclass(frozen=True)
class BaselineGeometryPlan:
    """Fully specified primitives needed to make the first editable Fusion assembly."""

    split_z_mm: float
    plate_bottom_z_mm: float
    plate_top_z_mm: float
    plate_profile: str
    toe_spring_start_percent: float
    toe_spring_start_y_mm: float
    toe_spring_rise_mm: float
    toe_axis_direction: str
    plate_corner_radius_mm: float
    plate_transverse_scale: float
    plate_longitudinal_scale: float
    plate_heel_relief_percent: float
    plate_heel_cap_radius_mm: float
    plate_toe_end_percent: float
    plate_rocker_follow_ratio: float
    rocker_profile_sample_count: int
    plate_min_x_mm: float
    plate_max_x_mm: float
    plate_min_y_mm: float
    plate_max_y_mm: float
    pocket_bottom_z_mm: float
    pocket_top_z_mm: float
    pocket_min_x_mm: float
    pocket_max_x_mm: float
    pocket_min_y_mm: float
    pocket_max_y_mm: float
    pocket_corner_radius_mm: float
    pocket_transverse_scale: float
    pocket_longitudinal_scale: float


def build_baseline_plan(candidate_document: dict[str, Any], bounds: BoundsMm) -> BaselineGeometryPlan:
    """Map a checked candidate to a split plane, plate, and clearance-pocket bounds.

    V1 deliberately supports the current Fusion convention only: X is width, Y is
    heel-to-toe, and Z is vertical. Refusing other mappings is safer than silently
    creating a malformed shoe from a rotated input.
    """
    axes = candidate_document["input_mesh"]["inferred_axes"]
    if (axes["longitudinal"], axes["transverse"], axes["vertical"]) != ("y", "x", "z"):
        raise ValueError("Fusion baseline generation requires source axes X=width, Y=length, Z=vertical.")
    if candidate_document["outer_geometry"]["mode"] != "locked_from_input_mesh":
        raise ValueError("Fusion baseline generation requires a locked outer envelope.")

    candidate = candidate_document["candidate"]
    split_percent = float(candidate["split_height_percent"])
    plate_offset = float(candidate["plate_offset_from_split_mm"])
    plate_thickness = float(candidate["plate_thickness_mm"])
    plate_profile = str(candidate.get("plate_profile", "rocker_following"))
    toe_spring_start_percent = float(candidate.get("toe_spring_start_percent", 68.0))
    toe_spring_rise_mm = float(candidate.get("toe_spring_rise_mm", 5.0))
    plate_corner_radius_mm = float(candidate.get("plate_corner_radius_mm", 10.0))
    if not 0.0 < split_percent < 100.0:
        raise ValueError("split_height_percent must be between 0 and 100.")
    if plate_thickness <= 0.0:
        raise ValueError("plate_thickness_mm must be positive.")
    if plate_profile != "rocker_following":
        raise ValueError("V1 supports only the rocker_following PC-plate profile.")
    if not 0.0 < toe_spring_start_percent < 100.0:
        raise ValueError("toe_spring_start_percent must be between 0 and 100.")
    if toe_spring_rise_mm < 0.0:
        raise ValueError("toe_spring_rise_mm must be zero or positive.")
    if plate_corner_radius_mm <= 0.0:
        raise ValueError("plate_corner_radius_mm must be positive.")
    if abs(plate_offset) >= plate_thickness / 2.0:
        raise ValueError("The plate must cross the split surface so both midsoles capture it.")

    min_x, min_y, min_z = bounds.minimum
    max_x, max_y, max_z = bounds.maximum
    width, length, height = bounds.dimensions
    split_z = min_z + height * split_percent / 100.0
    plate_center_z = split_z + plate_offset
    plate_bottom_z = plate_center_z - plate_thickness / 2.0
    plate_top_z = plate_center_z + plate_thickness / 2.0

    plate_min_x = min_x + width * PLATE_TRANSVERSE_MARGIN_RATIO + PLATE_POCKET_CLEARANCE_MM
    plate_max_x = max_x - width * PLATE_TRANSVERSE_MARGIN_RATIO - PLATE_POCKET_CLEARANCE_MM
    plate_min_y = min_y + length * PLATE_LONGITUDINAL_MARGIN_RATIO + PLATE_POCKET_CLEARANCE_MM
    plate_max_y = max_y - length * PLATE_LONGITUDINAL_MARGIN_RATIO - PLATE_POCKET_CLEARANCE_MM
    if plate_min_x >= plate_max_x or plate_min_y >= plate_max_y:
        raise ValueError("The configured plate margins leave no valid plate footprint.")
    if plate_corner_radius_mm >= (plate_max_x - plate_min_x) / 2.0:
        raise ValueError("plate_corner_radius_mm must be less than half of the plate width.")
    # Fusion's left-side camera maps negative Y to screen-right. The supplied
    # model's toe is therefore low Y, while the heel is high Y.
    toe_spring_start_y = plate_max_y - (plate_max_y - plate_min_y) * toe_spring_start_percent / 100.0

    return BaselineGeometryPlan(
        split_z_mm=split_z,
        plate_bottom_z_mm=plate_bottom_z,
        plate_top_z_mm=plate_top_z,
        plate_profile=plate_profile,
        toe_spring_start_percent=toe_spring_start_percent,
        toe_spring_start_y_mm=toe_spring_start_y,
        toe_spring_rise_mm=toe_spring_rise_mm,
        toe_axis_direction="negative_y",
        plate_corner_radius_mm=plate_corner_radius_mm,
        plate_transverse_scale=PLATE_TRANSVERSE_SCALE,
        plate_longitudinal_scale=PLATE_LONGITUDINAL_SCALE,
        plate_heel_relief_percent=PLATE_HEEL_RELIEF_PERCENT,
        plate_heel_cap_radius_mm=PLATE_HEEL_CAP_RADIUS_MM,
        plate_toe_end_percent=PLATE_TOE_END_PERCENT,
        plate_rocker_follow_ratio=PLATE_ROCKER_FOLLOW_RATIO,
        rocker_profile_sample_count=ROCKER_PROFILE_SAMPLE_COUNT,
        plate_min_x_mm=plate_min_x,
        plate_max_x_mm=plate_max_x,
        plate_min_y_mm=plate_min_y,
        plate_max_y_mm=plate_max_y,
        pocket_bottom_z_mm=plate_bottom_z - PLATE_POCKET_CLEARANCE_MM,
        pocket_top_z_mm=plate_top_z + PLATE_POCKET_CLEARANCE_MM,
        pocket_min_x_mm=plate_min_x - PLATE_POCKET_CLEARANCE_MM,
        pocket_max_x_mm=plate_max_x + PLATE_POCKET_CLEARANCE_MM,
        pocket_min_y_mm=plate_min_y - PLATE_POCKET_CLEARANCE_MM,
        pocket_max_y_mm=plate_max_y + PLATE_POCKET_CLEARANCE_MM,
        pocket_corner_radius_mm=plate_corner_radius_mm + PLATE_POCKET_CLEARANCE_MM,
        pocket_transverse_scale=PLATE_TRANSVERSE_SCALE + 2.0 * PLATE_POCKET_CLEARANCE_MM / width,
        pocket_longitudinal_scale=PLATE_LONGITUDINAL_SCALE + 2.0 * PLATE_POCKET_CLEARANCE_MM / length,
    )
