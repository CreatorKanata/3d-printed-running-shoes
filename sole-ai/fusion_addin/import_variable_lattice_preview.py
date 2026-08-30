# fusion_addin.import_variable_lattice_preview: display grown sole lattice in Fusion.
"""Import the lightweight biological-growth preview without calculating it in Fusion."""
from __future__ import annotations

import os
import sys
import traceback

import adsk.core
import adsk.fusion


SCRIPT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))
if SCRIPT_DIRECTORY not in sys.path:
    sys.path.insert(0, SCRIPT_DIRECTORY)

from mesh_geometry import import_mesh_body


def _new_component(parent, name: str):
    """Create one identity-transform child component."""
    occurrence = parent.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    occurrence.component.name = name
    return occurrence.component


def _preview_path(side: str, half: str) -> str:
    """Resolve one generated preview path without changing the source files."""
    return os.path.normpath(
        os.path.join(
            SCRIPT_DIRECTORY,
            "..",
            "outputs",
            side,
            "lattice",
            "organic-strut",
            "{}-organic-strut-preview.stl".format(half),
        )
    )


def run(context):
    """Prompt for a side and import only its already-generated preview meshes."""
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            raise ValueError("Open a Fusion Design document first.")
        side, cancelled = ui.inputBox("left or right", "Import growth lattice preview", "right")
        if cancelled:
            return
        side = side.strip().lower()
        if side not in ("left", "right"):
            raise ValueError("Side must be left or right.")
        assembly = _new_component(
            design.rootComponent, "{}_BIOLOGICAL_GROWTH_PREVIEW".format(side.upper())
        )
        lower_component = _new_component(assembly, "BOTTOM_MIDSOLE_GROWTH_PREVIEW")
        upper_component = _new_component(assembly, "UPPER_MIDSOLE_GROWTH_PREVIEW")
        lower = import_mesh_body(
            lower_component, _preview_path(side, "lower"), "LOWER_BIOLOGICAL_GROWTH"
        )
        upper = import_mesh_body(
            upper_component, _preview_path(side, "upper"), "UPPER_BIOLOGICAL_GROWTH"
        )
        app.activeViewport.fit()
        app.activeViewport.refresh()
        ui.messageBox(
            "Imported script-generated previews:\n"
            "Lower: {:,} triangles\nUpper: {:,} triangles".format(
                lower.mesh.triangleCount, upper.mesh.triangleCount
            )
        )
    except:
        if ui:
            ui.messageBox("Growth-lattice preview import failed:\n" + traceback.format_exc())


def stop(context):
    """The preview importer installs no persistent handlers."""
    pass
