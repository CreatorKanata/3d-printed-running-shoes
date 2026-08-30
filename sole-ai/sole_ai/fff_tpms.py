# sole_ai.fff_tpms: supportless FFF-oriented graded TPU Gyroid generation.
"""Create continuous warped TPMS walls, solid interfaces, and validated STL pairs."""
from __future__ import annotations

import json
import math
from pathlib import Path
import subprocess

from .config import (
    FLASH_STUDIO_BED_MARGIN_MM,
    FLASH_STUDIO_BED_SIZE_MM,
    BLENDER_EXECUTABLE,
    GROUND_SKIN_THICKNESS_MM,
    GYROID_CELL_SIZE_MM,
    IMPLICIT_FIELD_ZERO_BIAS_MM,
    OUTPUT_DIR,
    RAW_DATA_DIR,
    TOP_SKIN_THICKNESS_MM,
    TPMS_WALL_MAX_MM,
    TPMS_WALL_MIN_MM,
    TPMS_REPAIR_VOXEL_MM,
    TPMS_WARP_AMPLITUDE_MM,
    TPMS_WARP_WAVELENGTH_X_MM,
    TPMS_WARP_WAVELENGTH_Y_MM,
    TPMS_WARP_WAVELENGTH_Z_MM,
    VARIABLE_LATTICE_GRID_STEP_MM,
    VARIABLE_LATTICE_PREVIEW_GRID_STEP_MM,
)
from .gyroid import _axis_values
from .marching_tetra import march_tetrahedra
from .mesh import is_watertight, read_binary_stl_triangles, write_binary_stl
from .organic_strut import _bad_edge_counts, _clean_triangles, _flash_transform, _plate_regions
from .pipeline import validate_envelope
from .variable_lattice import (
    _column_widths,
    _interpolate_path,
    _projected_triangles,
    _vertical_bounds,
    relative_density,
)


Point = tuple[float, float, float]


