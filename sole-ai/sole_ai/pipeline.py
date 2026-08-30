# sole_ai.pipeline: orchestration for mesh validation and candidate-manifest export.
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import (
    DEFAULT_CONFIG_PATH,
    MAX_SOLE_LENGTH_MM,
    MAX_SOLE_WIDTH_MM,
    MIN_SOLE_LENGTH_MM,
    MIN_SOLE_WIDTH_MM,
    OUTPUT_DIR,
    PROJECT_ROOT,
    RAW_DATA_DIR,
)
from .design import sample_candidates
from .stl import MeshBounds, StlValidationError, infer_sole_axes, read_binary_stl_bounds


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    """Load and minimally validate the committed design-constraint document."""
    with path.open(encoding="utf-8") as config_file:
        config = json.load(config_file)
    for key in ("runner", "manufacturing", "outer_envelope", "design_bounds"):
        if key not in config:
            raise ValueError(f"Configuration is missing required section: {key}")
    if config["manufacturing"].get("units") != "mm":
        raise ValueError("Only millimetre geometry is supported in V1.")
    if config["outer_envelope"].get("mode") != "locked_from_input_mesh":
        raise ValueError("V1 requires the supplied thick sole envelope to remain locked.")
    return config


def input_mesh_path(side: str) -> Path:
    """Resolve the convention-based envelope path without changing input files."""
    if side not in {"left", "right"}:
        raise ValueError("side must be 'left' or 'right'")
    return RAW_DATA_DIR / side / "sole-envelope.stl"


def validate_envelope(side: str) -> MeshBounds:
    """Validate a supplied binary STL and catch axis/units mistakes early."""
    path = input_mesh_path(side)
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}. Export sole-envelope.step and a binary millimetre STL; "
            "see data/raw/README.md."
        )
    bounds = read_binary_stl_bounds(path)
    axes = infer_sole_axes(bounds)
    length = axes.longitudinal_length_mm
    width = axes.transverse_width_mm
    if not MIN_SOLE_LENGTH_MM <= length <= MAX_SOLE_LENGTH_MM:
        raise StlValidationError(
            f"{axes.longitudinal_axis.upper()} dimension is {length:.1f} mm; expected a sole length between "
            f"{MIN_SOLE_LENGTH_MM:.0f} and {MAX_SOLE_LENGTH_MM:.0f} mm. Check units and orientation."
        )
    if not MIN_SOLE_WIDTH_MM <= width <= MAX_SOLE_WIDTH_MM:
        raise StlValidationError(
            f"{axes.transverse_axis.upper()} dimension is {width:.1f} mm; expected a sole width between "
            f"{MIN_SOLE_WIDTH_MM:.0f} and {MAX_SOLE_WIDTH_MM:.0f} mm. Check units and orientation."
        )
    return bounds


def generate_manifests(
    side: str, count: int, seed: int, config_path: Path | None = None
) -> list[Path]:
    """Validate geometry and write deterministic, reviewable candidate manifests."""
    resolved_config_path = config_path or DEFAULT_CONFIG_PATH
    config = load_config(resolved_config_path)
    bounds = validate_envelope(side)
    axes = infer_sole_axes(bounds)
    output_directory = OUTPUT_DIR / side
    output_directory.mkdir(parents=True, exist_ok=True)

    outputs: list[Path] = []
    for candidate in sample_candidates(
        side=side, bounds=config["design_bounds"], count=count, seed=seed
    ):
        document = candidate.as_dict() | {
            "project_name": config["project_name"],
            "input_mesh": {
                "path": str(input_mesh_path(side).relative_to(PROJECT_ROOT)),
                "triangle_count": bounds.triangle_count,
                "minimum_mm": bounds.minimum,
                "maximum_mm": bounds.maximum,
                "dimensions_mm": bounds.dimensions,
                "inferred_axes": {
                    "longitudinal": axes.longitudinal_axis,
                    "transverse": axes.transverse_axis,
                    "vertical": axes.vertical_axis,
                    "length_mm": axes.longitudinal_length_mm,
                    "width_mm": axes.transverse_width_mm,
                    "stack_height_mm": axes.stack_height_mm,
                },
            },
            "runner_intent": config["runner"],
            "outer_envelope_constraint": config["outer_envelope"],
            "manufacturing_constraints": config["manufacturing"],
        }
        output_path = output_directory / f"candidate-{candidate.candidate_id}.json"
        with output_path.open("w", encoding="utf-8") as output_file:
            json.dump(document, output_file, ensure_ascii=False, indent=2)
            output_file.write("\n")
        outputs.append(output_path)
    return outputs
