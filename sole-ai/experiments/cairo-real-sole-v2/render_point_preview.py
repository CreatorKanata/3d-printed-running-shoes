# render_point_preview: dependency-light visual QA when local Blender cannot import STL.
"""Project dense STL surface samples into a shaded PNG with a depth buffer."""
from __future__ import annotations

import argparse
from pathlib import Path
import struct

import numpy as np
from PIL import Image, ImageFilter


def _read_binary_stl(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Read triangle vertices and stored normals from a binary STL."""
    with path.open("rb") as source:
        source.seek(80)
        count = struct.unpack("<I", source.read(4))[0]
    records = np.fromfile(
        path,
        dtype=np.dtype(
            [
                ("header", "V84"),
                ("records", [("normal", "<f4", 3), ("vertices", "<f4", (3, 3)), ("attr", "<u2")], count),
            ]
        ),
        count=1,
    )
    data = records["records"][0]
    return data["vertices"].astype(np.float64), data["normal"].astype(np.float64)


def render(source: Path, output: Path, width: int = 1400, height: int = 900) -> None:
    """Render one outer-side oblique view using vertices plus face centroids."""
    triangles, normals = _read_binary_stl(source)
    low = triangles.min(axis=(0, 1))
    high = triangles.max(axis=(0, 1))
    centre = (low + high) / 2.0
    size = high - low
    camera = centre + np.array((size[0] * 2.4, -size[1] * 0.70, size[2] * 2.1))
    forward = centre - camera
    forward /= np.linalg.norm(forward)
    right = np.cross(forward, np.array((0.0, 0.0, 1.0)))
    right /= np.linalg.norm(right)
    up = np.cross(right, forward)
    samples = np.concatenate((triangles.reshape(-1, 3), triangles.mean(axis=1)), axis=0)
    shades = np.concatenate((np.repeat(normals, 3, axis=0), normals), axis=0)
    relative = samples - camera
    horizontal = relative @ right
    vertical = relative @ up
    depth = relative @ forward
    span = max(horizontal.max() - horizontal.min(), (vertical.max() - vertical.min()) * width / height)
    scale = 0.92 * width / span
    px = np.rint((horizontal - (horizontal.min() + horizontal.max()) / 2.0) * scale + width / 2.0).astype(np.int32)
    py = np.rint(height / 2.0 - (vertical - (vertical.min() + vertical.max()) / 2.0) * scale).astype(np.int32)
    valid = (px >= 0) & (px < width) & (py >= 0) & (py < height) & (depth > 0)
    px, py, depth, shades = px[valid], py[valid], depth[valid], shades[valid]
    linear = py * width + px
    order = np.lexsort((depth, linear))
    linear_ordered = linear[order]
    first = np.concatenate(([True], linear_ordered[1:] != linear_ordered[:-1]))
    chosen = order[first]
    light = np.array((0.35, -0.45, 0.82))
    light /= np.linalg.norm(light)
    brightness = 0.48 + 0.48 * np.abs(shades[chosen] @ light)
    pixels = np.zeros((height * width, 3), dtype=np.uint8)
    background = np.array((18, 22, 31), dtype=np.uint8)
    pixels[:] = background
    base = np.array((214, 222, 231), dtype=np.float64)
    pixels[linear[chosen]] = np.clip(base * brightness[:, None], 0, 255).astype(np.uint8)
    image = Image.fromarray(pixels.reshape(height, width, 3), "RGB")
    # A tiny maximum filter fills sub-pixel gaps without closing real cell openings.
    image = image.filter(ImageFilter.MaxFilter(3))
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a binary STL point preview.")
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    render(arguments.source, arguments.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
