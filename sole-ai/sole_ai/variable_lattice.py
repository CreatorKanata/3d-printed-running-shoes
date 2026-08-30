# sole_ai.variable_lattice: script-generated organic graded TPMS sole cores.
"""Generate upper/lower variable-density Gyroid STLs from the scanned envelope."""
from __future__ import annotations

import json
import math
from pathlib import Path

from .config import (
    GROUND_SKIN_THICKNESS_MM,
    GYROID_CELL_SIZE_MM,
    OUTPUT_DIR,
    PLATE_CRADLE_THICKNESS_MM,
    RAW_DATA_DIR,
    TOP_SKIN_THICKNESS_MM,
    VARIABLE_DENSITY_BASE,
    VARIABLE_DENSITY_MAX,
    VARIABLE_DENSITY_MIN,
    VARIABLE_FOREFOOT_GAIN,
    VARIABLE_HEEL_RIM_GAIN,
    VARIABLE_LATTICE_GRID_STEP_MM,
    VARIABLE_LATTICE_PREVIEW_GRID_STEP_MM,
    VARIABLE_MIDFOOT_GAIN,
    VARIABLE_PLATE_PATH_GAIN,
)
from .gyroid import _axis_values, _write_binary_stl
from .marching_tetra import march_tetrahedra
from .mesh import is_watertight, read_binary_stl_triangles
from .pipeline import validate_envelope


Point = tuple[float, float, float]


def _gaussian(value: float, center: float, width: float) -> float:
    """Return a smooth unit Gaussian used to blend density zones."""
    return math.exp(-0.5 * ((value - center) / width) ** 2)


def relative_density(longitudinal: float, transverse: float, plate_distance_mm: float) -> float:
    """Return a continuous heuristic density before runner pressure data is available."""
    forefoot = _gaussian(longitudinal, 0.76, 0.16)
    midfoot = _gaussian(longitudinal, 0.48, 0.13) * (0.65 + 0.35 * abs(transverse))
    heel_rim = _gaussian(longitudinal, 0.12, 0.13) * transverse * transverse
    plate_path = _gaussian(longitudinal, 0.62, 0.28) * _gaussian(plate_distance_mm, 0.0, 5.5)
    density = (
        VARIABLE_DENSITY_BASE
        + VARIABLE_FOREFOOT_GAIN * forefoot
        + VARIABLE_MIDFOOT_GAIN * midfoot
        + VARIABLE_HEEL_RIM_GAIN * heel_rim
        + VARIABLE_PLATE_PATH_GAIN * plate_path
    )
    return min(VARIABLE_DENSITY_MAX, max(VARIABLE_DENSITY_MIN, density))


def _solid_gyroid_value(point: Point, density: float) -> float:
    """Return a single-phase Gyroid field whose volume fraction follows density."""
    x, y, z = point
    wave = 2.0 * math.pi / GYROID_CELL_SIZE_MM
    gx, gy, gz = wave * x, wave * y, wave * z
    gyroid = (
        math.sin(gx) * math.cos(gy)
        + math.sin(gy) * math.cos(gz)
        + math.sin(gz) * math.cos(gx)
    )
    threshold = -0.72 + 1.35 * density
    return gyroid - threshold


def _projected_triangles(triangles):
    """Precompute XY barycentric data for vertical envelope intersections."""
    projected = []
    for triangle in triangles:
        first, second, third = triangle
        denominator = (
            (second[1] - third[1]) * (first[0] - third[0])
            + (third[0] - second[0]) * (first[1] - third[1])
        )
        if abs(denominator) < 1e-9:
            continue
        projected.append(
            (
                triangle,
                denominator,
                min(point[0] for point in triangle),
                max(point[0] for point in triangle),
                min(point[1] for point in triangle),
                max(point[1] for point in triangle),
            )
        )
    return projected


