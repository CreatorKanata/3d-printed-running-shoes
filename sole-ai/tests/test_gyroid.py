# tests.test_gyroid: regression coverage for dependency-free lattice generation.
from __future__ import annotations

from pathlib import Path
import struct
import tempfile
import unittest

from sole_ai.gyroid import _normal, _orient_direction, generate_gyroid_box


class GyroidGenerationTests(unittest.TestCase):
    """The Fusion lattice source must be a deterministic non-empty binary STL."""

    def test_generates_binary_stl_with_consistent_triangle_count(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "gyroid.stl"
            count = generate_gyroid_box(
                (0.0, 0.0, 0.0),
                (12.0, 12.0, 12.0),
                path,
                cell_size_mm=12.0,
                sheet_level=0.32,
                grid_step_mm=3.0,
            )
            data = path.read_bytes()

        self.assertGreater(count, 0)
        self.assertEqual(struct.unpack("<I", data[80:84])[0], count)
        self.assertEqual(len(data), 84 + 50 * count)

    def test_rejects_invalid_sheet_level(self) -> None:
        with self.assertRaises(ValueError):
            generate_gyroid_box((0, 0, 0), (10, 10, 10), Path("unused.stl"), sheet_level=1.0)

    def test_orients_surface_toward_the_positive_field(self) -> None:
        triangle = ((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), (1.0, 0.0, 0.0))
        oriented = _orient_direction(triangle, (0.0, 0.0, 1.0))

        self.assertGreater(_normal(oriented)[2], 0.0)
