# fusion_addin.structure_geometry: solid TPU skins, plate cradle, and 3D keys.
"""Build non-lattice wear, bonding, plate-support, and alignment regions."""
from __future__ import annotations

import adsk.core
import adsk.fusion

from plate_geometry import create_rocker_following_body
from structure_plan import build_plate_cradle_plan


MILLIMETRES_PER_FUSION_INTERNAL_UNIT = 10.0


def _fusion_units(value_mm: float) -> float:
    """Convert project millimetres to Fusion API internal centimetres."""
    return value_mm / MILLIMETRES_PER_FUSION_INTERNAL_UNIT


def _millimetres(value_in_fusion_units: float) -> float:
    """Convert Fusion API internal centimetres to project millimetres."""
    return value_in_fusion_units * MILLIMETRES_PER_FUSION_INTERNAL_UNIT


def copy_body(component, source_body, name: str):
    """Copy one source body into a component without mutating it."""
    body = component.features.copyPasteBodies.add(source_body).bodies.item(0)
    body.name = name
    return body


def combine(component, target_body, tool_body, operation) -> None:
    """Combine two bodies in one component and consume the tool."""
    tools = adsk.core.ObjectCollection.create()
    tools.add(tool_body)
    combine_input = component.features.combineFeatures.createInput(target_body, tools)
    combine_input.operation = operation
    combine_input.isKeepToolBodies = False
    combine_input.isNewComponent = False
    component.features.combineFeatures.add(combine_input)


def _profile_band_body(component, min_x_mm, max_x_mm, lower_points_mm, thickness_mm, name):
    """Extrude a constant-vertical-thickness band along a longitudinal rocker."""
    plane_input = component.constructionPlanes.createInput()
    plane_input.setByOffset(
        component.yZConstructionPlane,
        adsk.core.ValueInput.createByReal(_fusion_units(min_x_mm)),
    )
    plane = component.constructionPlanes.add(plane_input)
    plane.name = name + "_PROFILE_PLANE"
    sketch = component.sketches.add(plane)

    def point(y_mm, z_mm):
        model_point = adsk.core.Point3D.create(
            _fusion_units(min_x_mm), _fusion_units(y_mm), _fusion_units(z_mm)
        )
        return sketch.modelToSketchSpace(model_point)

    lower_fit = adsk.core.ObjectCollection.create()
    for y_mm, z_mm in lower_points_mm:
        lower_fit.add(point(y_mm, z_mm))
    upper_fit = adsk.core.ObjectCollection.create()
    for y_mm, z_mm in reversed(lower_points_mm):
        upper_fit.add(point(y_mm, z_mm + thickness_mm))
    curves = sketch.sketchCurves
    curves.sketchFittedSplines.add(lower_fit)
    curves.sketchLines.addByTwoPoints(
        point(lower_points_mm[-1][0], lower_points_mm[-1][1]),
        point(lower_points_mm[-1][0], lower_points_mm[-1][1] + thickness_mm),
    )
    curves.sketchFittedSplines.add(upper_fit)
    curves.sketchLines.addByTwoPoints(
        point(lower_points_mm[0][0], lower_points_mm[0][1] + thickness_mm),
        point(lower_points_mm[0][0], lower_points_mm[0][1]),
    )
    if sketch.profiles.count != 1:
        raise ValueError("Expected one closed ground-skin profile.")
    extrude_input = component.features.extrudeFeatures.createInput(
        sketch.profiles.item(0), adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    )
    extrude_input.setDistanceExtent(
        False, adsk.core.ValueInput.createByReal(_fusion_units(max_x_mm - min_x_mm))
    )
    body = component.features.extrudeFeatures.add(extrude_input).bodies.item(0)
    body.name = name
    return body


