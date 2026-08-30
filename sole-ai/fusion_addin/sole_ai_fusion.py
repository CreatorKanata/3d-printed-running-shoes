# fusion_addin.sole_ai_fusion: Fusion script that makes editable thick-sole baseline components.
"""Run this script inside Fusion after opening the matching sole-envelope.step file."""
import json
import os
import sys
import traceback

import adsk.core
import adsk.fusion

SCRIPT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))
if SCRIPT_DIRECTORY not in sys.path:
    sys.path.insert(0, SCRIPT_DIRECTORY)

from config import BODY_DIMENSION_TOLERANCE_MM, MILLIMETRES_PER_FUSION_INTERNAL_UNIT
from geometry_plan import BoundsMm, build_baseline_plan
from plate_geometry import create_rocker_following_body
from rocker_geometry import build_rocker_path, create_rocker_split_surface


def _millimetres(value_in_fusion_units):
    """Convert Fusion's internal centimetres to the millimetre project convention."""
    return value_in_fusion_units * MILLIMETRES_PER_FUSION_INTERNAL_UNIT


def _fusion_units(value_mm):
    """Convert a project millimetre value to Fusion's internal centimetres."""
    return value_mm / MILLIMETRES_PER_FUSION_INTERNAL_UNIT


def _load_candidate(ui):
    """Read the candidate manifest selected by its absolute filesystem path."""
    default_path = os.path.normpath(
        os.path.join(SCRIPT_DIRECTORY, "..", "outputs", "left", "candidate-left-0042-001.json")
    )
    path, cancelled = ui.inputBox("Candidate JSON absolute path", "Sole AI Fusion", default_path)
    if cancelled:
        return None, None
    candidate_path = os.path.abspath(path.strip())
    with open(candidate_path, encoding="utf-8") as candidate_file:
        return json.load(candidate_file), candidate_path


def _bounds_mm(body):
    """Read a selected B-Rep body's bounds and convert them to millimetres."""
    box = body.preciseBoundingBox
    return BoundsMm(
        (_millimetres(box.minPoint.x), _millimetres(box.minPoint.y), _millimetres(box.minPoint.z)),
        (_millimetres(box.maxPoint.x), _millimetres(box.maxPoint.y), _millimetres(box.maxPoint.z)),
    )


def _validate_selected_body(candidate, body):
    """Reject a wrong side, scaled import, or unrelated body before any edits occur."""
    expected = candidate["input_mesh"]["dimensions_mm"]
    actual = _bounds_mm(body).dimensions
    for label, expected_value, actual_value in zip(("X", "Y", "Z"), expected, actual):
        if abs(float(expected_value) - actual_value) > BODY_DIMENSION_TOLERANCE_MM:
            raise ValueError(
                "Selected body does not match the candidate input on {}: expected {:.2f} mm, got {:.2f} mm."
                .format(label, expected_value, actual_value)
            )


def _new_component(parent, name):
    """Create an identity-transform component nested under the supplied component."""
    occurrence = parent.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    occurrence.component.name = name
    return occurrence.component


def _copy_body(target_component, source_body):
    """Copy a B-Rep body into a component without mutating the source geometry."""
    copy_feature = target_component.features.copyPasteBodies.add(source_body)
    return copy_feature.bodies.item(0)


def _create_offset_plane(component, z_mm, name):
    """Create the horizontal split or plate plane at a known global Z coordinate."""
    plane_input = component.constructionPlanes.createInput()
    plane_input.setByOffset(
        component.xYConstructionPlane, adsk.core.ValueInput.createByReal(_fusion_units(z_mm))
    )
    plane = component.constructionPlanes.add(plane_input)
    plane.name = name
    return plane


