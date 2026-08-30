# tests.test_design: regression coverage for reproducible, bounded design candidates.
from __future__ import annotations

import unittest

from sole_ai.design import sample_candidates


class CandidateSamplingTests(unittest.TestCase):
    """V1 candidate exploration must honour every committed design constraint."""

    def test_sampling_is_reproducible_and_bounded(self) -> None:
        bounds = {
            "plate_offset_from_split_mm": [-0.4, 0.4],
            "plate_thickness_mm": [1.2, 2.4],
            "toe_spring_start_percent": [65.0, 78.0],
            "toe_spring_rise_mm": [3.0, 7.0],
            "upper_density": [0.24, 0.58],
            "bottom_density": [0.30, 0.72],
            "split_height_percent": [45.0, 52.0],
            "plate_corner_radius_mm": [8.0, 14.0],
        }
        first = sample_candidates(side="left", bounds=bounds, count=3, seed=42)
        second = sample_candidates(side="left", bounds=bounds, count=3, seed=42)

        self.assertEqual(first, second)
        self.assertEqual(len(first), 3)
        for candidate in first:
            self.assertTrue(-0.4 <= candidate.plate_offset_from_split_mm <= 0.4)
            self.assertTrue(0.24 <= candidate.upper_density <= 0.58)
            self.assertTrue(0.30 <= candidate.bottom_density <= 0.72)
            self.assertTrue(65.0 <= candidate.toe_spring_start_percent <= 78.0)
            self.assertTrue(3.0 <= candidate.toe_spring_rise_mm <= 7.0)
            self.assertTrue(8.0 <= candidate.plate_corner_radius_mm <= 14.0)

    def test_candidate_locks_the_supplied_outer_geometry(self) -> None:
        bounds = {
            "plate_offset_from_split_mm": [-0.4, 0.4],
            "plate_thickness_mm": [1.2, 2.4],
            "toe_spring_start_percent": [65.0, 78.0],
            "toe_spring_rise_mm": [3.0, 7.0],
            "upper_density": [0.24, 0.58],
            "bottom_density": [0.30, 0.72],
            "split_height_percent": [45.0, 52.0],
            "plate_corner_radius_mm": [8.0, 14.0],
        }
        document = sample_candidates(side="left", bounds=bounds, count=1, seed=42)[0].as_dict()

        self.assertEqual(document["outer_geometry"]["mode"], "locked_from_input_mesh")
        self.assertNotIn("heel_stack_mm", document["fusion_parameters"])
        self.assertNotIn("rocker_radius_mm", document["fusion_parameters"])
        self.assertEqual(document["fusion_parameters"]["plate_profile"], "rocker_following")
        self.assertIn("plate_corner_radius_mm", document["fusion_parameters"])
        self.assertEqual(document["fusion_parameters"]["plate_heel_relief_percent"], 18.0)
        self.assertEqual(document["fusion_parameters"]["plate_heel_cap_radius_mm"], 40.0)
        self.assertEqual(document["fusion_parameters"]["plate_toe_end_percent"], 93.0)
        self.assertEqual(document["fusion_parameters"]["plate_rocker_follow_ratio"], 0.45)