def _vertical_bounds(x_mm: float, y_mm: float, projected) -> tuple[float, float] | None:
    """Return the lowest/highest scanned-envelope intersections at one XY point."""
    hits = []
    for triangle, denominator, min_x, max_x, min_y, max_y in projected:
        if not min_x - 1e-7 <= x_mm <= max_x + 1e-7 or not min_y - 1e-7 <= y_mm <= max_y + 1e-7:
            continue
        first, second, third = triangle
        alpha = (
            (second[1] - third[1]) * (x_mm - third[0])
            + (third[0] - second[0]) * (y_mm - third[1])
        ) / denominator
        beta = (
            (third[1] - first[1]) * (x_mm - third[0])
            + (first[0] - third[0]) * (y_mm - third[1])
        ) / denominator
        gamma = 1.0 - alpha - beta
        if min(alpha, beta, gamma) >= -1e-7:
            hits.append(alpha * first[2] + beta * second[2] + gamma * third[2])
    return (min(hits), max(hits)) if len(hits) >= 2 else None


def _interpolate_path(y_mm: float, points) -> float:
    """Interpolate the approved heel-relieved plate/split centreline."""
    if y_mm >= points[0][0]:
        return points[0][1]
    if y_mm <= points[-1][0]:
        return points[-1][1]
    for first, second in zip(points, points[1:]):
        if first[0] >= y_mm >= second[0]:
            fraction = (first[0] - y_mm) / (first[0] - second[0])
            return first[1] + fraction * (second[1] - first[1])
    raise ValueError("Plate path does not cover the requested Y coordinate.")


def _column_widths(columns, axes):
    """Return local scanned-footprint X limits for every sampled Y row."""
    widths = {}
    for iy in range(len(axes[1])):
        x_values = [axes[0][ix] for ix in range(len(axes[0])) if (ix, iy) in columns]
        if x_values:
            widths[iy] = (min(x_values), max(x_values))
    return widths


def _inside_cradle(x_mm, y_mm, z_mm, split_z_mm, local_width, plate_points, scale=0.93):
    """Reserve the Fusion-generated 2 mm solid TPU shell around the plate."""
    heel_y, toe_y = plate_points[0][0] + PLATE_CRADLE_THICKNESS_MM, plate_points[-1][0] - PLATE_CRADLE_THICKNESS_MM
    if not toe_y <= y_mm <= heel_y or local_width is None:
        return False
    center_x = (local_width[0] + local_width[1]) / 2.0
    half_width = (local_width[1] - local_width[0]) * scale / 2.0
    pocket_half_mm = 0.815
    return abs(x_mm - center_x) <= half_width and abs(z_mm - split_z_mm) <= (
        pocket_half_mm + PLATE_CRADLE_THICKNESS_MM
    )


def _inside_interlock_exclusion(x_mm, y_mm, z_mm, split_z_mm, local_width, plate_points):
    """Reserve six alternating solid-TPU key/socket regions on the curved split."""
    if local_width is None:
        return False
    center_x = (local_width[0] + local_width[1]) / 2.0
    width = local_width[1] - local_width[0]
    heel_y, toe_y = plate_points[0][0], plate_points[-1][0]
    for index in range(6):
        y_center = heel_y + (toe_y - heel_y) * index / 5.0
        x_center = center_x + (0.17 * width if index % 2 == 0 else -0.17 * width)
        if (x_mm - x_center) ** 2 + (y_mm - y_center) ** 2 <= 5.3 ** 2:
            return abs(z_mm - split_z_mm) <= 2.8
    return False


def _field_values(axes, columns, widths, plate_points, half: str):
    """Sample one closed upper or lower variable-density implicit material field."""
    min_y, max_y = axes[1][1], axes[1][-2]
    min_x, max_x = axes[0][1], axes[0][-2]
    density_values = []
    field = []
    for ix, x_mm in enumerate(axes[0]):
        x_slice = []
        for iy, y_mm in enumerate(axes[1]):
            bounds = columns.get((ix, iy))
            column = []
            for z_mm in axes[2]:
                if bounds is None or not bounds[0] <= z_mm <= bounds[1]:
                    column.append(1.0)
                    continue
                split_z = _interpolate_path(y_mm, plate_points)
                in_half = z_mm <= split_z if half == "lower" else z_mm >= split_z
                in_skin = z_mm <= bounds[0] + GROUND_SKIN_THICKNESS_MM or z_mm >= bounds[1] - TOP_SKIN_THICKNESS_MM
                in_cradle = _inside_cradle(x_mm, y_mm, z_mm, split_z, widths.get(iy), plate_points)
                in_interlock = _inside_interlock_exclusion(
                    x_mm, y_mm, z_mm, split_z, widths.get(iy), plate_points
                )
                if not in_half or in_skin or in_cradle or in_interlock:
                    column.append(1.0)
                    continue
                longitudinal = (max_y - y_mm) / (max_y - min_y)
                transverse = 2.0 * (x_mm - (min_x + max_x) / 2.0) / (max_x - min_x)
                density = relative_density(longitudinal, transverse, z_mm - split_z)
                density_values.append(density)
                column.append(_solid_gyroid_value((x_mm, y_mm, z_mm), density))
            x_slice.append(column)
        field.append(x_slice)
    return field, density_values


