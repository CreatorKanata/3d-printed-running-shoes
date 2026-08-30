# tests.test_geometry_plan: regression coverage for Fusion-independent baseline geometry math.
from __future__ import annotations

import pathlib
import sys
import unittest

FUSION_ADDIN_DIRECTORY = pathlib.Path(__file__).resolve().parents[1] / "fusion_addin"
sys.path.insert(0, str(FUSION_ADDIN_DIRECTORY))

from geometry_plan import BoundsMm, build_baseline_plan


class BaselineGeometryPlanTests(unittest.TestCase):
    """The plate must cross the split and leave clearance without changing the exterior."""

    def test_builds_a_plate_and_pocket_at_the_split_surface(self) -> None:
        document = {
            "candidate": {
                "split_height_percent": 50.0,
                "plate_offset_from_split_mm": 0.0,
                "plate_thickness_mm": 2.0,
                "plate_profile": "rocker_following",
                "toe_spring_start_percent": 68.0,
                "toe_spring_rise_mm": 5.0,
                "plate_corner_radius_mm": 10.0,
            },
            "outer_geometry": {"mode": "locked_from_input_mesh"},
            "input_mesh": {"inferred_axes": {"longitudinal": "y", "transverse": "x", "vertical": "z"}},
        }
        plan = build_baseline_plan(document, BoundsMm((0.0, 0.0, -44.0), (91.0, 238.0, 0.0)))

        self.assertEqual(plan.split_z_mm, -22.0)
        self.assertLess(plan.plate_bottom_z_mm, plan.split_z_mm)
        self.assertGreater(plan.plate_top_z_mm, plan.split_z_mm)
        self.assertLess(plan.pocket_min_x_mm, plan.plate_min_x_mm)
        self.assertGreater(plan.pocket_max_y_mm, plan.plate_max_y_mm)
        self.assertEqual(plan.plate_profile, "rocker_following")
        self.assertAlmostEqual(plan.toe_spring_start_y_mm, 86.5136)
        self.assertEqual(plan.toe_spring_rise_mm, 5.0)
        self.assertEqual(plan.toe_axis_direction, "negative_y")
        self.assertEqual(plan.plate_corner_radius_mm, 10.0)
        self.assertEqual(plan.pocket_corner_radius_mm, 10.2)
        self.assertEqual(plan.plate_transverse_scale, 0.74)
        self.assertEqual(plan.plate_longitudinal_scale, 0.92)
        self.assertEqual(plan.plate_heel_relief_percent, 18.0)
        self.assertEqual(plan.plate_heel_cap_radius_mm, 40.0)
        self.assertEqual(plan.plate_toe_end_percent, 93.0)
        self.assertEqual(plan.plate_rocker_follow_ratio, 0.45)
        self.assertEqual(plan.rocker_profile_sample_count, 25)
        self.assertGreater(plan.pocket_transverse_scale, plan.plate_transverse_scale)
        self.assertGreater(plan.pocket_longitudinal_scale, plan.plate_longitudinal_scale)

    def test_rejects_a_plate_that_would_not_cross_the_split(self) -> None:
        document = {
            "candidate": {
                "split_height_percent": 50.0,
                "plate_offset_from_split_mm": 1.1,
                "plate_thickness_mm": 2.0,
                "plate_profile": "rocker_following",
                "toe_spring_start_percent": 68.0,
                "toe_spring_rise_mm": 5.0,
                "plate_corner_radius_mm": 10.0,
            },
            "outer_geometry": {"mode": "locked_from_input_mesh"},
            "input_mesh": {"inferred_axes": {"longitudinal": "y", "transverse": "x", "vertical": "z"}},
        }
        with self.assertRaises(ValueError):
            build_baseline_plan(document, BoundsMm((0.0, 0.0, -44.0), (91.0, 238.0, 0.0)))
