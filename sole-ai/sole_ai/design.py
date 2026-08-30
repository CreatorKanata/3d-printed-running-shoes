# sole_ai.design: bounded sole-design candidates and deterministic sampling logic.
from __future__ import annotations

from dataclasses import asdict, dataclass
import random
from typing import Any

from .config import (
    PLATE_HEEL_CAP_RADIUS_MM,
    PLATE_HEEL_RELIEF_PERCENT,
    PLATE_ROCKER_FOLLOW_RATIO,
    PLATE_TOE_END_PERCENT,
)


@dataclass(frozen=True)
class SoleCandidate:
    """A CAD-independent candidate intended for later geometry and physics stages."""

    candidate_id: str
    side: str
    plate_offset_from_split_mm: float
    plate_thickness_mm: float
    toe_spring_start_percent: float
    toe_spring_rise_mm: float
    plate_corner_radius_mm: float
    upper_density: float
    bottom_density: float
    split_height_percent: float

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-ready document with the Fusion parameter mapping included."""
        values = asdict(self)
        return {
            "candidate": values,
            "outer_geometry": {
                "mode": "locked_from_input_mesh",
                "rocker_geometry": "inherited_from_input_mesh",
                "note": "The thick external silhouette is not a candidate variable in V1.",
            },
            "fusion_parameters": {
                "plate_offset_from_split_mm": self.plate_offset_from_split_mm,
                "plate_thickness_mm": self.plate_thickness_mm,
                "plate_profile": "rocker_following",
                "toe_axis_direction": "negative_y",
                "plate_heel_relief_percent": PLATE_HEEL_RELIEF_PERCENT,
                "plate_heel_cap_radius_mm": PLATE_HEEL_CAP_RADIUS_MM,
                "plate_toe_end_percent": PLATE_TOE_END_PERCENT,
                "plate_rocker_follow_ratio": PLATE_ROCKER_FOLLOW_RATIO,
                "toe_spring_start_percent": self.toe_spring_start_percent,
                "toe_spring_rise_mm": self.toe_spring_rise_mm,
                "plate_corner_radius_mm": self.plate_corner_radius_mm,
                "upper_bottom_split_height_percent": self.split_height_percent,
            },
            "density_field": {
                "type": "bounded-linear-baseline",
                "upper_relative_density": self.upper_density,
                "bottom_relative_density": self.bottom_density,
                "note": "Replace with a smooth spatial field after FEA and printing calibration."
            },
            "status": "candidate_only_not_manufacturing_geometry",
        }


def sample_candidates(
    *, side: str, bounds: dict[str, Any], count: int, seed: int
) -> list[SoleCandidate]:
    """Create reproducible, in-bounds candidates before a physics score exists.

    Random sampling is intentional for V1. It establishes a valid dataset and clear
    parameter contract; Bayesian or learned search belongs after the FEA loop exists.
    """
    if side not in {"left", "right"}:
        raise ValueError("side must be 'left' or 'right'")
    if count < 1:
        raise ValueError("count must be at least 1")

    randomizer = random.Random(seed)

    def value(name: str) -> float:
        lower, upper = bounds[name]
        return round(randomizer.uniform(lower, upper), 3)

    return [
        SoleCandidate(
            candidate_id=f"{side}-{seed:04d}-{index:03d}",
            side=side,
            plate_offset_from_split_mm=value("plate_offset_from_split_mm"),
            plate_thickness_mm=value("plate_thickness_mm"),
            toe_spring_start_percent=value("toe_spring_start_percent"),
            toe_spring_rise_mm=value("toe_spring_rise_mm"),
            plate_corner_radius_mm=value("plate_corner_radius_mm"),
            upper_density=value("upper_density"),
            bottom_density=value("bottom_density"),
            split_height_percent=value("split_height_percent"),
        )
        for index in range(1, count + 1)
    ]
