# cairo_real_sole.config: print and geometry settings for the real-size sole.
"""Centralise every tunable that changes the printable Side-Reveal structure."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SoleCellConfig:
    """Millimetre settings for one full-size, support-conscious TPU candidate."""

    wall_mm: float = 1.5
    longitudinal_rail_count: int = 2
    longitudinal_rail_mm: float = 1.5
    anchor_skin_mm: float = 1.5
    junction_blend_mm: float = 0.25
    thin_interval_solid_mm: float = 1.5
    rail_height_fraction_low: float = 0.18
    rail_height_fraction_high: float = 0.50
    # V2 triples V1's ten transverse arches to about thirty on a 218 mm sole.
    cell_pitch_mm: float = 22.0 / 3.0
    pitch_variation: float = 0.10
    shoulder_fraction: float = 0.54
    shoulder_variation: float = 0.035
    preview_step_mm: float = 0.75
    production_step_mm: float = 0.70
    padding_cells: int = 1
    grid_phase_fraction: float = 0.38196601125
    export_cleanup_mm: float = 0.00001
    isosurface_guard_mm: float = 0.005
    surface_bias_mm: float = 0.01
    runner_mass_kg: float = 28.0
    running_peak_bodyweight: float = 3.0
    structural_safety_factor: float = 1.5
    material_name: str = "eSUN eLastic TPE-83A"
    material_density_g_cm3: float = 1.14
    material_shore_a: float = 83.0
    nozzle_temperature_min_c: float = 220.0
    nozzle_temperature_max_c: float = 250.0
    bed_temperature_min_c: float = 45.0
    bed_temperature_max_c: float = 60.0
    maximum_print_speed_mm_s: float = 50.0
    drying_temperature_c: float = 55.0
    minimum_drying_hours: float = 4.0

    @property
    def design_test_load_n(self) -> float:
        """Return the conservative single-foot vertical proof-load target."""
        return (
            self.runner_mass_kg
            * 9.81
            * self.running_peak_bodyweight
            * self.structural_safety_factor
        )

    def validate(self, step_mm: float) -> None:
        """Reject settings that the scalar grid cannot represent reliably."""
        if self.wall_mm < 1.4 * step_mm:
            raise ValueError("The cell wall needs about two scalar-grid samples.")
        if self.cell_pitch_mm < 4.0 * self.wall_mm:
            raise ValueError("The requested cells are too dense for a fast-print core.")
        if self.longitudinal_rail_count < 2:
            raise ValueError("Running V2 needs at least two anti-buckling rails.")
        if self.longitudinal_rail_mm < self.wall_mm:
            raise ValueError("Anti-buckling rails cannot be thinner than cell walls.")
        if self.anchor_skin_mm < self.wall_mm:
            raise ValueError("Load-spreading skins cannot be thinner than cell walls.")
        if not (
            0.0
            < self.rail_height_fraction_low
            < self.rail_height_fraction_high
            <= self.shoulder_fraction
        ):
            raise ValueError("Rails must terminate inside the vertical arch legs.")
        if not 0.0 < self.grid_phase_fraction < 1.0:
            raise ValueError("The scalar-grid phase must stay inside one cell.")
        if not 0.0 < self.export_cleanup_mm <= 0.01:
            raise ValueError("Export cleanup may remove only microscopic slivers.")
        if not 10.0 * self.export_cleanup_mm < self.isosurface_guard_mm < self.wall_mm / 100.0:
            raise ValueError("Isosurface guard must remain small but exceed QA tolerance.")
        if not 0.005 <= self.surface_bias_mm <= 0.05:
            raise ValueError("Surface bias must stay negligible beside a 1.5 mm wall.")
        if not 0.45 <= self.shoulder_fraction <= 0.65:
            raise ValueError("Shoulders outside 45--65% lose the pentagonal opening.")
        if self.material_density_g_cm3 <= 0.0 or self.material_shore_a != 83.0:
            raise ValueError("This V2 configuration is qualified only for the named TPE-83A.")