def generate_variable_lattice(side: str, *, preview: bool = False) -> tuple[Path, Path, Path]:
    """Generate upper/lower graded TPMS STLs and a reviewable density manifest."""
    bounds = validate_envelope(side)
    triangles = read_binary_stl_triangles(RAW_DATA_DIR / side / "sole-envelope.stl")
    projected = _projected_triangles(triangles)
    grid_step_mm = (
        VARIABLE_LATTICE_PREVIEW_GRID_STEP_MM if preview else VARIABLE_LATTICE_GRID_STEP_MM
    )
    axes = [
        _axis_values(low, high, grid_step_mm)
        for low, high in zip(bounds.minimum, bounds.maximum)
    ]
    columns = {}
    for ix, x_mm in enumerate(axes[0]):
        for iy, y_mm in enumerate(axes[1]):
            hit = _vertical_bounds(x_mm, y_mm, projected)
            if hit is not None:
                columns[(ix, iy)] = hit
    report_path = OUTPUT_DIR / side / "geometry" / f"{side}-0042-001-low-rocker-smooth-heel" / "generation-report.json"
    with report_path.open(encoding="utf-8") as stream:
        plate_points = tuple(tuple(point) for point in json.load(stream)["plate_centerline_points_mm"])
    widths = _column_widths(columns, axes)
    output_directory = OUTPUT_DIR / side / "lattice" / "variable-density"
    output_directory.mkdir(parents=True, exist_ok=True)
    outputs, all_densities, triangle_counts = [], [], {}
    lower_field, lower_densities = _field_values(axes, columns, widths, plate_points, "lower")
    upper_field, upper_densities = _field_values(axes, columns, widths, plate_points, "upper")
    suffix = "-preview" if preview else ""
    for half, field, densities in (
        ("lower", lower_field, lower_densities),
        ("upper", upper_field, upper_densities),
    ):
        mesh = march_tetrahedra(axes, field)
        if not is_watertight(mesh):
            raise ValueError(f"Generated {half} TPMS is not a closed two-manifold mesh.")
        path = output_directory / f"{half}-organic-graded-tpms{suffix}.stl"
        _write_binary_stl(path, mesh)
        outputs.append(path)
        triangle_counts[half] = len(mesh)
        all_densities.extend(densities)
    manifest_path = output_directory / f"density{suffix}-manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "side": side,
                "type": "smooth_variable_density_gyroid",
                "density_range": [min(all_densities), max(all_densities)],
                "high_density_zones": ["forefoot propulsion", "midfoot stability", "plate load path", "heel rim"],
                "low_density_zone": "central heel and unloaded transition volumes",
                "ground_skin_mm": GROUND_SKIN_THICKNESS_MM,
                "top_skin_mm": TOP_SKIN_THICKNESS_MM,
                "plate_cradle_mm": PLATE_CRADLE_THICKNESS_MM,
                "grid_step_mm": grid_step_mm,
                "purpose": "fusion_visual_review" if preview else "print_geometry",
                "split": "approved curved rocker path",
                "interlocks": "six alternating solid-TPU key/socket exclusions",
                "triangle_counts": triangle_counts,
                "cell_size_mm": GYROID_CELL_SIZE_MM,
            },
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    return outputs[0], outputs[1], manifest_path
