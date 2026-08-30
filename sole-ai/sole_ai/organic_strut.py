# sole_ai.organic_strut: closed stochastic cellular-foam sole generation.
"""Generate dense curved cells plus solid TPU skins and plate supports."""
from __future__ import annotations

from collections import Counter, defaultdict
import json
import math
from pathlib import Path

from .config import (
    FLASH_STUDIO_BED_MARGIN_MM,
    FLASH_STUDIO_BED_SIZE_MM,
    GROUND_SKIN_THICKNESS_MM,
    ORGANIC_CELL_SIZE_MM,
    ORGANIC_DESIGN_BRANCH_DIAMETER_MM,
    ORGANIC_IMPLICIT_MERGE_MM,
    ORGANIC_MAX_BRANCH_ANGLE_DEG,
    ORGANIC_MAX_BRIDGE_MM,
    ORGANIC_MAX_BRANCH_DIAMETER_MM,
    ORGANIC_MIN_BRANCH_DIAMETER_MM,
    ORGANIC_SMOOTH_UNION_MM,
    ORGANIC_STRUT_GRID_STEP_MM,
    ORGANIC_STRUT_PREVIEW_GRID_STEP_MM,
    ORGANIC_SURFACE_VERTEX_BIAS_MM,
    OUTPUT_DIR,
    PLATE_CRADLE_THICKNESS_MM,
    PLATE_POCKET_CLEARANCE_MM,
    PLATE_THICKNESS_MM,
    PLATE_VISIBLE_LATTICE_MARGIN_MM,
    RAW_DATA_DIR,
    TOP_SKIN_THICKNESS_MM,
)
from .flash_layout import flash_transform as _flash_transform
from .gyroid import _axis_values, _write_binary_stl
from .marching_tetra import march_tetrahedra
from .mesh import is_watertight, read_binary_stl_triangles, write_binary_stl
from .organic_network import _branch_angle, build_network
from .pipeline import validate_envelope
from .variable_lattice import (
    _column_widths,
    _interpolate_path,
    _projected_triangles,
    _vertical_bounds,
)


Point = tuple[float, float, float]
Segment = tuple[Point, Point, float]


def _clean_triangles(triangles):
    """Remove zero-area and coincident faces created at exact field contacts."""
    cleaned, seen = [], set()
    for triangle in triangles:
        keys = tuple(tuple(round(value, 7) for value in point) for point in triangle)
        if len(set(keys)) < 3:
            continue
        left = tuple(triangle[1][axis] - triangle[0][axis] for axis in range(3))
        right = tuple(triangle[2][axis] - triangle[0][axis] for axis in range(3))
        cross = (
            left[1] * right[2] - left[2] * right[1],
            left[2] * right[0] - left[0] * right[2],
            left[0] * right[1] - left[1] * right[0],
        )
        if sum(value * value for value in cross) <= 1e-16:
            continue
        face = tuple(sorted(keys))
        if face not in seen:
            cleaned.append(triangle)
            seen.add(face)
    return cleaned


def _bad_edge_counts(triangles) -> dict[int, int]:
    """Summarize topology defects for a useful failure instead of a vague STL error."""
    edges = Counter()
    for triangle in triangles:
        keys = [tuple(round(value, 5) for value in point) for point in triangle]
        for first, second in zip(keys, keys[1:] + keys[:1]):
            edges[tuple(sorted((first, second)))] += 1
    return dict(Counter(edges.values()))


def _segment_bins(segments: list[Segment], bin_size: float):
    """Index struts spatially so dense scalar-grid sampling stays practical."""
    bins = defaultdict(list)
    for segment in segments:
        first, second, radius = segment
        minima = [min(a, b) - radius for a, b in zip(first, second)]
        maxima = [max(a, b) + radius for a, b in zip(first, second)]
        ranges = [range(math.floor(low / bin_size), math.floor(high / bin_size) + 1) for low, high in zip(minima, maxima)]
        for ix in ranges[0]:
            for iy in ranges[1]:
                for iz in ranges[2]:
                    bins[(ix, iy, iz)].append(segment)
    return bins


