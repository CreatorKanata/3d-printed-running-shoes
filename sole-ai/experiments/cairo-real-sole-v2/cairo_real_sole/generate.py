# cairo_real_sole.generate: build and verify real left/right Side-Reveal soles.
"""Use each supplied STL directly, then emit a reproducible printable candidate."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict
import json
import math
from pathlib import Path
import sys

from .config import SoleCellConfig
from .field_topology import prune_tiny_components
from .geometry import build_field, make_layout


def _topology_examples(triangles, limit: int = 32) -> dict[str, object]:
    """Locate a few non-two-use edges so boundary failures can be fixed locally."""
    edges = Counter()
    for triangle in triangles:
        points = [tuple(round(value, 5) for value in point) for point in triangle]
        for first, second in zip(points, points[1:] + points[:1]):
            edges[tuple(sorted((first, second)))] += 1
    bad = [(edge, count) for edge, count in edges.items() if count != 2]
    return {
        "bad_edge_count": len(bad),
        "multiplicity": dict(Counter(count for _, count in bad)),
        "examples": [
            {"first": edge[0], "second": edge[1], "uses": count}
            for edge, count in bad[:limit]
        ],
    }


def _clean_at_export_tolerance(triangles, tolerance_mm: float = 0.00001):
    """Remove only numerical faces that collapse at the mesh QA tolerance."""
    cleaned = []
    seen = set()
    for triangle in triangles:
        keys = tuple(
            tuple(round(value / tolerance_mm) for value in point)
            for point in triangle
        )
        if len(set(keys)) < 3:
            continue
        face = tuple(sorted(keys))
        if face in seen:
            continue
        seen.add(face)
        cleaned.append(triangle)
    return cleaned


def _guard_isosurface_samples(field, guard_mm: float) -> int:
    """Move near-zero samples away from grid nodes without changing their sign."""
    adjusted = 0
    for x_slice in field:
        for column in x_slice:
            for index, value in enumerate(column):
                if -guard_mm < value < guard_mm:
                    column[index] = -guard_mm if value <= 0.0 else guard_mm
                    adjusted += 1
    return adjusted


def _cap_microscopic_boundary_loops(triangles, maximum_diameter_mm: float = 0.01):
    """Cap only closed sub-0.01 mm marching artefacts; reject real openings."""
    edges = Counter()
    points = {}
    for triangle in triangles:
        keys = [tuple(round(value * 100_000.0) for value in point) for point in triangle]
        for key, point in zip(keys, triangle):
            points.setdefault(key, point)
        for first, second in zip(keys, keys[1:] + keys[:1]):
            edges[tuple(sorted((first, second)))] += 1
    if any(count > 2 for count in edges.values()):
        return triangles, {"capped_loops": 0, "maximum_diameter_mm": None}
    boundary = [edge for edge, count in edges.items() if count == 1]
    neighbours = defaultdict(set)
    for first, second in boundary:
        neighbours[first].add(second)
        neighbours[second].add(first)
    if any(len(items) != 2 for items in neighbours.values()):
        return triangles, {"capped_loops": 0, "maximum_diameter_mm": None}
    unused = set(boundary)
    caps = []
    diameters = []
    while unused:
        start, current = next(iter(unused))
        loop = [start, current]
        unused.discard(tuple(sorted((start, current))))
        previous = start
        while current != start:
            following = next(item for item in neighbours[current] if item != previous)
            edge = tuple(sorted((current, following)))
            unused.discard(edge)
            previous, current = current, following
            if current != start:
                loop.append(current)
            if len(loop) > len(neighbours):
                return triangles, {"capped_loops": 0, "maximum_diameter_mm": None}
        loop_points = [points[key] for key in loop]
        diameter = max(
            math.dist(first, second)
            for first in loop_points
            for second in loop_points
        )
        if diameter > maximum_diameter_mm:
            return triangles, {"capped_loops": 0, "maximum_diameter_mm": diameter}
        centre = tuple(
            sum(point[axis] for point in loop_points) / len(loop_points)
            for axis in range(3)
        )
        caps.extend(
            (centre, first, second)
            for first, second in zip(loop_points, loop_points[1:] + loop_points[:1])
        )
        diameters.append(diameter)
    return triangles + caps, {
        "capped_loops": len(diameters),
        "maximum_diameter_mm": max(diameters, default=0.0),
    }


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
            low - config.padding_cells * step + config.grid_phase_fraction * step,
            high + config.padding_cells * step,
            step,
        )
        for low, high in zip(bounds.minimum, bounds.maximum)
    ]
    interval_columns, bands, histogram = rasterize_intervals(axes, source)
    layout = make_layout(bounds.minimum[1], bounds.maximum[1], config)
    field = build_field(axes, interval_columns, layout, config)
    field_connectivity = prune_tiny_components(field)
    guarded_samples = _guard_isosurface_samples(field, config.isosurface_guard_mm)
    negative_samples = sum(
        value <= 0.0
        for x_slice in field
        for column in x_slice
        for value in column
    )
    raw = march_tetrahedra(axes, field)
    triangles = _clean_at_export_tolerance(
        clean_triangles(raw),
        config.export_cleanup_mm,
    )
    topology_repair = {"capped_loops": 0, "maximum_diameter_mm": 0.0}
    if not is_watertight(triangles):
        triangles, topology_repair = _cap_microscopic_boundary_loops(triangles)
    if not is_watertight(triangles):
        output_stl.parent.mkdir(parents=True, exist_ok=True)
        debug_path = output_stl.with_name(output_stl.stem + "-topology-debug.json")
        debug_path.write_text(
            json.dumps(_topology_examples(triangles), indent=2) + "\n",
            encoding="utf-8",
        )
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
        "longitudinal_rail_count": config.longitudinal_rail_count,
        "design_test_load_n": config.design_test_load_n,
        "vertical_interval_histogram": histogram,
        "vertical_band_count": len(bands),
        "triangle_count": len(triangles),
        "sampled_material_volume_mm3": negative_samples * step**3,
        "estimated_material_mass_g": (
            negative_samples * step**3 / 1000.0 * config.material_density_g_cm3
        ),
        "closed_two_manifold": True,
        "topology_repair": topology_repair,
        "field_connectivity": field_connectivity,
        "guarded_isosurface_samples": guarded_samples,
        "config": asdict(config),
        "design_note": (
            "Side openings are intentional. Continuous 1.5 mm upper/lower "
            "skins distribute landing load; two longitudinal rails resist "
            "progressive lateral buckling. "
            "Material metadata targets eSUN eLastic TPE-83A. "
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