def _create_rectangular_body(component, min_x, max_x, min_y, max_y, bottom_z, top_z, name):
    """Create a flat plate or oversized pocket tool in the component's XY coordinate frame."""
    plane = _create_offset_plane(component, bottom_z, name + "_PLANE")
    sketch = component.sketches.add(plane)
    lines = sketch.sketchCurves.sketchLines
    point_one = adsk.core.Point3D.create(_fusion_units(min_x), _fusion_units(min_y), 0)
    point_two = adsk.core.Point3D.create(_fusion_units(max_x), _fusion_units(max_y), 0)
    lines.addTwoPointRectangle(point_one, point_two)
    profile = sketch.profiles.item(0)
    extrude_input = component.features.extrudeFeatures.createInput(
        profile, adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    )
    extrude_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(_fusion_units(top_z - bottom_z)))
    body = component.features.extrudeFeatures.add(extrude_input).bodies.item(0)
    body.name = name
    return body


def _split_to_midsole_components(assembly_component, source_body, split_points_mm, candidate_id):
    """Split the envelope on the rocker path and promote both bodies to components."""
    work_component = _new_component(assembly_component, "MIDSOLE_SPLIT_WORK_" + candidate_id)
    copied_body = _copy_body(work_component, source_body)
    copied_body.name = "LOCKED_OUTER_ENVELOPE_COPY"
    split_surface = create_rocker_split_surface(
        work_component, source_body, split_points_mm, "UPPER_BOTTOM_ROCKER_SPLIT"
    )
    split_input = work_component.features.splitBodyFeatures.createInput(copied_body, split_surface, True)
    work_component.features.splitBodyFeatures.add(split_input)
    solid_bodies = [
        work_component.bRepBodies.item(index)
        for index in range(work_component.bRepBodies.count)
        if work_component.bRepBodies.item(index).isSolid
    ]
    if len(solid_bodies) != 2:
        raise ValueError(
            "Expected exactly two solid bodies after splitting the sole envelope, found {}."
            .format(len(solid_bodies))
        )
    split_surface.isLightBulbOn = False
    first, second = solid_bodies
    lower_body, upper_body = sorted(
        (first, second),
        key=lambda body: body.preciseBoundingBox.minPoint.z + body.preciseBoundingBox.maxPoint.z,
    )
    lower_body = lower_body.createComponent()
    lower_component = lower_body.parentComponent
    lower_component.name = "BOTTOM_MIDSOLE_" + candidate_id
    upper_body = upper_body.createComponent()
    upper_component = upper_body.parentComponent
    upper_component.name = "UPPER_MIDSOLE_" + candidate_id
    return lower_body, upper_body, lower_component, upper_component


def _cut_pocket(target_body, pocket_body):
    """Subtract a copied clearance tool from one TPU midsole component."""
    target_component = target_body.parentComponent
    copied_tool = _copy_body(target_component, pocket_body)
    tools = adsk.core.ObjectCollection.create()
    tools.add(copied_tool)
    combine_input = target_component.features.combineFeatures.createInput(target_body, tools)
    combine_input.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
    combine_input.isKeepToolBodies = False
    combine_input.isNewComponent = False
    target_component.features.combineFeatures.add(combine_input)


def _export_component(design, component, output_directory, stem):
    """Export an editable STEP and printer-ready 3MF for exactly one component."""
    manager = design.exportManager
    step_options = manager.createSTEPExportOptions(os.path.join(output_directory, stem + ".step"), component)
    manager.execute(step_options)
    three_mf_options = manager.createC3MFExportOptions(component, os.path.join(output_directory, stem + ".3mf"))
    manager.execute(three_mf_options)


