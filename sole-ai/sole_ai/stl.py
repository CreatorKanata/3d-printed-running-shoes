# sole_ai.stl: small, dependency-free binary-STL validator for immutable input meshes.
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import struct

from .config import MAX_STL_TRIANGLES, STL_HEADER_BYTES, STL_TRIANGLE_BYTES


class StlValidationError(ValueError):
    """Raised when an input mesh is not a usable binary STL envelope."""


@dataclass(frozen=True)
class MeshBounds:
    """Axis-aligned bounds in the mesh's declared millimetre coordinate system."""

    minimum: tuple[float, float, float]
    maximum: tuple[float, float, float]
    triangle_count: int

    @property
    def dimensions(self) -> tuple[float, float, float]:
        return tuple(high - low for low, high in zip(self.minimum, self.maximum))


@dataclass(frozen=True)
class SoleAxes:
    """Physical sole directions inferred from a mesh's three source coordinates."""

    longitudinal_axis: str
    transverse_axis: str
    vertical_axis: str
    longitudinal_length_mm: float
    transverse_width_mm: float
    stack_height_mm: float


def infer_sole_axes(bounds: MeshBounds) -> SoleAxes:
    """Infer sole directions by dimension instead of assuming a CAD export frame.

    The input STEP/STL pair currently uses X=width, Y=length, and Z=height.
    Detecting that relation keeps this project compatible with common Fusion exports
    while preserving the original file rather than silently rotating it.
    """
    axis_names = ("x", "y", "z")
    ordered_axes = sorted(range(3), key=lambda axis: bounds.dimensions[axis])
    vertical, transverse, longitudinal = ordered_axes
    dimensions = bounds.dimensions
    return SoleAxes(
        longitudinal_axis=axis_names[longitudinal],
        transverse_axis=axis_names[transverse],
        vertical_axis=axis_names[vertical],
        longitudinal_length_mm=dimensions[longitudinal],
        transverse_width_mm=dimensions[transverse],
        stack_height_mm=dimensions[vertical],
    )


def read_binary_stl_bounds(path: Path) -> MeshBounds:
    """Return bounds for a binary STL while rejecting corrupt or ambiguous input.

    STL has no inherent unit metadata. This project therefore treats every input as
    millimetres by contract and catches implausible sole dimensions separately.
    """
    if path.suffix.lower() != ".stl":
        raise StlValidationError(f"Expected an .stl mesh, received: {path.name}")

    file_size = path.stat().st_size
    if file_size < STL_HEADER_BYTES:
        raise StlValidationError(f"STL is too small to contain a header: {path}")

    with path.open("rb") as mesh_file:
        mesh_file.read(80)
        triangle_count_bytes = mesh_file.read(4)
        if len(triangle_count_bytes) != 4:
            raise StlValidationError(f"STL has no triangle count: {path}")
        triangle_count = struct.unpack("<I", triangle_count_bytes)[0]

        if triangle_count > MAX_STL_TRIANGLES:
            raise StlValidationError(
                f"STL declares {triangle_count:,} triangles; limit is {MAX_STL_TRIANGLES:,}."
            )
        expected_size = STL_HEADER_BYTES + triangle_count * STL_TRIANGLE_BYTES
        if file_size != expected_size:
            raise StlValidationError(
                "Only complete binary STL files are supported; "
                f"expected {expected_size:,} bytes from the triangle count but found {file_size:,}."
            )

        minimum = [math.inf, math.inf, math.inf]
        maximum = [-math.inf, -math.inf, -math.inf]
        triangle_format = struct.Struct("<12fH")
        for index in range(triangle_count):
            data = mesh_file.read(STL_TRIANGLE_BYTES)
            if len(data) != STL_TRIANGLE_BYTES:
                raise StlValidationError(f"STL ended inside triangle {index}: {path}")
            values = triangle_format.unpack(data)
            vertices = (values[3:6], values[6:9], values[9:12])
            for vertex in vertices:
                if not all(math.isfinite(coordinate) for coordinate in vertex):
                    raise StlValidationError(f"STL contains non-finite vertex values: {path}")
                for axis, coordinate in enumerate(vertex):
                    minimum[axis] = min(minimum[axis], coordinate)
                    maximum[axis] = max(maximum[axis], coordinate)

    if triangle_count == 0:
        raise StlValidationError(f"STL contains no triangles: {path}")
    return MeshBounds(tuple(minimum), tuple(maximum), triangle_count)
