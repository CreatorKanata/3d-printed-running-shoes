# sole_ai.envelope_lattice: graded lattice generation inside designer-supplied solids.
"""Fill sole-lattice-left/right STL volumes with one smooth organic network."""
from __future__ import annotations

import json
import math
from pathlib import Path

from .config import (
    ENVELOPE_LATTICE_ANCHOR_SKIN_MM,
    ENVELOPE_LATTICE_CELL_SIZE_MM,
    ENVELOPE_LATTICE_GRID_STEP_MM,
    ENVELOPE_LATTICE_PREVIEW_GRID_STEP_MM,
    ENVELOPE_LATTICE_SMOOTH_UNION_MM,
    ENVELOPE_LATTICE_SURFACE_VERTEX_BIAS_MM,
    ENVELOPE_LATTICE_THIN_SOLID_THRESHOLD_MM,
    FLASH_STUDIO_BED_MARGIN_MM,
    FLASH_STUDIO_BED_SIZE_MM,
    MAX_SOLE_LENGTH_MM,
    MAX_SOLE_WIDTH_MM,
    MIN_SOLE_LENGTH_MM,
    MIN_SOLE_WIDTH_MM,
    OUTPUT_DIR,
    RAW_DATA_DIR,
)
from .envelope_clearance import measure_side_clearance
from .envelope_manifest import build_manifest
from .envelope_network import (
    NetworkStats,
    build_fill_network,
)
from .envelope_domain import (
    planform_clearance as _planform_clearance,
    rasterize_intervals,
)
from .flash_layout import flash_transform
from .gyroid import _axis_values
from .marching_tetra import march_tetrahedra
from .mesh import is_watertight, read_binary_stl_triangles, write_binary_stl
from .organic_strut import _bad_edge_counts, _clean_triangles, _segment_bins
from .stl import StlValidationError, infer_sole_axes, read_binary_stl_bounds


Point = tuple[float, float, float]


def input_lattice_path(side: str) -> Path:
    """Resolve the explicit lattice-volume STL supplied for one scanned foot."""
    if side not in {"left", "right"}:
        raise ValueError("side must be 'left' or 'right'")
    return RAW_DATA_DIR / side / f"sole-lattice-{side}.stl"


def validate_lattice_volume(side: str):
    """Require a plausible, watertight binary STL without modifying the source."""
    path = input_lattice_path(side)
    if not path.exists():
        raise FileNotFoundError(f"Missing designer lattice volume: {path}")
    bounds = read_binary_stl_bounds(path)
    axes = infer_sole_axes(bounds)
    if not MIN_SOLE_LENGTH_MM <= axes.longitudinal_length_mm <= MAX_SOLE_LENGTH_MM:
        raise StlValidationError("The lattice volume has an implausible sole length.")
    if not MIN_SOLE_WIDTH_MM <= axes.transverse_width_mm <= MAX_SOLE_WIDTH_MM:
        raise StlValidationError("The lattice volume has an implausible sole width.")
    triangles = read_binary_stl_triangles(path)
    if not is_watertight(triangles):
        raise StlValidationError("The lattice volume must be a closed two-manifold STL.")
    return bounds, triangles


def _padded_axes(bounds, step: float) -> list[list[float]]:
    """Give marching tetrahedra one positive cell outside every source bound."""
    return [
        _axis_values(low - step, high + step, step)
        for low, high in zip(bounds.minimum, bounds.maximum)
    ]


def _segment_field(point: Point, bins, bin_size: float) -> float:
    """Return a smoothly blended variable-radius distance to local branches."""
    key = tuple(math.floor(value / bin_size) for value in point)
    best = None
    for first, second, radius in bins.get(key, ()):
        direction = tuple(b - a for a, b in zip(first, second))
        length_squared = sum(value * value for value in direction)
        offset = tuple(value - start for value, start in zip(point, first))
        fraction = max(
            0.0,
            min(
                1.0,
                sum(a * b for a, b in zip(offset, direction)) / length_squared,
            ),
        )
        closest = tuple(
            start + fraction * delta for start, delta in zip(first, direction)
        )
        value = math.dist(point, closest) - radius
        if best is None:
            best = value
        else:
            blend = max(
                ENVELOPE_LATTICE_SMOOTH_UNION_MM - abs(best - value),
                0.0,
            )
            best = min(best, value) - blend**2 / (
                4.0 * ENVELOPE_LATTICE_SMOOTH_UNION_MM
            )
    return 1.0 if best is None else best


def _interval_field(z_mm: float, limits, branch_value: float) -> float:
    """Clip branches to one interval and union its two conformal anchor skins."""
    low_z, high_z = limits
    interval = max(low_z - z_mm, z_mm - high_z)
    if high_z - low_z <= ENVELOPE_LATTICE_THIN_SOLID_THRESHOLD_MM:
        return interval
    lower_anchor = max(
        low_z - z_mm,
        z_mm - (low_z + ENVELOPE_LATTICE_ANCHOR_SKIN_MM),
    )
    upper_anchor = max(
        high_z - ENVELOPE_LATTICE_ANCHOR_SKIN_MM - z_mm,
        z_mm - high_z,
    )
    return max(min(lower_anchor, upper_anchor, branch_value), interval)


