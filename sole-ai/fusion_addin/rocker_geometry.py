# fusion_addin.rocker_geometry: source-sampled rocker path and curved split surface.
"""Measure the sole underside and turn it into a safe, moderated rocker path."""
from __future__ import annotations

from dataclasses import dataclass

import adsk.core
import adsk.fusion


MILLIMETRES_PER_FUSION_INTERNAL_UNIT = 10.0
SPLIT_EDGE_EXTENSION_MM = 5.0
SPLIT_SURFACE_SIDE_EXTENSION_MM = 5.0
SPLIT_MIN_SKIN_MM = 0.8


@dataclass(frozen=True)
class RockerPath:
    """Centreline points for the full split and the shorter PC plate."""

    split_points_mm: tuple[tuple[float, float], ...]
    plate_points_mm: tuple[tuple[float, float], ...]
    heel_start_y_mm: float
    toe_end_y_mm: float
    deepest_center_z_mm: float


def _millimetres(value_in_fusion_units: float) -> float:
    """Convert Fusion API internal centimetres to project millimetres."""
    return value_in_fusion_units * MILLIMETRES_PER_FUSION_INTERNAL_UNIT


def _fusion_units(value_mm: float) -> float:
    """Convert project millimetres to Fusion API internal centimetres."""
    return value_mm / MILLIMETRES_PER_FUSION_INTERNAL_UNIT


def _sample_vertical_hits(source_body, x_mm: float, y_mm: float) -> tuple[float, float] | None:
    """Return the lowest and highest intersections with the source sole at XY."""
    box = source_body.preciseBoundingBox
    origin = adsk.core.Point3D.create(
        _fusion_units(x_mm), _fusion_units(y_mm), box.minPoint.z - 2.0
    )
    hit_points = adsk.core.ObjectCollection.create()
    source_body.parentComponent.findBRepUsingRay(
        origin,
        adsk.core.Vector3D.create(0.0, 0.0, 1.0),
        adsk.fusion.BRepEntityTypes.BRepFaceEntityType,
        0.001,
        False,
        hit_points,
    )
    if hit_points.count < 2:
        return None
    z_values = [_millimetres(hit_points.item(index).z) for index in range(hit_points.count)]
    return min(z_values), max(z_values)


def build_outsole_lower_path(source_body, sample_count: int) -> tuple[tuple[float, float], ...]:
    """Sample the actual centreline outsole for a ground-skin profile."""
    if sample_count < 7:
        raise ValueError("At least seven outsole samples are required.")
    box = source_body.preciseBoundingBox
    center_x_mm = (_millimetres(box.minPoint.x) + _millimetres(box.maxPoint.x)) / 2.0
    toe_y_mm = _millimetres(box.minPoint.y)
    heel_y_mm = _millimetres(box.maxPoint.y)
    points = []
    for index in range(sample_count):
        fraction = 0.02 + 0.96 * index / (sample_count - 1)
        y_mm = heel_y_mm + (toe_y_mm - heel_y_mm) * fraction
        hits = _sample_vertical_hits(source_body, center_x_mm, y_mm)
        if hits is not None:
            points.append((y_mm, hits[0]))
    if len(points) < 7:
        raise ValueError("The sole underside produced too few ground-skin samples.")
    return tuple(points)


def build_outsole_lower_zones(source_body, longitudinal_count: int, transverse_count: int):
    """Sample multiple transverse outsole paths for a 3D ground-contact skin."""
    if transverse_count < 3:
        raise ValueError("At least three transverse ground-skin zones are required.")
    box = source_body.preciseBoundingBox
    min_x_mm, max_x_mm = _millimetres(box.minPoint.x), _millimetres(box.maxPoint.x)
    toe_y_mm, heel_y_mm = _millimetres(box.minPoint.y), _millimetres(box.maxPoint.y)
    x_values = [
        min_x_mm + (max_x_mm - min_x_mm) * (0.06 + 0.88 * index / (transverse_count - 1))
        for index in range(transverse_count)
    ]
    boundaries = [min_x_mm - 1.0]
    boundaries.extend((left + right) / 2.0 for left, right in zip(x_values, x_values[1:]))
    boundaries.append(max_x_mm + 1.0)
    zones = []
    for zone_index, x_mm in enumerate(x_values):
        points = []
        for index in range(longitudinal_count):
            fraction = 0.02 + 0.96 * index / (longitudinal_count - 1)
            y_mm = heel_y_mm + (toe_y_mm - heel_y_mm) * fraction
            hits = _sample_vertical_hits(source_body, x_mm, y_mm)
            if hits is not None:
                points.append((y_mm, hits[0]))
        if len(points) >= 7:
            zones.append((boundaries[zone_index] - 0.1, boundaries[zone_index + 1] + 0.1, tuple(points)))
    if len(zones) < 3:
        raise ValueError("The sole underside produced too few transverse ground-skin zones.")
    return tuple(zones)