def _segment_field(point: Point, bins, bin_size: float) -> float:
    """Return signed distance to the nearest locally indexed variable-radius strut."""
    key = tuple(math.floor(value / bin_size) for value in point)
    best = None
    for first, second, radius in bins.get(key, ()):
        direction = tuple(b - a for a, b in zip(first, second))
        length_squared = sum(value * value for value in direction)
        offset = tuple(value - start for value, start in zip(point, first))
        fraction = max(0.0, min(1.0, sum(a * b for a, b in zip(offset, direction)) / length_squared))
        closest = tuple(start + fraction * delta for start, delta in zip(first, direction))
        distance = math.sqrt(sum((value - near) ** 2 for value, near in zip(point, closest)))
        value = distance - radius - ORGANIC_IMPLICIT_MERGE_MM
        if best is None:
            best = value
        else:
            blend = max(ORGANIC_SMOOTH_UNION_MM - abs(best - value), 0.0)
            best = min(best, value) - blend * blend / (4.0 * ORGANIC_SMOOTH_UNION_MM)
    return 1.0 if best is None else best


def _plate_regions(x_mm, y_mm, z_mm, split_z, local_width, plate_points, half):
    """Return pocket exclusion and the 2 mm plate sandwich/support solid."""
    if local_width is None:
        return False, False
    heel_y, toe_y = plate_points[0][0], plate_points[-1][0]
    if not toe_y <= y_mm <= heel_y:
        return False, False
    center_x = (local_width[0] + local_width[1]) / 2.0
    local_half_width = (local_width[1] - local_width[0]) / 2.0
    inner_half_width = max(
        local_half_width * 0.55,
        local_half_width - PLATE_VISIBLE_LATTICE_MARGIN_MM - PLATE_CRADLE_THICKNESS_MM,
    )
    outer_half_width = inner_half_width + PLATE_CRADLE_THICKNESS_MM
    inside_inner = abs(x_mm - center_x) <= inner_half_width
    inside_outer = abs(x_mm - center_x) <= outer_half_width
    pocket_half = PLATE_THICKNESS_MM / 2.0 + PLATE_POCKET_CLEARANCE_MM
    if half == "lower":
        pocket = inside_inner and z_mm > split_z - pocket_half
        face_support = inside_inner and split_z - pocket_half - PLATE_CRADLE_THICKNESS_MM <= z_mm <= split_z - pocket_half
    else:
        pocket = inside_inner and z_mm < split_z + pocket_half
        face_support = inside_inner and split_z + pocket_half <= z_mm <= split_z + pocket_half + PLATE_CRADLE_THICKNESS_MM
    side_support = inside_outer and not inside_inner and abs(z_mm - split_z) <= pocket_half + PLATE_CRADLE_THICKNESS_MM
    return pocket, face_support or side_support


def _field(axes, columns, widths, plate_points, bins, half):
    """Union struts, skins, and plate support into one closed component field."""
    field = []
    for ix, x_mm in enumerate(axes[0]):
        x_slice = []
        for iy, y_mm in enumerate(axes[1]):
            bounds = columns.get((ix, iy))
            column = []
            for z_mm in axes[2]:
                if bounds is None:
                    column.append(1.0)
                    continue
                split_z = _interpolate_path(y_mm, plate_points)
                in_half = z_mm <= split_z if half == "lower" else z_mm >= split_z
                pocket, plate_support = _plate_regions(
                    x_mm, y_mm, z_mm, split_z, widths.get(iy), plate_points, half
                )
                ground_skin = half == "lower" and z_mm <= bounds[0] + GROUND_SKIN_THICKNESS_MM
                top_skin = half == "upper" and z_mm >= bounds[1] - TOP_SKIN_THICKNESS_MM
                if not bounds[0] <= z_mm <= bounds[1] or not in_half or pocket:
                    value = 1.0
                elif ground_skin or top_skin or plate_support:
                    value = -1.0
                else:
                    value = _segment_field((x_mm, y_mm, z_mm), bins, ORGANIC_CELL_SIZE_MM)
                if abs(value) < ORGANIC_SURFACE_VERTEX_BIAS_MM:
                    value = ORGANIC_SURFACE_VERTEX_BIAS_MM
                column.append(value)
            x_slice.append(column)
        field.append(x_slice)
    return field


def _padded_axes(bounds, grid_step: float):
    """Surround the source envelope with one positive-field cell on every side."""
    return [
        _axis_values(low - grid_step, high + grid_step, grid_step)
        for low, high in zip(bounds.minimum, bounds.maximum)
    ]


