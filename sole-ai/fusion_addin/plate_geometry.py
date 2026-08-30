# fusion_addin.plate_geometry: source-derived rocker-following PC-plate geometry.
"""Create a heel-relieved plate contained by the supplied left or right sole."""
from __future__ import annotations

import math

import adsk.core
import adsk.fusion


MILLIMETRES_PER_FUSION_INTERNAL_UNIT = 10.0


def _fusion_units(value_mm: float) -> float:
    """Convert project millimetres to Fusion API internal centimetres."""
    return value_mm / MILLIMETRES_PER_FUSION_INTERNAL_UNIT


def _millimetres(value_in_fusion_units: float) -> float:
    """Convert Fusion API internal centimetres to project millimetres."""
    return value_in_fusion_units * MILLIMETRES_PER_FUSION_INTERNAL_UNIT


def _create_scaled_shoe_clip(component, source_body, transverse_scale, longitudinal_scale, name):
    """Copy and shrink the actual sole in XY to make a sidewall-safe trim tool."""
    copied_body = component.features.copyPasteBodies.add(source_body).bodies.item(0)
    copied_body.name = name
    box = copied_body.preciseBoundingBox
    center_x = (box.minPoint.x + box.maxPoint.x) / 2.0
    center_y = (box.minPoint.y + box.maxPoint.y) / 2.0
    sketch = component.sketches.add(component.xYConstructionPlane)
    scale_point = sketch.sketchPoints.add(adsk.core.Point3D.create(center_x, center_y, 0.0))
    entities = adsk.core.ObjectCollection.create()
    entities.add(copied_body)
    scale_input = component.features.scaleFeatures.createInput(
        entities, scale_point, adsk.core.ValueInput.createByReal(1.0)
    )
    scale_input.setToNonUniform(
        adsk.core.ValueInput.createByReal(transverse_scale),
        adsk.core.ValueInput.createByReal(longitudinal_scale),
        adsk.core.ValueInput.createByReal(1.0),
    )
    component.features.scaleFeatures.add(scale_input)
    return copied_body


def _add_profile_spline(sketch, point, centerline_points_mm, z_offset_mm):
    """Add one fitted spline parallel to the sampled rocker centreline."""
    fit_points = adsk.core.ObjectCollection.create()
    for y_mm, center_z_mm in centerline_points_mm:
        fit_points.add(point(y_mm, center_z_mm + z_offset_mm))
    return sketch.sketchCurves.sketchFittedSplines.add(fit_points)


def _create_rocker_profile_body(
    component,
    min_x_mm: float,
    max_x_mm: float,
    centerline_points_mm,
    thickness_mm: float,
    name: str,
):
    """Extrude a constant-vertical-thickness profile along the sampled rocker."""
    half_thickness = thickness_mm / 2.0
    plane_input = component.constructionPlanes.createInput()
    plane_input.setByOffset(
        component.yZConstructionPlane,
        adsk.core.ValueInput.createByReal(_fusion_units(min_x_mm)),
    )
    plane = component.constructionPlanes.add(plane_input)
    plane.name = name + "_SIDE_PROFILE_PLANE"
    sketch = component.sketches.add(plane)

    def point(y_mm: float, z_mm: float):
        model_point = adsk.core.Point3D.create(
            _fusion_units(min_x_mm), _fusion_units(y_mm), _fusion_units(z_mm)
        )
        return sketch.modelToSketchSpace(model_point)

    lower_points = tuple(centerline_points_mm)
    upper_points = tuple(reversed(lower_points))
    _add_profile_spline(sketch, point, lower_points, -half_thickness)
    lines = sketch.sketchCurves.sketchLines
    toe_y_mm, toe_z_mm = lower_points[-1]
    lines.addByTwoPoints(
        point(toe_y_mm, toe_z_mm - half_thickness),
        point(toe_y_mm, toe_z_mm + half_thickness),
    )
    _add_profile_spline(sketch, point, upper_points, half_thickness)
    heel_y_mm, heel_z_mm = lower_points[0]
    lines.addByTwoPoints(
        point(heel_y_mm, heel_z_mm + half_thickness),
        point(heel_y_mm, heel_z_mm - half_thickness),
    )
    if sketch.profiles.count != 1:
        raise ValueError("Expected one closed rocker plate profile, found {}.".format(sketch.profiles.count))

    extrude_input = component.features.extrudeFeatures.createInput(
        sketch.profiles.item(0), adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    )
    extrude_input.setDistanceExtent(
        False, adsk.core.ValueInput.createByReal(_fusion_units(max_x_mm - min_x_mm))
    )
    body = component.features.extrudeFeatures.add(extrude_input).bodies.item(0)
    body.name = name
    return body


