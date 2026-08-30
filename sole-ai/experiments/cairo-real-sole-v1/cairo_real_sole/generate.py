# cairo_real_sole.generate: build and verify real left/right Side-Reveal soles.
"""Use each supplied STL directly, then emit a reproducible printable candidate."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

from .config import SoleCellConfig
from .geometry import build_field, make_layout


def _load_project_api(sole_ai_root: Path):
    """Import the project's tested STL/domain tools from an explicit checkout."""
    sys.path.insert(0, str(sole_ai_root))
    from sole_ai.envelope_domain import rasterize_intervals
    from sole_ai.gyroid import _axis_values
    from sole_ai.marching_tetra import march_tetrahedra
    from sole_ai.mesh import is_watertight, write_binary_stl
    from sole_ai.organic_strut import _bad_edge_counts, _clean_triangles
    from sole_ai.stl import read_binary_stl_bounds
    from sole_ai.mesh import read_binary_stl_triangles

    return (
        rasterize_intervals,
        _axis_values,
        march_tetrahedra,
        is_watertight,
        write_binary_stl,
        _bad_edge_counts,
        _clean_triangles,
        read_binary_stl_bounds,
        read_binary_stl_triangles,
    )


def generate_real_sole(
    source_stl: Path,
    output_stl: Path,
    sole_ai_root: Path,
    *,
    preview: bool = False,
    config: SoleCellConfig | None = None,
) -> dict[str, object]:
    """Replace one real designer volume with a clipped pentagonal thin-wall core."""
    config = config or SoleCellConfig()
    api = _load_project_api(sole_ai_root)
    (
        rasterize_intervals,
        axis_values,
        march_tetrahedra,
        is_watertight,
        write_binary_stl,
        bad_edge_counts,
        clean_triangles,
        read_bounds,
        read_triangles,
    ) = api
    bounds = read_bounds(source_stl)
    source = read_triangles(source_stl)
    if not is_watertight(source):
        raise ValueError(f"The source STL is not closed: {source_stl}")
    step = config.preview_step_mm if preview else config.production_step_mm
    config.validate(step)
    axes = [
        axis_values(
            low - config.padding_cells * step + 0.31 * step,
            high + config.padding_cells * step,
            step,
        )
        for low, high in zip(bounds.minimum, bounds.maximum)
    ]
    interval_columns, bands, histogram = rasterize_intervals(axes, source)
    layout = make_layout(bounds.minimum[1], bounds.maximum[1], config)
    field = build_field(axes, interval_columns, layout, config)
    negative_samples = sum(
        value <= 0.0
        for x_slice in field
        for column in x_slice
        for value in column
    )
    raw = march_tetrahedra(axes, field)
    triangles = raw if is_watertight(raw) else clean_triangles(raw)
    if not is_watertight(triangles):
        raise RuntimeError(f"Generated mesh is not manifold: {bad_edge_counts(triangles)}")
    output_stl.parent.mkdir(parents=True, exist_ok=True)
    write_binary_stl(output_stl, triangles, "Cairo Bio-Cell real sole")
    vertices = [point for triangle in triangles for point in triangle]
    minimum = tuple(min(point[axis] for point in vertices) for axis in range(3))
    maximum = tuple(max(point[axis] for point in vertices) for axis in range(3))
    report = {
        "source_stl": str(source_stl.resolve()),
        "output_stl": str(output_stl.resolve()),
        "preview": preview,
        "grid_step_mm": step,
        "source_bounds_mm": {
            "minimum": bounds.minimum,
            "maximum": bounds.maximum,
            "dimensions": bounds.dimensions,
        },
        "output_bounds_mm": {
            "minimum": minimum,
            "maximum": maximum,
            "dimensions": tuple(high - low for low, high in zip(minimum, maximum)),
        },
        "cell_count_longitudinal": len(layout.shoulders),
        "vertical_interval_histogram": histogram,
        "vertical_band_count": len(bands),
        "triangle_count": len(triangles),
        "sampled_material_volume_mm3": negative_samples * step**3,
        "closed_two_manifold": True,
        "config": asdict(config),
        "design_note": (
            "Side openings are intentional. Arch legs and apices provide "
            "discrete lower/upper anchors; no continuous skin is added. "
            "This is a print-test candidate, "
            "not a validated running structure."
        ),
    }
    output_stl.with_suffix(".json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    """Generate one left or right candidate from command-line paths."""
    parser = argparse.ArgumentParser(description="Generate a real Cairo Side-Reveal sole.")
    parser.add_argument("source_stl", type=Path)
    parser.add_argument("output_stl", type=Path)
    parser.add_argument("--sole-ai-root", type=Path, required=True)
    parser.add_argument("--preview", action="store_true")
    arguments = parser.parse_args()
    report = generate_real_sole(
        arguments.source_stl,
        arguments.output_stl,
        arguments.sole_ai_root,
        preview=arguments.preview,
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
