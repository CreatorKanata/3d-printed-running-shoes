# fusion_addin.mesh_geometry: import and trim exposed Gyroid mesh bodies.
"""Convert B-Reps to mesh masks and intersect a Gyroid with each midsole half."""
from __future__ import annotations

import adsk.fusion


def import_mesh_body(component, path: str, name: str):
    """Import one STL into a parametric component through a temporary base feature."""
    base_feature = component.features.baseFeatures.add()
    base_feature.startEdit()
    bodies = component.meshBodies.add(path, adsk.fusion.MeshUnits.MillimeterMeshUnit, base_feature)
    base_feature.finishEdit()
    if bodies.count != 1:
        raise ValueError("Expected one STL mesh body, found {}.".format(bodies.count))
    bodies.item(0).name = name
    return bodies.item(0)


def brep_to_mesh_body(component, brep_body, name: str):
    """Create a low-quality triangular mesh mask from one B-Rep body."""
    calculator = brep_body.meshManager.createMeshCalculator()
    calculator.setQuality(adsk.fusion.TriangleMeshQualityOptions.LowQualityTriangleMesh)
    mesh = calculator.calculate()
    body = component.meshBodies.addByTriangleMeshData(
        mesh.nodeCoordinatesAsDouble,
        mesh.nodeIndices,
        [],
        [],
    )
    if body is None:
        raise ValueError("Fusion could not create the B-Rep mesh mask.")
    body.name = name
    return body


def _mesh_boolean(component, target_mesh, tool_meshes, operation, name: str):
    """Run one enhanced mesh Boolean and return its post-operation target body."""
    combine_input = component.features.meshCombineFeatures.createInput(target_mesh, tool_meshes)
    combine_input.meshCombineOperationType = operation
    combine_input.meshCombineAlgorithmType = (
        adsk.fusion.MeshCombineAlgorithmTypes.EnhancedMeshCombineAlgorithmType
    )
    feature = component.features.meshCombineFeatures.add(combine_input)
    # MeshCombineFeature exposes the post-Boolean body as targetBody; unlike
    # B-Rep features it does not have a meshBodies result collection.
    result = feature.targetBody
    result.name = name
    return result


def intersect_mesh(component, target_mesh, brep_envelope, name: str):
    """Trim a Gyroid mesh to a closed B-Rep envelope using enhanced mesh Boolean."""
    tool_mesh = brep_to_mesh_body(component, brep_envelope, name + "_MASK")
    return _mesh_boolean(
        component,
        target_mesh,
        [tool_mesh],
        adsk.fusion.MeshCombineOperationTypes.IntersectMeshCombineType,
        name,
    )


def subtract_brep_regions(component, target_mesh, solid_bodies, name: str):
    """Remove all solid TPU regions from a Gyroid in one mesh Boolean feature."""
    tools = [
        brep_to_mesh_body(component, body, name + "_TOOL_{:02d}".format(index))
        for index, body in enumerate(solid_bodies, start=1)
    ]
    return _mesh_boolean(
        component,
        target_mesh,
        tools,
        adsk.fusion.MeshCombineOperationTypes.CutMeshCombineType,
        name,
    )