def build_rocker_path(
    source_body,
    deepest_center_z_mm: float,
    heel_relief_percent: float,
    toe_end_percent: float,
    follow_ratio: float,
    sample_count: int,
) -> RockerPath:
    """Blend the measured outsole rocker into a lower, manufacturable split path."""
    if not 0.0 < heel_relief_percent < toe_end_percent < 100.0:
        raise ValueError("Plate heel/toe percentages must be ordered inside 0-100.")
    if not 0.0 <= follow_ratio <= 1.0:
        raise ValueError("plate_rocker_follow_ratio must be between 0 and 1.")
    if sample_count < 7:
        raise ValueError("At least seven rocker samples are required.")

    box = source_body.preciseBoundingBox
    min_x_mm = _millimetres(box.minPoint.x)
    max_x_mm = _millimetres(box.maxPoint.x)
    toe_y_mm = _millimetres(box.minPoint.y)
    heel_y_mm = _millimetres(box.maxPoint.y)
    min_z_mm = _millimetres(box.minPoint.z)
    center_x_mm = (min_x_mm + max_x_mm) / 2.0
    heel_fraction = heel_relief_percent / 100.0
    toe_fraction = toe_end_percent / 100.0

    fractions = {0.04 + 0.94 * index / (sample_count - 1) for index in range(sample_count)}
    fractions.update((heel_fraction, toe_fraction))
    sampled: list[tuple[float, float, float]] = []
    for fraction in sorted(fractions):
        y_mm = heel_y_mm + (toe_y_mm - heel_y_mm) * fraction
        hits = _sample_vertical_hits(source_body, center_x_mm, y_mm)
        if hits is None:
            continue
        lower_z_mm, upper_z_mm = hits
        center_z_mm = deepest_center_z_mm + follow_ratio * (lower_z_mm - min_z_mm)
        center_z_mm = max(lower_z_mm + SPLIT_MIN_SKIN_MM, center_z_mm)
        center_z_mm = min(upper_z_mm - SPLIT_MIN_SKIN_MM, center_z_mm)
        sampled.append((fraction, y_mm, center_z_mm))
    if len(sampled) < 7:
        raise ValueError("The sole underside produced too few valid rocker samples.")

    plate_points = tuple(
        (y_mm, z_mm)
        for fraction, y_mm, z_mm in sampled
        if heel_fraction <= fraction <= toe_fraction
    )
    if len(plate_points) < 5:
        raise ValueError("The heel-relieved plate path produced too few points.")
    split_points = [(sampled[0][1] + SPLIT_EDGE_EXTENSION_MM, sampled[0][2])]
    split_points.extend((y_mm, z_mm) for _, y_mm, z_mm in sampled)
    split_points.append((sampled[-1][1] - SPLIT_EDGE_EXTENSION_MM, sampled[-1][2]))
    return RockerPath(
        split_points_mm=tuple(split_points),
        plate_points_mm=plate_points,
        heel_start_y_mm=plate_points[0][0],
        toe_end_y_mm=plate_points[-1][0],
        deepest_center_z_mm=deepest_center_z_mm,
    )


def create_rocker_split_surface(component, source_body, split_points_mm, name: str):
    """Extrude the rocker centreline across the full sole as a surface split tool."""
    box = source_body.preciseBoundingBox
    min_x_mm = _millimetres(box.minPoint.x) - SPLIT_SURFACE_SIDE_EXTENSION_MM
    max_x_mm = _millimetres(box.maxPoint.x) + SPLIT_SURFACE_SIDE_EXTENSION_MM
    plane_input = component.constructionPlanes.createInput()
    plane_input.setByOffset(
        component.yZConstructionPlane,
        adsk.core.ValueInput.createByReal(_fusion_units(min_x_mm)),
    )
    plane = component.constructionPlanes.add(plane_input)
    plane.name = name + "_PLANE"
    sketch = component.sketches.add(plane)
    fit_points = adsk.core.ObjectCollection.create()
    for y_mm, z_mm in split_points_mm:
        model_point = adsk.core.Point3D.create(
            _fusion_units(min_x_mm), _fusion_units(y_mm), _fusion_units(z_mm)
        )
        fit_points.add(sketch.modelToSketchSpace(model_point))
    spline = sketch.sketchCurves.sketchFittedSplines.add(fit_points)
    open_profile = component.createOpenProfile(spline, False)
    if open_profile is None:
        raise ValueError("Fusion could not create the open rocker split profile.")
    extrude_input = component.features.extrudeFeatures.createInput(
        open_profile, adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    )
    extrude_input.isSolid = False
    extrude_input.setDistanceExtent(
        False,
        adsk.core.ValueInput.createByReal(_fusion_units(max_x_mm - min_x_mm)),
    )
    surface = component.features.extrudeFeatures.add(extrude_input).bodies.item(0)
    surface.name = name
    return surface
