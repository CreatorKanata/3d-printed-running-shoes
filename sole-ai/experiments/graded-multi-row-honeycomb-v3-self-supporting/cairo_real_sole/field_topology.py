# cairo_real_sole.field_topology: connectivity gate for sampled sole material.
"""Remove only tiny isolated field noise before it becomes a closed STL island."""
from __future__ import annotations

from collections import deque


def prune_tiny_components(field) -> dict[str, object]:
    """Keep one connected core, pruning only components below the noise limit."""
    nx, ny, nz = len(field), len(field[0]), len(field[0][0])
    yz = ny * nz
    inside = bytearray(nx * yz)
    for ix, x_slice in enumerate(field):
        for iy, column in enumerate(x_slice):
            base = ix * yz + iy * nz
            for iz, value in enumerate(column):
                if value <= 0.0:
                    inside[base + iz] = 1
    components = []
    for start in range(len(inside)):
        if not inside[start]:
            continue
        inside[start] = 0
        queue = deque([start])
        component = []
        while queue:
            index = queue.popleft()
            component.append(index)
            ix, remainder = divmod(index, yz)
            iy, iz = divmod(remainder, nz)
            neighbours = []
            if ix:
                neighbours.append(index - yz)
            if ix + 1 < nx:
                neighbours.append(index + yz)
            if iy:
                neighbours.append(index - nz)
            if iy + 1 < ny:
                neighbours.append(index + nz)
            if iz:
                neighbours.append(index - 1)
            if iz + 1 < nz:
                neighbours.append(index + 1)
            for neighbour in neighbours:
                if inside[neighbour]:
                    inside[neighbour] = 0
                    queue.append(neighbour)
        components.append(component)
    if not components:
        raise ValueError("The sampled sole contains no printable material.")
    components.sort(key=len, reverse=True)
    noise_limit = max(64, round(len(components[0]) * 0.001))
    if len(components) > 1 and len(components[1]) > noise_limit:
        raise ValueError(
            "The sampled sole contains a second structural-size disconnected body."
        )
    removed = components[1:]
    for component in removed:
        for index in component:
            ix, remainder = divmod(index, yz)
            iy, iz = divmod(remainder, nz)
            field[ix][iy][iz] = 1.0
    return {
        "components_before": len(components),
        "components_after": 1,
        "removed_components": len(removed),
        "removed_samples": sum(map(len, removed)),
        "largest_component_samples": len(components[0]),
        "noise_limit_samples": noise_limit,
    }

