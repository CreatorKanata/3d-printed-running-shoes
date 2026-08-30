# cairo_real_sole.geometry: conformal, self-supporting honeycomb field.
"""Fill the scanned sole with vertical and rising TPE honeycomb walls."""
from __future__ import annotations

from dataclasses import dataclass
import math

from .config import SoleCellConfig


Point2 = tuple[float, float]
Segment2 = tuple[Point2, Point2]


@dataclass(frozen=True)
class HoneycombLayout:
    """Pre-binned point-top hexagon edges covering the left sole side profile."""

    y_min: float
    y_max: float
    z_min: float
    z_max: float
    segments: tuple[Segment2, ...]
    bins: dict[tuple[int, int], tuple[int, ...]]
    bin_mm: float
    column_count: int
    row_count: int
    cell_count: int
    minimum_rising_angle_deg: float
    horizontal_edge_count: int


def make_layout(
    y_min: float,
    y_max: float,
    z_min: float,
    z_max: float,
    config: SoleCellConfig,
) -> HoneycombLayout:
    """Create a point-top tiling without build-plate-parallel cell edges."""
    half_width = config.honeycomb_half_width_mm
    half_height = config.honeycomb_half_height_mm
    vertical_half_edge = config.honeycomb_vertical_half_edge_mm
    y_step = 2.0 * half_width
    z_step = half_height + vertical_half_edge
    y_origin = y_min
    z_origin = z_min + half_height
    q_max = math.ceil((y_max - y_origin) / y_step) + 2
    r_max = math.ceil((z_max - z_origin) / z_step) + 2
    unique_segments: dict[tuple[Point2, Point2], Segment2] = {}
    cells = 0
    columns = set()
    rows = set()
    for r_index in range(-2, r_max + 1):
        centre_z = z_origin + r_index * z_step
        stagger = (r_index & 1) * half_width
        for q_index in range(-2, q_max + 1):
            centre_y = y_origin + stagger + q_index * y_step
            vertices = _hex_vertices(
                centre_y,
                centre_z,
                half_width,
                half_height,
                vertical_half_edge,
            )
            if not _polygon_overlaps(vertices, y_min, y_max, z_min, z_max):
                continue
            cells += 1
            if y_min <= centre_y <= y_max:
                columns.add(q_index)
            if z_min <= centre_z <= z_max:
                rows.add(r_index)
            for first, second in zip(vertices, vertices[1:] + vertices[:1]):
                key = tuple(sorted((_point_key(first), _point_key(second))))
                unique_segments.setdefault(key, (first, second))
    segments = tuple(unique_segments.values())
    bins = _bin_segments(segments, config)
    return HoneycombLayout(
        y_min=y_min,
        y_max=y_max,
        z_min=z_min,
        z_max=z_max,
        segments=segments,
        bins=bins,
        bin_mm=config.honeycomb_bin_mm,
        column_count=len(columns),
        row_count=max(1, len(rows)),
        cell_count=cells,
        minimum_rising_angle_deg=math.degrees(
            math.atan2(half_height - vertical_half_edge, half_width)
        ),
        horizontal_edge_count=sum(
            abs(first[1] - second[1]) < 1e-8 for first, second in segments
        ),
    )


def graded_wall_mm(y_mm: float, layout: HoneycombLayout, config: SoleCellConfig) -> float:
    """Thicken heel and forefoot smoothly while retaining a compliant arch."""
    fraction = (y_mm - layout.y_min) / max(layout.y_max - layout.y_min, 1e-9)
    heel = 1.0 - _smoothstep(
        config.heel_dense_end_fraction,
        config.heel_transition_end_fraction,
        fraction,
    )
    forefoot = _smoothstep(
        config.forefoot_transition_start_fraction,
        config.forefoot_dense_start_fraction,
        fraction,
    )
    weight = max(heel, forefoot)
    return config.wall_mm + (config.dense_wall_mm - config.wall_mm) * weight


def solid_value(
    x_mm: float,
    y_mm: float,
    z_mm: float,
    intervals,
    plan_limits,
    layout: HoneycombLayout,
    config: SoleCellConfig,
) -> float:
    """Return negative values in honeycomb walls, ties, or load-spreading skins."""
    matching = next(
        (limits for limits in intervals if limits[0] <= z_mm <= limits[1]),
        None,
    )
    if matching is None:
        return 1.0
    low_z, high_z = matching
    height = high_z - low_z
    clip = max(
        low_z - z_mm,
        z_mm - high_z,
        layout.y_min - y_mm,
        y_mm - layout.y_max,
    )
    if plan_limits is not None:
        low_x, high_x = plan_limits
        clip = max(
            clip,
            low_x + config.lateral_envelope_inset_mm - x_mm,
            x_mm - (high_x - config.lateral_envelope_inset_mm),
        )
    if height <= max(config.thin_interval_solid_mm, 2.0 * config.anchor_skin_mm):
        return clip + config.surface_bias_mm

    wall = _nearest_wall_distance(y_mm, z_mm, layout)
    wall -= graded_wall_mm(y_mm, layout, config) / 2.0
    rail = _rail_value(x_mm, y_mm, z_mm, matching, plan_limits, layout, config)
    material = _smooth_union(wall, rail, config.junction_blend_mm)
    lower_skin = max(low_z - z_mm, z_mm - (low_z + config.anchor_skin_mm))
    upper_skin = max(high_z - config.anchor_skin_mm - z_mm, z_mm - high_z)
    material = _smooth_union(material, lower_skin, config.junction_blend_mm)
    material = _smooth_union(material, upper_skin, config.junction_blend_mm)
    return max(material, clip) + config.surface_bias_mm


