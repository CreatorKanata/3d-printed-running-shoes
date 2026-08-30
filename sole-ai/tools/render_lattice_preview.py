# tools.render_lattice_preview: Blender visual QA for generated sole meshes.
"""Render assembled upper/lower STL meshes from an oblique side view."""
from __future__ import annotations

import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def _material(name: str, color) -> bpy.types.Material:
    """Create a slightly translucent TPU-like review material."""
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*color, 1.0)
    material.metallic = 0.02
    material.roughness = 0.34
    return material


def _look_at(camera, target: Vector) -> None:
    """Point one Blender camera at the assembled sole centre."""
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def _bounds(objects) -> tuple[Vector, Vector]:
    """Return world-space bounds for all imported mesh objects."""
    points = [item.matrix_world @ Vector(corner) for item in objects for corner in item.bound_box]
    return (
        Vector(tuple(min(point[axis] for point in points) for axis in range(3))),
        Vector(tuple(max(point[axis] for point in points) for axis in range(3))),
    )


def main() -> None:
    """Import two STLs, style them, and render a deterministic PNG."""
    lower_path, upper_path, output_path = (
        Path(value).resolve() for value in sys.argv[sys.argv.index("--") + 1 :]
    )
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    meshes = []
    if not hasattr(bpy.ops.import_mesh, "stl"):
        bpy.ops.preferences.addon_enable(module="io_mesh_stl")
    for path, name, color in (
        (lower_path, "LOWER_CELLULAR_LATTICE", (0.025, 0.38, 0.80)),
        (upper_path, "UPPER_CELLULAR_LATTICE", (0.05, 0.68, 1.0)),
    ):
        bpy.ops.import_mesh.stl(filepath=str(path))
        item = bpy.context.object
        item.name = name
        for polygon in item.data.polygons:
            polygon.use_smooth = True
        item.data.materials.append(_material(name + "_TPU", color))
        meshes.append(item)

    low, high = _bounds(meshes)
    centre = (low + high) / 2.0
    size = high - low

    bpy.ops.object.camera_add(location=centre + Vector((size.x * 4.2, -size.y * 0.10, size.z * 0.65)))
    camera = bpy.context.object
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = size.y * 1.12
    _look_at(camera, centre)
    bpy.context.scene.camera = camera

    for location, energy, scale in (
        (centre + Vector((160.0, -120.0, 230.0)), 2200.0, 160.0),
        (centre + Vector((-180.0, 80.0, 100.0)), 1700.0, 130.0),
        (centre + Vector((40.0, 220.0, -40.0)), 1100.0, 100.0),
    ):
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.data.energy = energy
        light.data.shape = "DISK"
        light.data.size = scale
        _look_at(light, centre)

    bpy.ops.mesh.primitive_plane_add(size=max(size) * 4.0, location=(centre.x, centre.y, low.z - 2.0))
    floor = bpy.context.object
    floor.data.materials.append(_material("FLOOR", (0.055, 0.065, 0.085)))

    scene = bpy.context.scene
    # Workbench makes the open branches and voids easier to inspect than a dark
    # photoreal material, especially at the coarse Fusion-preview resolution.
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.use_gtao = True
    scene.eevee.gtao_distance = 3.0
    scene.eevee.gtao_factor = 1.25
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(output_path)
    scene.render.film_transparent = False
    scene.world.color = (0.035, 0.045, 0.065)
    scene.view_settings.look = "Medium High Contrast"
    bpy.ops.wm.save_as_mainfile(filepath=str(output_path.with_suffix(".blend")))
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
