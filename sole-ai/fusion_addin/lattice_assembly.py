# fusion_addin.lattice_assembly: assemble exposed Gyroid and solid TPU regions.
"""Build the reviewable sole structure while preserving the approved PC plate."""
from __future__ import annotations

import adsk.core
import adsk.fusion

from mesh_geometry import import_mesh_body, intersect_mesh, subtract_brep_regions
from rocker_geometry import build_outsole_lower_zones
from structure_geometry import (
    copy_body,
    create_ground_skin_zones,
    create_interlock_keys,
    create_plate_support_shell,
    create_top_bonding_skin,
)


def _new_component(parent, name: str):
    """Create one identity-transform child component."""
    occurrence = parent.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    occurrence.component.name = name
    return occurrence.component


def build_lattice_assembly(
    parent_component,
    source_body,
    lower_source_body,
    upper_source_body,
    plate_source_body,
    pocket_source_body,
    rocker_path,
    plan,
    raw_gyroid_path: str,
    settings,
    name: str,
):
    """Build upper/lower Gyroid cores plus all required non-lattice TPU parts."""
    assembly = _new_component(parent_component, name)
    lower_component = _new_component(assembly, "BOTTOM_MIDSOLE_LATTICE")
    upper_component = _new_component(assembly, "UPPER_MIDSOLE_LATTICE")
    cradle_component = _new_component(assembly, "SOLID_TPU_PLATE_CRADLE")
    plate_component = _new_component(assembly, "APPROVED_PC_PLATE")

    lower_envelope = copy_body(lower_component, lower_source_body, "LOWER_LATTICE_ENVELOPE")
    upper_envelope = copy_body(upper_component, upper_source_body, "UPPER_LATTICE_ENVELOPE")
    plate = copy_body(plate_component, plate_source_body, "PC_PLATE_APPROVED_POSITION")

    outsole_zones = build_outsole_lower_zones(
        source_body,
        settings.STRUCTURE_PROFILE_SAMPLE_COUNT,
        settings.GROUND_SKIN_TRANSVERSE_ZONE_COUNT,
    )
    ground_skins = create_ground_skin_zones(
        lower_component,
        source_body,
        outsole_zones,
        settings.GROUND_SKIN_THICKNESS_MM,
        "GROUND_SKIN_{:.1f}MM".format(settings.GROUND_SKIN_THICKNESS_MM),
    )
    top_skin = create_top_bonding_skin(
        upper_component,
        source_body,
        settings.TOP_BONDING_SKIN_THICKNESS_MM,
        "TOP_BONDING_SKIN_{:.1f}MM".format(settings.TOP_BONDING_SKIN_THICKNESS_MM),
    )
    cradle, cradle_plan = create_plate_support_shell(
        cradle_component,
        source_body,
        pocket_source_body,
        rocker_path.plate_points_mm,
        plan.pocket_top_z_mm - plan.pocket_bottom_z_mm,
        plan.pocket_transverse_scale,
        plan.pocket_longitudinal_scale,
        plan.plate_heel_cap_radius_mm + 0.2,
        settings.PLATE_SUPPORT_THICKNESS_MM,
        "PLATE_CRADLE_{:.1f}MM_SOLID_TPU".format(settings.PLATE_SUPPORT_THICKNESS_MM),
    )
    key_positions = create_interlock_keys(
        lower_component,
        upper_component,
        source_body,
        rocker_path.split_points_mm,
        settings.INTERLOCK_KEY_HEIGHT_MM,
        settings.INTERLOCK_KEY_RADIUS_MM,
        settings.INTERLOCK_KEY_CLEARANCE_MM,
        settings.INTERLOCK_KEY_COUNT,
    )

    lower_raw = import_mesh_body(lower_component, raw_gyroid_path, "RAW_LATTICE_LOWER")
    lower_lattice = intersect_mesh(
        lower_component, lower_raw, lower_envelope, "LOWER_EXPOSED_LATTICE"
    )
    if settings.MESH_EXCLUSION_BOOLEAN:
        lower_lattice = subtract_brep_regions(
            lower_component,
            lower_lattice,
            list(ground_skins) + [cradle] + [entry[3] for entry in key_positions],
            "LOWER_LATTICE_WITH_SOLID_TPU_EXCLUSIONS",
        )
    upper_raw = import_mesh_body(upper_component, raw_gyroid_path, "RAW_LATTICE_UPPER")
    upper_lattice = intersect_mesh(
        upper_component, upper_raw, upper_envelope, "UPPER_EXPOSED_LATTICE"
    )
    if settings.MESH_EXCLUSION_BOOLEAN:
        upper_lattice = subtract_brep_regions(
            upper_component,
            upper_lattice,
            [top_skin, cradle] + [entry[5] for entry in key_positions],
            "UPPER_LATTICE_WITH_SOLID_TPU_EXCLUSIONS",
        )
    lower_envelope.isLightBulbOn = False
    upper_envelope.isLightBulbOn = False
    return {
        "assembly": assembly,
        "lower_component": lower_component,
        "upper_component": upper_component,
        "cradle_component": cradle_component,
        "plate_component": plate_component,
        "lower_lattice": lower_lattice,
        "upper_lattice": upper_lattice,
        "ground_skins": ground_skins,
        "top_skin": top_skin,
        "cradle": cradle,
        "plate": plate,
        "key_positions": key_positions,
        "cradle_plan": cradle_plan,
    }
