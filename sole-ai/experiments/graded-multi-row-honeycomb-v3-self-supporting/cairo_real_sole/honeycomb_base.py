# cairo_real_sole.honeycomb_base: rail-free full sole from the new base STL.
"""Generate a side-reveal sole with 1.5 mm top and ground skins."""
from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path

from .config import SoleCellConfig
from .generate import generate_real_sole


def honeycomb_base_config() -> SoleCellConfig:
    """Keep the proven cells and skins while removing stiff internal rails."""
    return replace(
        SoleCellConfig(),
        longitudinal_rail_count=0,
        merge_vertical_source_intervals=False,
        plate_slot_enabled=True,
    )


def generate_honeycomb_base(
    source_stl: Path,
    output_stl: Path,
    sole_ai_root: Path,
    *,
    side: str,
    preview: bool = False,
) -> dict[str, object]:
    """Fill one supplied base volume without mirroring or adding side skins."""
    if side not in {"left", "right"}:
        raise ValueError("Side must be 'left' or 'right'.")
    config = honeycomb_base_config()
    report = generate_real_sole(
        source_stl,
        output_stl,
        sole_ai_root,
        preview=preview,
        config=config,
    )
    report.update(
        {
            "architecture": "honeycomb-base-v3-3-plate-pocket-side-reveal",
            "design": "Plate-Pocket Honeycomb Sole from the supplied base STL",
            "side": side,
            "source_filename": source_stl.name,
            "lower_honeycomb_top_skin_mm": config.anchor_skin_mm,
            "ground_skin_mm": config.anchor_skin_mm,
            "solid_side_wall_count": 0,
            "side_reveal": True,
            "longitudinal_reinforcement_wall_count": 0,
            "source_vertical_band_count": report["vertical_band_count"],
            "plate_slot_thickness_mm": config.plate_slot_expected_mm,
            "plate_slot_perimeter_wall_mm": config.plate_slot_wall_mm,
            "upper_region": "preserved solid from the supplied base STL",
            "design_note": (
                "The exact supplied base STL defines the independent foot shape. "
                "The material above the nested 2.2 mm plate-slot cutter remains "
                "solid instead of becoming honeycomb. Below it, point-top cells "
                "receive a 1.5 mm ground skin and a 1.5 mm pocket-floor skin. "
                "A 1.5 mm solid perimeter wall encloses the slot for a pause-and-"
                "insert print. No lateral skins or longitudinal rails are added "
                "to the lower honeycomb. This is a print-test candidate, not a "
                "validated running structure."
            ),
        }
    )
    output_stl.with_suffix(".json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    """Generate one base-derived left or right sole from explicit paths."""
    parser = argparse.ArgumentParser(
        description="Generate a rail-free side-reveal honeycomb sole."
    )
    parser.add_argument("source_stl", type=Path)
    parser.add_argument("output_stl", type=Path)
    parser.add_argument("--sole-ai-root", type=Path, required=True)
    parser.add_argument("--side", choices=("left", "right"), required=True)
    parser.add_argument("--preview", action="store_true")
    arguments = parser.parse_args()
    report = generate_honeycomb_base(
        arguments.source_stl,
        arguments.output_stl,
        arguments.sole_ai_root,
        side=arguments.side,
        preview=arguments.preview,
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
