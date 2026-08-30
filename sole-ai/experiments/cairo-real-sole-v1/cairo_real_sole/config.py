# cairo_real_sole.config: print and geometry settings for the real-size sole.
"""Centralise every tunable that changes the printable Side-Reveal structure."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SoleCellConfig:
    """Millimetre settings for one full-size, support-conscious TPU candidate."""

    wall_mm: float = 1.2
    cell_pitch_mm: float = 22.0
    pitch_variation: float = 0.10
    shoulder_fraction: float = 0.54
    shoulder_variation: float = 0.035
    preview_step_mm: float = 0.80
    production_step_mm: float = 0.65
    padding_cells: int = 1
    surface_bias_mm: float = 0.01

    def validate(self, step_mm: float) -> None:
        """Reject settings that the scalar grid cannot represent reliably."""
        if self.wall_mm < 1.4 * step_mm:
            raise ValueError("The cell wall needs about two scalar-grid samples.")
        if self.cell_pitch_mm < 6.0 * self.wall_mm:
            raise ValueError("The requested cells are too dense for a fast-print core.")
        if not 0.45 <= self.shoulder_fraction <= 0.65:
            raise ValueError("Shoulders outside 45--65% lose the pentagonal opening.")