def _repair_mesh(path: Path, triangles):
    """Use a fine voxel remesh as the deterministic final manifold repair gate."""
    raw_path = path.with_name(path.stem + "-unrepaired.stl")
    write_binary_stl(raw_path, triangles, "unrepaired FFF graded Gyroid")
    script = Path(__file__).resolve().parents[1] / "tools" / "repair_mesh_blender.py"
    subprocess.run(
        [
            str(BLENDER_EXECUTABLE),
            "-b",
            "--python",
            str(script),
            "--",
            str(raw_path),
            str(path),
            str(TPMS_REPAIR_VOXEL_MM),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    repaired = read_binary_stl_triangles(path)
    if not is_watertight(repaired):
        raise ValueError(f"Voxel repair did not close {path.name}: {_bad_edge_counts(repaired)}")
    return repaired


def _warped_coordinates(point: Point) -> Point:
    """Apply a gentle long-wave phase warp that breaks visual repetition."""
    x_mm, y_mm, z_mm = point
    tau = 2.0 * math.pi
    x_warp = TPMS_WARP_AMPLITUDE_MM * math.sin(tau * y_mm / TPMS_WARP_WAVELENGTH_Y_MM)
    y_warp = TPMS_WARP_AMPLITUDE_MM * math.sin(tau * z_mm / TPMS_WARP_WAVELENGTH_Z_MM + 0.7)
    z_warp = TPMS_WARP_AMPLITUDE_MM * math.sin(tau * x_mm / TPMS_WARP_WAVELENGTH_X_MM + 1.4)
    return x_mm + x_warp, y_mm + y_warp, z_mm + z_warp


def _gyroid_and_gradient(point: Point) -> tuple[float, float]:
    """Return the warped Gyroid phase and an analytical local gradient scale."""
    x_mm, y_mm, z_mm = _warped_coordinates(point)
    wave = 2.0 * math.pi / GYROID_CELL_SIZE_MM
    x_phase, y_phase, z_phase = wave * x_mm, wave * y_mm, wave * z_mm
    value = (
        math.sin(x_phase) * math.cos(y_phase)
        + math.sin(y_phase) * math.cos(z_phase)
        + math.sin(z_phase) * math.cos(x_phase)
    )
    derivatives = (
        wave * (math.cos(x_phase) * math.cos(y_phase) - math.sin(z_phase) * math.sin(x_phase)),
        wave * (-math.sin(x_phase) * math.sin(y_phase) + math.cos(y_phase) * math.cos(z_phase)),
        wave * (-math.sin(y_phase) * math.sin(z_phase) + math.cos(z_phase) * math.cos(x_phase)),
    )
    return value, max(0.15, math.sqrt(sum(item * item for item in derivatives)))


def _wall_thickness(point: Point, bounds, plate_points) -> float:
    """Map the biomechanical density heuristic into a printable wall thickness."""
    x_mm, y_mm, z_mm = point
    longitudinal = (bounds.maximum[1] - y_mm) / bounds.dimensions[1]
    middle_x = (bounds.minimum[0] + bounds.maximum[0]) / 2.0
    transverse = 2.0 * (x_mm - middle_x) / bounds.dimensions[0]
    density = relative_density(
        max(0.0, min(1.0, longitudinal)),
        max(-1.0, min(1.0, transverse)),
        z_mm - _interpolate_path(y_mm, plate_points),
    )
    blend = max(0.0, min(1.0, (density - 0.18) / (0.55 - 0.18)))
    return TPMS_WALL_MIN_MM + blend * (TPMS_WALL_MAX_MM - TPMS_WALL_MIN_MM)


def _tpms_field(point: Point, bounds, plate_points) -> float:
    """Approximate signed distance to a constant-thickness warped Gyroid wall."""
    value, gradient = _gyroid_and_gradient(point)
    return abs(value) / gradient - _wall_thickness(point, bounds, plate_points) / 2.0


def _field(axes, columns, widths, bounds, plate_points, half):
    """Union the continuous TPMS with required skins and the solid plate cradle."""
    field = []
    for ix, x_mm in enumerate(axes[0]):
        x_slice = []
        for iy, y_mm in enumerate(axes[1]):
            local_bounds = columns.get((ix, iy))
            column = []
            for z_mm in axes[2]:
                if local_bounds is None:
                    column.append(1.0)
                    continue
                split_z = _interpolate_path(y_mm, plate_points)
                in_half = z_mm <= split_z if half == "lower" else z_mm >= split_z
                pocket, support = _plate_regions(
                    x_mm, y_mm, z_mm, split_z, widths.get(iy), plate_points, half
                )
                ground = half == "lower" and z_mm <= local_bounds[0] + GROUND_SKIN_THICKNESS_MM
                top = half == "upper" and z_mm >= local_bounds[1] - TOP_SKIN_THICKNESS_MM
                if not local_bounds[0] <= z_mm <= local_bounds[1] or not in_half or pocket:
                    value = 1.0
                elif ground or top or support:
                    value = -1.0
                else:
                    value = _tpms_field((x_mm, y_mm, z_mm), bounds, plate_points)
                if abs(value) < IMPLICIT_FIELD_ZERO_BIAS_MM:
                    value = -IMPLICIT_FIELD_ZERO_BIAS_MM
                column.append(value)
            x_slice.append(column)
        field.append(x_slice)
    return field


def generate_fff_graded_gyroid(side: str, *, preview: bool = False):
    """Generate upper/lower FFF TPU Gyroid bodies and manufacturing metadata."""
    bounds = validate_envelope(side)
    source = read_binary_stl_triangles(RAW_DATA_DIR / side / "sole-envelope.stl")
    projected = _projected_triangles(source)
    report = OUTPUT_DIR / side / "geometry" / f"{side}-0042-001-low-rocker-smooth-heel" / "generation-report.json"
    plate_points = tuple(tuple(point) for point in json.loads(report.read_text())["plate_centerline_points_mm"])
    step = VARIABLE_LATTICE_PREVIEW_GRID_STEP_MM if preview else VARIABLE_LATTICE_GRID_STEP_MM
    axes = [_axis_values(low, high, step) for low, high in zip(bounds.minimum, bounds.maximum)]
    columns = {}
    for ix, x_mm in enumerate(axes[0]):
        for iy, y_mm in enumerate(axes[1]):
            hit = _vertical_bounds(x_mm, y_mm, projected)
            if hit is not None:
                columns[(ix, iy)] = hit
    widths = _column_widths(columns, axes)
    output = OUTPUT_DIR / side / "lattice" / "fff-graded-gyroid-v1"
    output.mkdir(parents=True, exist_ok=True)
    suffix = "-preview" if preview else ""
    paths, records = [], {}
    for half in ("lower", "upper"):
        raw = march_tetrahedra(axes, _field(axes, columns, widths, bounds, plate_points, half))
        path = output / f"{half}-fff-graded-gyroid{suffix}.stl"
        mesh = raw if is_watertight(raw) else _clean_triangles(raw)
        if is_watertight(mesh):
            write_binary_stl(path, mesh, f"{side} {half} FFF graded Gyroid")
        else:
            mesh = _repair_mesh(path, raw)
        paths.append(path)
        records[half] = {"triangles": len(mesh)}
        if not preview:
            flash, angle, size = _flash_transform(
                mesh,
                FLASH_STUDIO_BED_SIZE_MM,
                FLASH_STUDIO_BED_MARGIN_MM,
                invert=half == "upper",
            )
            flash_path = output / f"{half}-fff-graded-gyroid-flashstudio.stl"
            write_binary_stl(flash_path, flash, f"{side} {half} FFF Gyroid Flash Studio")
            paths.append(flash_path)
            records[half].update({"flash_rotation_deg": angle, "flash_size_mm": size})
    manifest = output / f"fff-graded-gyroid{suffix}-manifest.json"
    manifest.write_text(json.dumps({
        "side": side,
        "type": "gently_warped_functionally_graded_walled_gyroid",
        "process": "Flashforge AD5X FFF; TPU 95A; dedicated 0.6 mm nozzle coupon baseline",
        "cell_size_mm": GYROID_CELL_SIZE_MM,
        "wall_thickness_range_mm": [TPMS_WALL_MIN_MM, TPMS_WALL_MAX_MM],
        "warp_amplitude_mm": TPMS_WARP_AMPLITUDE_MM,
        "upper_bonding_skin_mm": TOP_SKIN_THICKNESS_MM,
        "ground_skin_mm": GROUND_SKIN_THICKNESS_MM,
        "plate_support_each_side_mm": 2.0,
        "grid_step_mm": step,
        "closed_two_manifold": True,
        "manufacturing_orientation": {"lower": "ground skin on bed", "upper": "upper bonding skin on bed"},
        "slicer_and_coupon_validation_required": True,
        "components": records,
    }, indent=2) + "\n")
    paths.append(manifest)
    return tuple(paths)