def create_ground_skin(component, source_body, lower_points_mm, thickness_mm: float, name: str):
    """Create a nominal-thickness solid wear skin that follows the outsole rocker."""
    box = source_body.preciseBoundingBox
    # Extend slightly below the locked envelope so the Boolean has a clear
    # overlap instead of coincident outsole faces. Intersection restores the
    # exact supplied exterior while retaining the requested inside thickness.
    boolean_overshoot_mm = 0.5
    boolean_points = tuple((y_mm, z_mm - boolean_overshoot_mm) for y_mm, z_mm in lower_points_mm)
    band = _profile_band_body(
        component,
        _millimetres(box.minPoint.x) - 1.0,
        _millimetres(box.maxPoint.x) + 1.0,
        boolean_points,
        thickness_mm + boolean_overshoot_mm,
        name,
    )
    envelope = copy_body(component, source_body, name + "_ENVELOPE_TOOL")
    combine(component, band, envelope, adsk.fusion.FeatureOperations.IntersectFeatureOperation)
    band.name = name
    return band


def create_ground_skin_zones(component, source_body, zones, thickness_mm: float, name: str):
    """Create overlapping outsole-following strips that approximate a 3D skin."""
    bodies = []
    boolean_overshoot_mm = 0.5
    for index, (min_x_mm, max_x_mm, points_mm) in enumerate(zones, start=1):
        boolean_points = tuple((y_mm, z_mm - boolean_overshoot_mm) for y_mm, z_mm in points_mm)
        band = _profile_band_body(
            component,
            min_x_mm,
            max_x_mm,
            boolean_points,
            thickness_mm + boolean_overshoot_mm,
            "{}_{:02d}".format(name, index),
        )
        envelope = copy_body(component, source_body, "{}_ENVELOPE_TOOL_{:02d}".format(name, index))
        combine(component, band, envelope, adsk.fusion.FeatureOperations.IntersectFeatureOperation)
        band.name = "{}_{:02d}".format(name, index)
        bodies.append(band)
    return tuple(bodies)


def create_top_bonding_skin(component, source_body, thickness_mm: float, name: str):
    """Create a solid top interface for bonding the custom upper to the sole."""
    box = source_body.preciseBoundingBox
    min_x, max_x = _millimetres(box.minPoint.x) - 1.0, _millimetres(box.maxPoint.x) + 1.0
    min_y, max_y = _millimetres(box.minPoint.y) - 1.0, _millimetres(box.maxPoint.y) + 1.0
    top_z = _millimetres(box.maxPoint.z) + 0.1
    bottom_z = top_z - thickness_mm - 0.1
    plane_input = component.constructionPlanes.createInput()
    plane_input.setByOffset(
        component.xYConstructionPlane,
        adsk.core.ValueInput.createByReal(_fusion_units(bottom_z)),
    )
    plane = component.constructionPlanes.add(plane_input)
    sketch = component.sketches.add(plane)
    sketch.sketchCurves.sketchLines.addTwoPointRectangle(
        adsk.core.Point3D.create(_fusion_units(min_x), _fusion_units(min_y), 0.0),
        adsk.core.Point3D.create(_fusion_units(max_x), _fusion_units(max_y), 0.0),
    )
    extrude_input = component.features.extrudeFeatures.createInput(
        sketch.profiles.item(0), adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    )
    extrude_input.setDistanceExtent(
        False, adsk.core.ValueInput.createByReal(_fusion_units(top_z - bottom_z))
    )
    skin = component.features.extrudeFeatures.add(extrude_input).bodies.item(0)
    envelope = copy_body(component, source_body, name + "_ENVELOPE_TOOL")
    combine(component, skin, envelope, adsk.fusion.FeatureOperations.IntersectFeatureOperation)
    skin.name = name
    return skin


