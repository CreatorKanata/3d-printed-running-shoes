# tests.test_stl: regression coverage for binary-STL bounds and corruption detection.
from __future__ import annotations

from pathlib import Path
import struct
import tempfile
import unittest

from sole_ai.stl import StlValidationError, infer_sole_axes, read_binary_stl_bounds


def write_triangle(path: Path, vertices: tuple[tuple[float, float, float], ...]) -> None:
    """Write one valid binary STL triangle for isolated parser tests."""
    normal = (0.0, 0.0, 1.0)
    with path.open("wb") as output:
        output.write(b"test".ljust(80, b" "))
        output.write(struct.pack("<I", 1))
        output.write(struct.pack("<12fH", *normal, *vertices[0], *vertices[1], *vertices[2], 0))


class BinaryStlBoundsTests(unittest.TestCase):
    """The source mesh must have predictable dimensions before design exploration."""

    def test_reads_vertex_bounds(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "envelope.stl"
            write_triangle(path, ((-1.0, 2.0, 0.0), (3.0, -4.0, 6.0), (1.0, 8.0, -2.0)))
            bounds = read_binary_stl_bounds(path)

        self.assertEqual(bounds.minimum, (-1.0, -4.0, -2.0))
        self.assertEqual(bounds.maximum, (3.0, 8.0, 6.0))
        self.assertEqual(bounds.dimensions, (4.0, 12.0, 8.0))

    def test_rejects_non_binary_stl_size(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "envelope.stl"
            path.write_bytes(b"solid not-a-binary-stl")
            with self.assertRaises(StlValidationError):
                read_binary_stl_bounds(path)

    def test_infers_fusion_export_axes_from_bounds(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "envelope.stl"
            write_triangle(path, ((0.0, 0.0, 0.0), (91.0, 238.0, 44.0), (20.0, 100.0, 10.0)))
            axes = infer_sole_axes(read_binary_stl_bounds(path))

        self.assertEqual(axes.longitudinal_axis, "y")
        self.assertEqual(axes.transverse_axis, "x")
        self.assertEqual(axes.vertical_axis, "z")
        self.assertEqual(axes.longitudinal_length_mm, 238.0)
