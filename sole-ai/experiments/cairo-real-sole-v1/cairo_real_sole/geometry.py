# cairo_real_sole.geometry: conformal pentagonal arch field for scanned soles.
"""Map side-facing, support-conscious cells into every real STL solid interval."""
from __future__ import annotations

from dataclasses import dataclass
import bisect
import math

from .config import SoleCellConfig


@dataclass(frozen=True)
class CellLayout:
    """Shared longitudinal cell boundaries for one independent foot."""

    boundaries_mm: tuple[float, ...]
    shoulders: tuple[float, ...]


def make_layout(y_min: float, y_max: float, config: SoleCellConfig) -> CellLayout:
    """Build a deterministic, gently varied row without mirroring either foot."""
    widths = []
    cursor = y_min
    index = 0
    while cursor < y_max:
        variation = math.sin(index * 2.399963229728653) * config.pitch_variation
        width = config.cell_pitch_mm * (1.0 + variation)
        widths.append(width)
        cursor += width
        index += 1
    scale = (y_max - y_min) / sum(widths)
    boundaries = [y_min]
    for width in widths:
        boundaries.append(boundaries[-1] + width * scale)
    boundaries[-1] = y_max
    shoulders = tuple(
        config.shoulder_fraction
        + config.shoulder_variation * math.sin((index + 1) * 1.61803398875)
        for index in range(len(widths))
    )
    return CellLayout(tuple(boundaries), shoulders)


def solid_value(
    y_mm: float,
    z_mm: float,
    intervals,
    layout: CellLayout,
    config: SoleCellConfig,
) -> float:
    """Return a negative value only in anchors or pentagonal cell walls."""
    matching = next(
        (limits for limits in intervals if limits[0] <= z_mm <= limits[1]),
        None,
    )
    if matching is None:
        return 1.0
    low_z, high_z = matching
    height = high_z - low_z
    clip = max(low_z - z_mm, z_mm - high_z)
    if height <= config.wall_mm:
        return clip + config.surface_bias_mm

    cell_index = min(
        max(bisect.bisect_right(layout.boundaries_mm, y_mm) - 1, 0),
        len(layout.shoulders) - 1,
    )
    left = layout.boundaries_mm[cell_index]
    right = layout.boundaries_mm[cell_index + 1]
    width = right - left
    local = max(0.0, min(1.0, (y_mm - left) / width))
    shoulder_fraction = layout.shoulders[cell_index]
    shoulder_z = low_z + shoulder_fraction * height
    peak_z = high_z
    roof_fraction = 1.0 - abs(2.0 * local - 1.0)
    roof_z = shoulder_z + roof_fraction * (peak_z - shoulder_z)
    half_wall = config.wall_mm / 2.0

    boundary_distance = min(abs(y_mm - left), abs(y_mm - right))
    vertical_rib = max(
        boundary_distance - half_wall,
        z_mm - shoulder_z - half_wall,
    )
    roof_slope = 2.0 * (peak_z - shoulder_z) / max(width, 1e-9)
    roof_normal_scale = 1.0 / math.sqrt(1.0 + roof_slope * roof_slope)
    roof_rib = abs(z_mm - roof_z) * roof_normal_scale - half_wall
    # Deliberately omit full top/bottom skins. Each vertical leg terminates on
    # the lower source surface and each roof apex terminates on the upper one,
    # retaining only discrete attachment lines instead of two stiff sheets.
    material = min(vertical_rib, roof_rib)
    return max(material, clip) + config.surface_bias_mm


def build_field(axes, interval_columns, layout, config: SoleCellConfig):
    """Sample the whole clipped field while leaving both side faces revealed."""
    field = []
    for ix, _x_mm in enumerate(axes[0]):
        x_slice = []
        for iy, y_mm in enumerate(axes[1]):
            intervals = interval_columns.get((ix, iy), ())
            x_slice.append(
                [
                    solid_value(y_mm, z_mm, intervals, layout, config)
                    for z_mm in axes[2]
                ]
            )
        field.append(x_slice)
    return field