def _create_rounded_heel_mask(
    component,
    min_x_mm: float,
    max_x_mm: float,
    centerline_points_mm,
    thickness_mm: float,
    heel_cap_radius_mm: float,
    name: str,
):
    """Create a temporary mask that replaces the straight rear edge with a round cap."""
    center_x_mm = (min_x_mm + max_x_mm) / 2.0
    heel_y_mm = centerline_points_mm[0][0]
    toe_y_mm = centerline_points_mm[-1][0]
    cap_radius_mm = min(heel_cap_radius_mm, (max_x_mm - min_x_mm) * 0.50)
    cap_center_y_mm = heel_y_mm - cap_radius_mm
    z_values = [point[1] for point in centerline_points_mm]
    bottom_z_mm = min(z_values) - thickness_mm / 2.0 - 1.0
    top_z_mm = max(z_values) + thickness_mm / 2.0 + 1.0

    plane_input = component.constructionPlanes.createInput()
    plane_input.setByOffset(
        component.xYConstructionPlane,
        adsk.core.ValueInput.createByReal(_fusion_units(bottom_z_mm)),
    )
    plane = component.constructionPlanes.add(plane_input)
    plane.name = name + "_PLANE"
    sketch = component.sketches.add(plane)
    point = adsk.core.Point3D.create
    center = point(_fusion_units(center_x_mm), _fusion_units(cap_center_y_mm), 0.0)
    right_cap = point(
        _fusion_units(center_x_mm + cap_radius_mm), _fusion_units(cap_center_y_mm), 0.0
    )
    left_cap = point(
        _fusion_units(center_x_mm - cap_radius_mm), _fusion_units(cap_center_y_mm), 0.0
    )
    sketch.sketchCurves.sketchArcs.addByCenterStartSweep(center, right_cap, math.pi)
    lines = sketch.sketchCurves.sketchLines
    left_toe = point(
        _fusion_units(center_x_mm - cap_radius_mm), _fusion_units(toe_y_mm - 5.0), 0.0
    )
    right_toe = point(
        _fusion_units(center_x_mm + cap_radius_mm), _fusion_units(toe_y_mm - 5.0), 0.0
    )
    lines.addByTwoPoints(left_cap, left_toe)
    lines.addByTwoPoints(left_toe, right_toe)
    lines.addByTwoPoints(right_toe, right_cap)
    if sketch.profiles.count != 1:
        raise ValueError("Expected one rounded heel mask profile, found {}.".format(sketch.profiles.count))
    extrude_input = component.features.extrudeFeatures.createInput(
        sketch.profiles.item(0), adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    )
    extrude_input.setDistanceExtent(
        False, adsk.core.ValueInput.createByReal(_fusion_units(top_z_mm - bottom_z_mm))
    )
    body = component.features.extrudeFeatures.add(extrude_input).bodies.item(0)
    body.name = name
    return body


def _intersect_and_consume(component, target_body, tool_body) -> None:
    """Intersect a plate with one containment tool and consume that tool."""
    tools = adsk.core.ObjectCollection.create()
    tools.add(tool_body)
    combine_input = component.features.combineFeatures.createInput(target_body, tools)
    combine_input.operation = adsk.fusion.FeatureOperations.IntersectFeatureOperation
    combine_input.isKeepToolBodies = False
    combine_input.isNewComponent = False
    component.features.combineFeatures.add(combine_input)


def create_rocker_following_body(
    component,
    source_body,
    centerline_points_mm,
    thickness_mm: float,
    transverse_scale: float,
    longitudinal_scale: float,
    heel_cap_radius_mm: float,
    name: str,
):
    """Create a shortened shoe-shaped plate following the measured outsole rocker."""
    clip_body = _create_scaled_shoe_clip(
        component,
        source_body,
        transverse_scale,
        longitudinal_scale,
        name + "_SHOE_CONTAINMENT_TOOL",
    )
    box = clip_body.preciseBoundingBox
    profile_body = _create_rocker_profile_body(
        component,
        _millimetres(box.minPoint.x),
        _millimetres(box.maxPoint.x),
        centerline_points_mm,
        thickness_mm,
        name,
    )
    heel_mask = _create_rounded_heel_mask(
        component,
        _millimetres(box.minPoint.x),
        _millimetres(box.maxPoint.x),
        centerline_points_mm,
        thickness_mm,
        heel_cap_radius_mm,
        name + "_ROUNDED_HEEL_MASK",
    )
    _intersect_and_consume(component, profile_body, clip_body)
    _intersect_and_consume(component, profile_body, heel_mask)
    profile_body.name = name
    return profile_body
