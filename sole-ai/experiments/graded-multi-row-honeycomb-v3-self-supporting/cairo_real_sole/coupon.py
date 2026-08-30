# cairo_real_sole.coupon: make a 30 mm V3.2 rail-free printability box.
"""Generate a cubic coupon from the same field used by the left sole."""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
import json
from pathlib import Path

from .config import CouponConfig, SoleCellConfig
from .generate import _load_project_api, generate_real_sole


Point3 = tuple[float, float, float]
Triangle3 = tuple[Point3, Point3, Point3]


def coupon_sole_config(coupon: CouponConfig) -> SoleCellConfig:
    """Return sample-only settings with both stiff longitudinal rails disabled."""
    return replace(
        SoleCellConfig(),
        preview_step_mm=coupon.preview_step_mm,
        production_step_mm=coupon.production_step_mm,
        lateral_envelope_inset_mm=coupon.lateral_envelope_inset_mm,
        longitudinal_rail_count=0,
    )


def cube_triangles(size_mm: float) -> list[Triangle3]:
    """Return a closed twelve-triangle source volume at 0..size on every axis."""
    low, high = 0.0, size_mm
    p000, p100 = (low, low, low), (high, low, low)
    p010, p110 = (low, high, low), (high, high, low)
    p001, p101 = (low, low, high), (high, low, high)
    p011, p111 = (low, high, high), (high, high, high)
    return [
        (p000, p110, p100), (p000, p010, p110),
        (p001, p101, p111), (p001, p111, p011),
        (p000, p100, p101), (p000, p101, p001),
        (p010, p011, p111), (p010, p111, p110),
        (p000, p001, p011), (p000, p011, p010),
        (p100, p110, p111), (p100, p111, p101),
    ]


def generate_coupon(
    output_stl: Path,
    sole_ai_root: Path,
    *,
    preview: bool = False,
    coupon: CouponConfig | None = None,
) -> dict[str, object]:
    """Clip the exact V3.2 rail-free cell system to one nominal 30 mm cube."""
    coupon = coupon or CouponConfig()
    coupon.validate()
    output_stl.parent.mkdir(parents=True, exist_ok=True)
    source_stl = output_stl.with_name(output_stl.stem + "-source-volume.stl")
    api = _load_project_api(sole_ai_root)
    is_watertight, write_binary_stl = api[3], api[4]
    source = cube_triangles(coupon.size_mm)
    if not is_watertight(source):
        raise RuntimeError("The analytic coupon source cube is not watertight.")
    write_binary_stl(source_stl, source, "30 mm coupon source volume")

    sole_config = coupon_sole_config(coupon)
    report = generate_real_sole(
        source_stl,
        output_stl,
        sole_ai_root,
        preview=preview,
        config=sole_config,
    )
    report["design"] = "Rail-Free Honeycomb V3.2 30 mm printability box"
    report["architecture"] = "graded-multi-row-honeycomb-v3-2-rail-free-coupon"
    report["units"] = "millimetres"
    report["nominal_box_mm"] = [coupon.size_mm] * 3
    report["print_orientation"] = "Place the lower 30 x 30 mm face on the build plate."
    report["coupon_config"] = asdict(coupon)
    report["purpose"] = (
        "Support-free geometry and stiffness comparison; not a running-load proof."
    )
    report["design_note"] = (
        "The two longitudinal reinforcement rails are intentionally removed. "
        "Only point-top honeycomb walls and 1.5 mm upper/lower skins remain. "
        "This sample measures the flexibility change reported after printing V3.1."
    )
    output_stl.with_suffix(".json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    """Generate the box from explicit output and project paths."""
    parser = argparse.ArgumentParser(description="Generate the 30 mm V3.2 coupon.")
    parser.add_argument("output_stl", type=Path)
    parser.add_argument("--sole-ai-root", type=Path, required=True)
    parser.add_argument("--preview", action="store_true")
    arguments = parser.parse_args()
    report = generate_coupon(
        arguments.output_stl,
        arguments.sole_ai_root,
        preview=arguments.preview,
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