def generate_organic_strut_lattice(side: str, *, preview: bool = False):
    """Generate printable upper/lower components and Flash Studio build-plate copies."""
    bounds = validate_envelope(side)
    source = read_binary_stl_triangles(RAW_DATA_DIR / side / "sole-envelope.stl")
    projected = _projected_triangles(source)
    report_path = OUTPUT_DIR / side / "geometry" / f"{side}-0042-001-low-rocker-smooth-heel" / "generation-report.json"
    plate_points = tuple(tuple(point) for point in json.loads(report_path.read_text())["plate_centerline_points_mm"])
    grid_step = ORGANIC_STRUT_PREVIEW_GRID_STEP_MM if preview else ORGANIC_STRUT_GRID_STEP_MM
    axes = _padded_axes(bounds, grid_step)
    columns = {}
    for ix, x_mm in enumerate(axes[0]):
        for iy, y_mm in enumerate(axes[1]):
            hit = _vertical_bounds(x_mm, y_mm, projected)
            if hit is not None:
                columns[(ix, iy)] = hit
    widths = _column_widths(columns, axes)
    networks = {
        half: build_network(bounds, plate_points, half, (axes[0], axes[1], columns))
        for half in ("lower", "upper")
    }
    bins_by_half = {
        half: _segment_bins(segments, ORGANIC_CELL_SIZE_MM)
        for half, segments in networks.items()
    }
    output = OUTPUT_DIR / side / "lattice" / "organic-dense-branch-1p2-1p8-v2"
    output.mkdir(parents=True, exist_ok=True)
    suffix = "-preview" if preview else ""
    records, paths = {}, []
    for half in ("lower", "upper"):
        raw_triangles = march_tetrahedra(
            axes,
            _field(axes, columns, widths, plate_points, bins_by_half[half], half),
        )
        triangles = raw_triangles if is_watertight(raw_triangles) else _clean_triangles(raw_triangles)
        if not is_watertight(triangles):
            raise ValueError(
                f"Generated {half} cellular foam component is not watertight: "
                f"{_bad_edge_counts(triangles)}"
            )
        path = output / f"{half}-cellular-foam{suffix}.stl"
        write_binary_stl(path, triangles, f"{side} {half} cellular foam")
        paths.append(path)
        records[half] = {
            "triangles": len(triangles),
            "curved_branch_segments": len(networks[half]),
            "maximum_measured_branch_axis_angle_deg": max(
                _branch_angle(first, second) for first, second, _ in networks[half]
            ),
        }
        if not preview:
            flash, angle, size = _flash_transform(
                triangles,
                FLASH_STUDIO_BED_SIZE_MM,
                FLASH_STUDIO_BED_MARGIN_MM,
                invert=half == "upper",
            )
            flash_path = output / f"{half}-cellular-foam-flashstudio.stl"
            write_binary_stl(flash_path, flash, f"{side} {half} Flash Studio")
            paths.append(flash_path)
            records[half].update({"flash_rotation_deg": angle, "flash_size_mm": size})
    manifest = output / f"cellular-foam{suffix}-manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "side": side,
                "type": "support_constrained_stochastic_layer_cellular_foam",
                "nominal_cell_size_mm": ORGANIC_CELL_SIZE_MM,
                "density_profile": "dense_short-cell_redundant-branch_v2",
                "minimum_requested_branch_diameter_mm": ORGANIC_MIN_BRANCH_DIAMETER_MM,
                "minimum_designed_branch_diameter_mm": ORGANIC_DESIGN_BRANCH_DIAMETER_MM,
                "minimum_effective_branch_diameter_mm": (
                    ORGANIC_DESIGN_BRANCH_DIAMETER_MM + 2.0 * ORGANIC_IMPLICIT_MERGE_MM
                ),
                "implicit_fusion_overlap_mm_per_side": ORGANIC_IMPLICIT_MERGE_MM,
                "maximum_branch_diameter_mm": ORGANIC_MAX_BRANCH_DIAMETER_MM,
                "maximum_branch_angle_from_build_direction_deg": ORGANIC_MAX_BRANCH_ANGLE_DEG,
                "maximum_target_bridge_mm": ORGANIC_MAX_BRIDGE_MM,
                "upper_bonding_skin_mm": TOP_SKIN_THICKNESS_MM,
                "ground_skin_mm": GROUND_SKIN_THICKNESS_MM,
                "plate_support_each_side_mm": PLATE_CRADLE_THICKNESS_MM,
                "minimum_visible_lattice_beside_plate_mm": PLATE_VISIBLE_LATTICE_MARGIN_MM,
                "manufacturing_orientation": {
                    "lower": "ground skin on bed; build +engineering Z",
                    "upper": "upper bonding skin on bed; build -engineering Z",
                },
                "grid_step_mm": grid_step,
                "closed_two_manifold": True,
                "components": records,
            },
            indent=2,
        ) + "\n"
    )
    paths.append(manifest)
    return tuple(paths)