def create_plate_support_shell(
    component,
    source_body,
    pocket_body,
    centerline_points_mm,
    pocket_thickness_mm: float,
    pocket_transverse_scale: float,
    pocket_longitudinal_scale: float,
    pocket_heel_cap_radius_mm: float,
    support_thickness_mm: float,
    name: str,
):
    """Create a closed solid TPU shell outside the complete plate pocket."""
    box = source_body.preciseBoundingBox
    plan = build_plate_cradle_plan(
        _millimetres(box.maxPoint.x - box.minPoint.x),
        _millimetres(box.maxPoint.y - box.minPoint.y),
        pocket_thickness_mm,
        pocket_transverse_scale,
        pocket_longitudinal_scale,
        pocket_heel_cap_radius_mm,
        support_thickness_mm,
    )
    first_y, first_z = centerline_points_mm[0]
    last_y, last_z = centerline_points_mm[-1]
    outer_points = ((first_y + support_thickness_mm, first_z),) + tuple(centerline_points_mm) + (
        (last_y - support_thickness_mm, last_z),
    )
    outer = create_rocker_following_body(
        component,
        source_body,
        outer_points,
        plan.outer_thickness_mm,
        plan.transverse_scale,
        plan.longitudinal_scale,
        plan.heel_cap_radius_mm,
        name,
    )
    inner = copy_body(component, pocket_body, name + "_POCKET_TOOL")
    combine(component, outer, inner, adsk.fusion.FeatureOperations.CutFeatureOperation)
    outer.name = name
    return outer, plan


def _cylinder(component, x_mm, y_mm, bottom_z_mm, height_mm, radius_mm, name):
    """Create one vertical cylindrical solid for a male key or female socket."""
    plane_input = component.constructionPlanes.createInput()
    plane_input.setByOffset(
        component.xYConstructionPlane,
        adsk.core.ValueInput.createByReal(_fusion_units(bottom_z_mm)),
    )
    plane = component.constructionPlanes.add(plane_input)
    sketch = component.sketches.add(plane)
    sketch.sketchCurves.sketchCircles.addByCenterRadius(
        adsk.core.Point3D.create(_fusion_units(x_mm), _fusion_units(y_mm), 0.0),
        _fusion_units(radius_mm),
    )
    extrude_input = component.features.extrudeFeatures.createInput(
        sketch.profiles.item(0), adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    )
    extrude_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(_fusion_units(height_mm)))
    body = component.features.extrudeFeatures.add(extrude_input).bodies.item(0)
    body.name = name
    return body


def create_interlock_keys(
    lower_component,
    upper_component,
    source_body,
    split_points_mm,
    key_height_mm: float,
    key_radius_mm: float,
    clearance_mm: float,
    count: int,
):
    """Add alternating male pegs and female rings across the curved 3D split."""
    box = source_body.preciseBoundingBox
    center_x_mm = _millimetres((box.minPoint.x + box.maxPoint.x) / 2.0)
    width_mm = _millimetres(box.maxPoint.x - box.minPoint.x)
    usable = split_points_mm[3:-3]
    if len(usable) < count:
        raise ValueError("Too few rocker points for the requested interlock keys.")
    positions = []
    for key_index in range(count):
        point_index = round(key_index * (len(usable) - 1) / max(count - 1, 1))
        y_mm, z_mm = usable[point_index]
        x_mm = center_x_mm + (0.17 * width_mm if key_index % 2 == 0 else -0.17 * width_mm)
        male = _cylinder(
            lower_component, x_mm, y_mm, z_mm - 0.6, key_height_mm + 0.6,
            key_radius_mm, "MALE_KEY_{:02d}".format(key_index + 1),
        )
        outer = _cylinder(
            upper_component, x_mm, y_mm, z_mm - 0.1, key_height_mm + 1.2,
            key_radius_mm + 2.0, "FEMALE_SOCKET_{:02d}".format(key_index + 1),
        )
        exclusion = copy_body(
            upper_component, outer, "SOCKET_EXCLUSION_{:02d}".format(key_index + 1)
        )
        ring_hole = _cylinder(
            upper_component, x_mm, y_mm, z_mm - 0.2, key_height_mm + 1.5,
            key_radius_mm + clearance_mm, "SOCKET_RING_HOLE_TOOL",
        )
        combine(upper_component, outer, ring_hole, adsk.fusion.FeatureOperations.CutFeatureOperation)
        exclusion.isLightBulbOn = False
        positions.append((x_mm, y_mm, z_mm, male, outer, exclusion))
    return positions