def build_field(axes, interval_columns, layout, config: SoleCellConfig):
    """Sample the clipped honeycomb with continuous upper and lower skins."""
    plan_limits = {}
    for iy in range(len(axes[1])):
        x_values = [
            axes[0][ix]
            for ix in range(len(axes[0]))
            if (ix, iy) in interval_columns
        ]
        if x_values:
            plan_limits[iy] = (min(x_values), max(x_values))
    field = []
    for ix, x_mm in enumerate(axes[0]):
        x_slice = []
        for iy, y_mm in enumerate(axes[1]):
            intervals = interval_columns.get((ix, iy), ())
            if config.merge_vertical_source_intervals and intervals:
                intervals = ((intervals[0][0], intervals[-1][1]),)
            x_slice.append([
                solid_value(
                    x_mm,
                    y_mm,
                    z_mm,
                    intervals,
                    plan_limits.get(iy),
                    layout,
                    config,
                )
                for z_mm in axes[2]
            ])
        field.append(x_slice)
    return field


def _hex_vertices(
    centre_y: float,
    centre_z: float,
    half_width: float,
    half_height: float,
    vertical_half_edge: float,
) -> list[Point2]:
    """Return a point-top hexagon made only of vertical and rising edges."""
    return [
        (centre_y, centre_z + half_height),
        (centre_y - half_width, centre_z + vertical_half_edge),
        (centre_y - half_width, centre_z - vertical_half_edge),
        (centre_y, centre_z - half_height),
        (centre_y + half_width, centre_z - vertical_half_edge),
        (centre_y + half_width, centre_z + vertical_half_edge),
    ]


def _polygon_overlaps(vertices, y_min, y_max, z_min, z_max) -> bool:
    return not (
        max(point[0] for point in vertices) < y_min
        or min(point[0] for point in vertices) > y_max
        or max(point[1] for point in vertices) < z_min
        or min(point[1] for point in vertices) > z_max
    )


def _point_key(point: Point2) -> Point2:
    return tuple(round(value, 6) for value in point)


def _bin_segments(segments: tuple[Segment2, ...], config: SoleCellConfig):
    bins: dict[tuple[int, int], list[int]] = {}
    margin = config.dense_wall_mm / 2.0 + config.junction_blend_mm
    size = config.honeycomb_bin_mm
    for index, (first, second) in enumerate(segments):
        y_range = range(
            math.floor((min(first[0], second[0]) - margin) / size),
            math.floor((max(first[0], second[0]) + margin) / size) + 1,
        )
        z_range = range(
            math.floor((min(first[1], second[1]) - margin) / size),
            math.floor((max(first[1], second[1]) + margin) / size) + 1,
        )
        for y_bin in y_range:
            for z_bin in z_range:
                bins.setdefault((y_bin, z_bin), []).append(index)
    return {key: tuple(values) for key, values in bins.items()}


def _nearest_wall_distance(y_mm: float, z_mm: float, layout: HoneycombLayout) -> float:
    size = layout.bin_mm
    centre = (math.floor(y_mm / size), math.floor(z_mm / size))
    indices = set()
    for y_delta in (-1, 0, 1):
        for z_delta in (-1, 0, 1):
            indices.update(layout.bins.get((centre[0] + y_delta, centre[1] + z_delta), ()))
    if not indices:
        return math.inf
    return min(_segment_distance(y_mm, z_mm, layout.segments[index]) for index in indices)


def _segment_distance(y_mm: float, z_mm: float, segment: Segment2) -> float:
    first, second = segment
    dy, dz = second[0] - first[0], second[1] - first[1]
    denominator = dy * dy + dz * dz
    fraction = 0.0 if denominator == 0.0 else (
        (y_mm - first[0]) * dy + (z_mm - first[1]) * dz
    ) / denominator
    fraction = max(0.0, min(1.0, fraction))
    return math.hypot(
        y_mm - (first[0] + fraction * dy),
        z_mm - (first[1] + fraction * dz),
    )


def _rail_value(x_mm, y_mm, z_mm, interval, plan_limits, layout, config) -> float:
    if plan_limits is None:
        return math.inf
    low_z, high_z = interval
    low_x, high_x = plan_limits
    height = high_z - low_z
    rail = math.inf
    for index in range(1, config.longitudinal_rail_count + 1):
        rail_x = low_x + index * (high_x - low_x) / (config.longitudinal_rail_count + 1)
        rail = min(
            rail,
            max(
                abs(x_mm - rail_x) - config.longitudinal_rail_mm / 2.0,
                layout.y_min + config.honeycomb_half_width_mm - y_mm,
                y_mm - (layout.y_max - config.honeycomb_half_width_mm),
                low_z + config.rail_height_fraction_low * height - z_mm,
                z_mm - (low_z + config.rail_height_fraction_high * height),
            ),
        )
    return rail


def _smoothstep(low: float, high: float, value: float) -> float:
    fraction = max(0.0, min(1.0, (value - low) / max(high - low, 1e-9)))
    return fraction * fraction * (3.0 - 2.0 * fraction)


def _smooth_union(first: float, second: float, blend_mm: float) -> float:
    """Round wall intersections without thickening remote free surfaces."""
    overlap = max(blend_mm - abs(first - second), 0.0)
    return min(first, second) - overlap * overlap / (4.0 * blend_mm)