def _field(axes, interval_columns, band_clearances, bins, step: float):
    """Union the no-tip branch graph with conformal top and bottom anchors."""
    field = []
    for ix, x_mm in enumerate(axes[0]):
        x_slice = []
        for iy, y_mm in enumerate(axes[1]):
            intervals = interval_columns.get((ix, iy), ())
            column = []
            for z_mm in axes[2]:
                match = next(
                    (
                        (index, interval)
                        for index, interval in enumerate(intervals)
                        if interval[0] <= z_mm <= interval[1]
                    ),
                    None,
                )
                if match is None:
                    value = 1.0
                else:
                    band_index, limits = match
                    branch_value = _segment_field(
                        (x_mm, y_mm, z_mm),
                        bins,
                        ENVELOPE_LATTICE_CELL_SIZE_MM,
                    )
                    clearance = band_clearances[band_index][(ix, iy)]
                    value = max(
                        _interval_field(z_mm, limits, branch_value),
                        step / 2.0 - clearance,
                    )
                if abs(value) < ENVELOPE_LATTICE_SURFACE_VERTEX_BIAS_MM:
                    value = ENVELOPE_LATTICE_SURFACE_VERTEX_BIAS_MM
                column.append(value)
            x_slice.append(column)
        field.append(x_slice)
    return field


def generate_envelope_lattice(
    side: str,
    *,
    preview: bool = False,
) -> tuple[Path, ...]:
    """Generate one graded, organic, closed lattice inside the supplied volume."""
    bounds, source = validate_lattice_volume(side)
    step = (
        ENVELOPE_LATTICE_PREVIEW_GRID_STEP_MM
        if preview
        else ENVELOPE_LATTICE_GRID_STEP_MM
    )
    axes = _padded_axes(bounds, step)
    interval_columns, bands, interval_histogram = rasterize_intervals(axes, source)
    segments, network_stats, band_records, side_clearances = [], [], [], []
    band_clearances = []
    for index, band in enumerate(bands):
        clearance = _planform_clearance(band, step)
        band_clearances.append(clearance)
        domain = (axes[0], axes[1], band, clearance)
        band_segments, band_stats = build_fill_network(bounds, domain, side)
        if not band_segments:
            continue
        segments.extend(band_segments)
        network_stats.append(band_stats)
        measured, measured_surface = measure_side_clearance(
            band_segments,
            domain,
        )
        side_clearances.append(measured)
        band_records.append(
            {
                "band_index": index,
                "sampled_columns": len(band),
                "branch_count": band_stats.branch_count,
                "node_count": band_stats.node_count,
                "minimum_centerline_side_clearance_mm": measured,
                "minimum_branch_surface_side_clearance_mm": measured_surface,
                "maximum_coverage_radius_mm": band_stats.maximum_coverage_radius_mm,
                "maximum_edge_coverage_radius_mm": (
                    band_stats.maximum_edge_coverage_radius_mm
                ),
                "minimum_parent_links": band_stats.minimum_parent_links,
                "underlinked_node_count": band_stats.underlinked_node_count,
                "average_parent_links": band_stats.average_parent_links,
                "underlinked_node_ratio": band_stats.underlinked_node_ratio,
            }
        )
    if not segments:
        raise ValueError("The supplied volume contains no branch-capable interval.")
    stats = NetworkStats(
        max(item.layer_count for item in network_stats),
        sum(item.node_count for item in network_stats),
        sum(item.branch_count for item in network_stats),
        0,
        0,
        max(item.maximum_coverage_radius_mm for item in network_stats),
        max(item.maximum_edge_coverage_radius_mm for item in network_stats),
        min(item.minimum_parent_links for item in network_stats),
        sum(item.underlinked_node_count for item in network_stats),
        min(item.average_parent_links for item in network_stats),
        max(item.underlinked_node_ratio for item in network_stats),
    )
    minimum_side_clearance = min(side_clearances)
    bins = _segment_bins(segments, ENVELOPE_LATTICE_CELL_SIZE_MM)
    raw = march_tetrahedra(
        axes,
        _field(axes, interval_columns, band_clearances, bins, step),
    )
    triangles = raw if is_watertight(raw) else _clean_triangles(raw)
    if not is_watertight(triangles):
        raise ValueError(
            f"Generated lattice is not watertight: {_bad_edge_counts(triangles)}"
        )
    output = OUTPUT_DIR / side / "lattice" / (
        "designer-volume-biological-knn-v10-density50"
    )
    output.mkdir(parents=True, exist_ok=True)
    suffix = "-preview" if preview else ""
    lattice_path = output / f"sole-lattice-{side}-organic-graded{suffix}.stl"
    write_binary_stl(
        lattice_path,
        triangles,
        f"{side} designer volume organic lattice",
    )
    paths = [lattice_path]
    flash_record = None
    if not preview:
        transformed, angle, size = flash_transform(
            triangles,
            FLASH_STUDIO_BED_SIZE_MM,
            FLASH_STUDIO_BED_MARGIN_MM,
        )
        flash_path = output / f"sole-lattice-{side}-organic-graded-flashstudio.stl"
        write_binary_stl(
            flash_path,
            transformed,
            f"{side} organic lattice Flash Studio",
        )
        paths.append(flash_path)
        flash_record = {"rotation_deg": angle, "size_mm": size}
    manifest_path = output / (
        f"sole-lattice-{side}-organic-graded{suffix}-manifest.json"
    )
    manifest_path.write_text(
        json.dumps(
            build_manifest(
                side,
                input_lattice_path(side),
                step,
                triangles,
                segments,
                stats,
                flash_record,
                minimum_side_clearance,
                interval_histogram,
                band_records,
            ),
            indent=2,
        )
        + "\n"
    )
    paths.append(manifest_path)
    return tuple(paths)
