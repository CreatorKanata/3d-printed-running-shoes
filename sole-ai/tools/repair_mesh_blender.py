# tools.repair_mesh_blender: close implicit lattice STL surfaces with voxel remeshing.
"""Repair one lattice mesh in Blender and export a clean binary STL."""
from __future__ import annotations

from pathlib import Path
import sys

import bpy


def main() -> None:
    """Voxel-remesh one STL at a tolerance below one sixth of its minimum wall."""
    source, target, voxel_text = sys.argv[sys.argv.index("--") + 1 :]
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    if not hasattr(bpy.ops.import_mesh, "stl"):
        bpy.ops.preferences.addon_enable(module="io_mesh_stl")
    bpy.ops.import_mesh.stl(filepath=str(Path(source).resolve()))
    item = bpy.context.object
    item.data.remesh_voxel_size = float(voxel_text)
    item.data.remesh_voxel_adaptivity = 0.0
    bpy.context.view_layer.objects.active = item
    item.select_set(True)
    bpy.ops.object.voxel_remesh()
    # Remove duplicate triangles produced where the voxel surface touches an
    # envelope boundary, then fill the rare residual open contour.
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=float(voxel_text) * 0.05)
    bpy.ops.mesh.delete_loose()
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.mesh.select_non_manifold(
        extend=False,
        use_wire=True,
        use_boundary=True,
        use_multi_face=False,
        use_non_contiguous=False,
        use_verts=True,
    )
    bpy.ops.mesh.fill_holes(sides=32)
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.export_mesh.stl(
        filepath=str(Path(target).resolve()),
        use_selection=True,
        ascii=False,
    )


if __name__ == "__main__":
    main()