def run(context):
    """Create and export one baseline assembly without changing the selected source body."""
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            raise ValueError("Open the matching sole-envelope.step in Fusion's Design workspace first.")
        candidate, candidate_path = _load_candidate(ui)
        if not candidate:
            return
        selected = ui.selectEntity("Select the closed sole-envelope B-Rep body", "Bodies")
        source_body = adsk.fusion.BRepBody.cast(selected.entity)
        if not source_body or not source_body.isSolid:
            raise ValueError("Select one closed solid B-Rep body, not a mesh or surface.")
        _validate_selected_body(candidate, source_body)

        plan = build_baseline_plan(candidate, _bounds_mm(source_body))
        candidate_id = candidate["candidate"]["candidate_id"]
        root = design.rootComponent
        assembly = _new_component(root, "SOLE_AI_" + candidate_id)
        plate_thickness_mm = plan.plate_top_z_mm - plan.plate_bottom_z_mm
        deepest_center_z_mm = (plan.plate_bottom_z_mm + plan.plate_top_z_mm) / 2.0
        rocker_path = build_rocker_path(
            source_body,
            deepest_center_z_mm,
            plan.plate_heel_relief_percent,
            plan.plate_toe_end_percent,
            plan.plate_rocker_follow_ratio,
            plan.rocker_profile_sample_count,
        )
        lower_body, upper_body, lower_component, upper_component = _split_to_midsole_components(
            assembly, source_body, rocker_path.split_points_mm, candidate_id
        )
        plate_component = _new_component(assembly, "PC_PLATE_" + candidate_id)
        plate_body = create_rocker_following_body(
            plate_component,
            source_body,
            rocker_path.plate_points_mm,
            plate_thickness_mm,
            plan.plate_transverse_scale, plan.plate_longitudinal_scale,
            plan.plate_heel_cap_radius_mm,
            "PC_PLATE_HEEL_RELIEVED_ROCKER_FOLLOWING",
        )
        pocket_component = _new_component(assembly, "INTERNAL_POCKET_TOOL_" + candidate_id)
        pocket_body = create_rocker_following_body(
            pocket_component,
            source_body,
            rocker_path.plate_points_mm,
            plan.pocket_top_z_mm - plan.pocket_bottom_z_mm,
            plan.pocket_transverse_scale, plan.pocket_longitudinal_scale,
            plan.plate_heel_cap_radius_mm + 0.2,
            "PC_PLATE_CLEARANCE_TOOL",
        )
        _cut_pocket(lower_body, pocket_body)
        _cut_pocket(upper_body, pocket_body)
        pocket_body.isLightBulbOn = False
        source_body.isLightBulbOn = False

        output_directory = os.path.join(os.path.dirname(candidate_path), "geometry", candidate_id)
        os.makedirs(output_directory, exist_ok=True)
        _export_component(design, lower_component, output_directory, "bottom-midsole")
        _export_component(design, upper_component, output_directory, "upper-midsole")
        _export_component(design, plate_component, output_directory, "pc-plate")
        archive = design.exportManager.createFusionArchiveExportOptions(
            os.path.join(output_directory, "sole-ai-assembly.f3d"), assembly
        )
        design.exportManager.execute(archive)
        with open(os.path.join(output_directory, "generation-report.json"), "w", encoding="utf-8") as report:
            json.dump(
                {
                    "candidate_id": candidate_id,
                    "status": "baseline_brep_generated",
                    "plate_profile": "heel_relief_rocker_following",
                    "plate_planform": "scaled_from_actual_sole_brep",
                    "toe_axis_direction": plan.toe_axis_direction,
                    "plate_heel_relief_percent": plan.plate_heel_relief_percent,
                    "plate_toe_end_percent": plan.plate_toe_end_percent,
                    "plate_rocker_follow_ratio": plan.plate_rocker_follow_ratio,
                    "plate_transverse_scale": plan.plate_transverse_scale,
                    "plate_longitudinal_scale": plan.plate_longitudinal_scale,
                    "deepest_split_z_mm": rocker_path.deepest_center_z_mm,
                },
                report,
                indent=2,
            )
        ui.messageBox("Generated baseline B-Rep components in:\n" + output_directory)
    except:
        if ui:
            ui.messageBox("Sole AI generation failed:\n" + traceback.format_exc())


def stop(context):
    """Fusion calls stop for add-ins; the standalone script has no persistent handlers."""
    pass
