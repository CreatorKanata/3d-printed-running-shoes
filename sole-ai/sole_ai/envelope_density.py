# sole_ai.envelope_density: smooth load-zone grading for full lattice volumes.
"""Blend sole zones without hard density seams or mirrored foot assumptions."""
from __future__ import annotations

import math

from .config import (
    ENVELOPE_LOAD_ARCH,
    ENVELOPE_LOAD_BASE,
    ENVELOPE_LOAD_FOREFOOT,
    ENVELOPE_LOAD_HEEL,
    ENVELOPE_LOAD_RIM_GAIN,
    ENVELOPE_LOAD_TOE,
)


Point = tuple[float, float, float]


def _gaussian(value: float, definition: tuple[float, float, float]) -> float:
    """Evaluate one configured longitudinal load zone."""
    center, width, gain = definition
    return gain * math.exp(-0.5 * ((value - center) / width) ** 2)


def load_fraction(point: Point, bounds) -> float:
    """Blend heel, arch, forefoot, toe, and rim density without hard borders."""
    longitudinal = (bounds.maximum[1] - point[1]) / bounds.dimensions[1]
    center_x = (bounds.minimum[0] + bounds.maximum[0]) / 2.0
    transverse = 2.0 * (point[0] - center_x) / bounds.dimensions[0]
    heel = _gaussian(longitudinal, ENVELOPE_LOAD_HEEL) * (
        0.65 + 0.35 * transverse**2
    )
    arch = _gaussian(longitudinal, ENVELOPE_LOAD_ARCH) * (
        0.70 + 0.30 * abs(transverse)
    )
    value = (
        ENVELOPE_LOAD_BASE
        + heel
        + arch
        + _gaussian(longitudinal, ENVELOPE_LOAD_FOREFOOT)
        + _gaussian(longitudinal, ENVELOPE_LOAD_TOE)
        + ENVELOPE_LOAD_RIM_GAIN * transverse**2
    )
    return max(0.0, min(1.0, value))
