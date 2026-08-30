# sole_ai.mesh_pipeline: writes locally generated upper and bottom STL solids from one candidate.
from __future__ import annotations

import json
from pathlib import Path

from .config import OUTPUT_DIR, PROJECT_ROOT
from .mesh import is_watertight, read_binary_stl_triangles, split_solid_at_z, write_binary_stl


def generate_split_stls(candidate_path: Path) -> list[Path]:
    """Create capped upper/bottom STL baselines while preserving the supplied outer mesh."""
    with candidate_path.open(encoding="utf-8") as candidate_file:
        candidate = json.load(candidate_file)
    source_path = PROJECT_ROOT / candidate["input_mesh"]["path"]
    lower_bound = candidate["input_mesh"]["minimum_mm"][2]
    height = candidate["input_mesh"]["dimensions_mm"][2]
    split_percent = candidate["candidate"]["split_height_percent"]
    split_z = lower_bound + height * split_percent / 100.0
    upper, lower = split_solid_at_z(read_binary_stl_triangles(source_path), split_z)
    if not is_watertight(upper) or not is_watertight(lower):
        raise ValueError("Generated split meshes are not watertight; do not use them for printing.")

    candidate_id = candidate["candidate"]["candidate_id"]
    output_directory = OUTPUT_DIR / candidate["candidate"]["side"] / "geometry" / candidate_id
    output_directory.mkdir(parents=True, exist_ok=True)
    upper_path = output_directory / "upper-midsole-base.stl"
    lower_path = output_directory / "bottom-midsole-base.stl"
    write_binary_stl(upper_path, upper, "sole-ai upper midsole baseline")
    write_binary_stl(lower_path, lower, "sole-ai bottom midsole baseline")
    return [upper_path, lower_path]
