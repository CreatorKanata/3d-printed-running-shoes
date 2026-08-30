# cairo_real_sole.config: V3 honeycomb, material, and mesh settings.
"""Centralise every tunable for the left graded multi-row honeycomb sole."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SoleCellConfig:
    """Millimetre settings for the full-size TPE-83A V3 candidate."""

    wall_mm: float = 1.5
    dense_wall_mm: float = 1.8
    honeycomb_edge_mm: float = 5.5
    honeycomb_bin_mm: float = 12.0
    longitudinal_rail_count: int = 2
    longitudinal_rail_mm: float = 1.5
    anchor_skin_mm: float = 1.5
    junction_blend_mm: float = 0.25
    thin_interval_solid_mm: float = 1.5
    lateral_envelope_inset_mm: float = 0.2
    rail_height_fraction_low: float = 0.28
    rail_height_fraction_high: float = 0.72
    heel_dense_end_fraction: float = 0.22
    heel_transition_end_fraction: float = 0.40
    forefoot_transition_start_fraction: float = 0.55
    forefoot_dense_start_fraction: float = 0.72
    preview_step_mm: float = 0.90
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
        if self.honeycomb_edge_mm < 3.0 * self.dense_wall_mm:
            raise ValueError("Honeycomb openings need space between 1.8 mm walls.")
        if not self.wall_mm <= self.dense_wall_mm <= 2.0:
            raise ValueError("V3 walls must grade only from 1.5 to at most 2.0 mm.")
        if self.longitudinal_rail_count < 2:
            raise ValueError("Running V2 needs at least two anti-buckling rails.")
        if self.longitudinal_rail_mm < self.wall_mm:
            raise ValueError("Anti-buckling rails cannot be thinner than cell walls.")
        if self.anchor_skin_mm < self.wall_mm:
            raise ValueError("Load-spreading skins cannot be thinner than cell walls.")
        if not 0.0 <= self.lateral_envelope_inset_mm <= 0.5:
            raise ValueError("The lateral inset is only a raster-envelope guard.")
        if not (
            0.0
            < self.rail_height_fraction_low
            < self.rail_height_fraction_high
            < 1.0
        ):
            raise ValueError("Rails must stay inside the honeycomb height.")
        fractions = (
            self.heel_dense_end_fraction,
            self.heel_transition_end_fraction,
            self.forefoot_transition_start_fraction,
            self.forefoot_dense_start_fraction,
        )
        if tuple(sorted(fractions)) != fractions or not 0.0 < fractions[0] < fractions[-1] < 1.0:
            raise ValueError("Density transition fractions must increase along the sole.")
        if not 0.0 < self.grid_phase_fraction < 1.0:
            raise ValueError("The scalar-grid phase must stay inside one cell.")
        if not 0.0 < self.export_cleanup_mm <= 0.01:
            raise ValueError("Export cleanup may remove only microscopic slivers.")
        if not 10.0 * self.export_cleanup_mm < self.isosurface_guard_mm < self.wall_mm / 100.0:
            raise ValueError("Isosurface guard must remain small but exceed QA tolerance.")
        if not 0.005 <= self.surface_bias_mm <= 0.05:
            raise ValueError("Surface bias must stay negligible beside a 1.5 mm wall.")
        if self.material_density_g_cm3 <= 0.0 or self.material_shore_a != 83.0:
            raise ValueError("This V3 configuration is qualified only for the named TPE-83A.")
