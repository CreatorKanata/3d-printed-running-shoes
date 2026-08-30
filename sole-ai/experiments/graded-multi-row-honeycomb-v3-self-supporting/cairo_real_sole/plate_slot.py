# cairo_real_sole.plate_slot: preserve the insert pocket in the new base STL.
"""Keep the original solid upper and wall a 2.2 mm plate pocket."""
from __future__ import annotations

import heapq
import math
import statistics

from .geometry import _smooth_union, solid_value


def _slot_levels(interval_columns, expected_mm: float) -> tuple[float, float]:
    """Recover the nested cutter's lower and upper faces from two-band rays."""
    gaps = [
        (intervals[0][1], intervals[-1][0])
        for intervals in interval_columns.values()
        if len(intervals) >= 2
    ]
    if not gaps:
        raise ValueError("The source STL does not contain a nested plate-slot volume.")
    bottom = statistics.median(item[0] for item in gaps)
    top = statistics.median(item[1] for item in gaps)
    tolerance = max(0.25, expected_mm * 0.15)
    if abs((top - bottom) - expected_mm) > tolerance:
        raise ValueError("The detected plate slot is not the expected 2.2 mm thick.")
    return bottom, top


def _inside_clearance(keys, x_step: float, y_step: float):
    """Measure inward plan distance so the pocket gets a real perimeter wall."""
    keys = set(keys)
    neighbours = tuple(
        (dx, dy, math.hypot(dx * x_step, dy * y_step))
        for dx in (-1, 0, 1)
        for dy in (-1, 0, 1)
        if dx or dy
    )
    edge_distance = min(x_step, y_step) / 2.0
    distances = {key: math.inf for key in keys}
    queue = []
    for key in keys:
        if any((key[0] + dx, key[1] + dy) not in keys for dx, dy, _ in neighbours):
            distances[key] = edge_distance
            heapq.heappush(queue, (edge_distance, key))
    while queue:
        distance, key = heapq.heappop(queue)
        if distance != distances[key]:
            continue
        for dx, dy, cost in neighbours:
            candidate = (key[0] + dx, key[1] + dy)
            updated = distance + cost
            if candidate in distances and updated < distances[candidate]:
                distances[candidate] = updated
                heapq.heappush(queue, (updated, candidate))
    return distances


def _plan_limits(axes, interval_columns):
    """Retain the source plan envelope instead of growing a rectangular sole."""
    limits = {}
    for iy in range(len(axes[1])):
        values = [
            axes[0][ix]
            for ix in range(len(axes[0]))
            if (ix, iy) in interval_columns
        ]
        if values:
            limits[iy] = (min(values), max(values))
    return limits


def _envelope_clip(x_mm, y_mm, z_mm, outer, plan_limits, layout, config) -> float:
    """Clip preserved solids to the same sampled source envelope as the cells."""
    low_z, high_z = outer
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
    return clip


def _plate_value(
    x_mm,
    y_mm,
    z_mm,
    outer,
    plan_limits,
    layout,
    config,
    slot_bottom,
    slot_top,
    slot_clearance,
) -> float:
    """Combine lower honeycomb, pocket walls, and the unchanged solid upper."""
    clip = _envelope_clip(x_mm, y_mm, z_mm, outer, plan_limits, layout, config)
    if clip > 0.0:
        return clip + config.surface_bias_mm
    if z_mm >= slot_top:
        return clip + config.surface_bias_mm

    base = solid_value(
        x_mm,
        y_mm,
        z_mm,
        (outer,),
        plan_limits,
        layout,
        config,
    )
    if z_mm <= slot_bottom:
        pocket_floor = max(
            slot_bottom - config.anchor_skin_mm - z_mm,
            z_mm - slot_bottom,
        )
        pocket_floor = max(pocket_floor, clip) + config.surface_bias_mm
        return _smooth_union(base, pocket_floor, config.junction_blend_mm)
    if slot_clearance is None:
        return base

    pocket_wall = max(
        slot_clearance - config.plate_slot_wall_mm,
        slot_bottom - z_mm,
        z_mm - slot_top,
        clip,
    )
    return pocket_wall + config.surface_bias_mm


def build_plate_slot_field(axes, interval_columns, layout, config):
    """Sample one manifold field while preserving the nested 2.2 mm pocket."""
    slot_bottom, slot_top = _slot_levels(
        interval_columns,
        config.plate_slot_expected_mm,
    )
    slot_keys = {
        key for key, intervals in interval_columns.items() if len(intervals) >= 2
    }
    clearance = _inside_clearance(
        slot_keys,
        abs(axes[0][1] - axes[0][0]),
        abs(axes[1][1] - axes[1][0]),
    )
    plan_limits = _plan_limits(axes, interval_columns)
    field = []
    for ix, x_mm in enumerate(axes[0]):
        x_slice = []
        for iy, y_mm in enumerate(axes[1]):
            intervals = interval_columns.get((ix, iy), ())
            if not intervals:
                x_slice.append([1.0 for _ in axes[2]])
                continue
            outer = (intervals[0][0], intervals[-1][1])
            slot_clearance = clearance.get((ix, iy))
            x_slice.append([
                _plate_value(
                    x_mm,
                    y_mm,
                    z_mm,
                    outer,
                    plan_limits.get(iy),
                    layout,
                    config,
                    slot_bottom,
                    slot_top,
                    slot_clearance,
                )
                for z_mm in axes[2]
            ])
        field.append(x_slice)
    return field
