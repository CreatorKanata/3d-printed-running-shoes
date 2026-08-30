# sole_ai.cli: intentionally small command line for the validation-first design workflow.
from __future__ import annotations

import argparse
from pathlib import Path

from .envelope_lattice import generate_envelope_lattice
from .fff_tpms import generate_fff_graded_gyroid
from .mesh_pipeline import generate_split_stls
from .organic_strut import generate_organic_strut_lattice
from .pipeline import generate_manifests, validate_envelope
from .stl import infer_sole_axes


def build_parser() -> argparse.ArgumentParser:
    """Build the explicit command interface used by designers and CI."""
    parser = argparse.ArgumentParser(description="Validate and explore custom sole-design inputs.")
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser("validate", help="Validate the supplied sole-envelope.stl.")
    validate.add_argument("--side", choices=("left", "right"), required=True)

    generate = commands.add_parser("generate", help="Write bounded design candidates after validation.")
    generate.add_argument("--side", choices=("left", "right"), required=True)
    generate.add_argument("--count", type=int, default=12)
    generate.add_argument("--seed", type=int, default=42)
    generate.add_argument("--config", type=Path, default=None)

    mesh = commands.add_parser("generate-mesh", help="Write capped upper/bottom baseline STLs from a candidate.")
    mesh.add_argument("--candidate", type=Path, required=True)

    variable = commands.add_parser(
        "generate-variable-lattice",
        help="Write upper/lower FFF-ready graded Gyroid STLs.",
    )
    variable.add_argument("--side", choices=("left", "right"), required=True)
    variable.add_argument("--preview", action="store_true")

    organic = commands.add_parser(
        "generate-organic-lattice",
        help="Write upper/lower organic branch-network STLs.",
    )
    organic.add_argument("--side", choices=("left", "right"), required=True)
    organic.add_argument("--preview", action="store_true")

    envelope = commands.add_parser(
        "generate-envelope-lattice",
        help="Fill sole-lattice-left/right STL with a graded organic network.",
    )
    envelope.add_argument("--side", choices=("left", "right"), required=True)
    envelope.add_argument("--preview", action="store_true")
    return parser


def main() -> int:
    """Run a command and expose only the reviewable output paths."""
    arguments = build_parser().parse_args()
    if arguments.command == "validate":
        bounds = validate_envelope(arguments.side)
        axes = infer_sole_axes(bounds)
        print(f"{arguments.side}: {bounds.triangle_count:,} triangles")
        print(
            "source_axes: "
            f"longitudinal={axes.longitudinal_axis}, "
            f"transverse={axes.transverse_axis}, vertical={axes.vertical_axis}"
        )
        print(
            "sole_dimensions_mm: "
            f"length={axes.longitudinal_length_mm:.2f}, "
            f"width={axes.transverse_width_mm:.2f}, "
            f"stack={axes.stack_height_mm:.2f}"
        )
        return 0

    if arguments.command == "generate-mesh":
        for path in generate_split_stls(arguments.candidate):
            print(path)
        return 0

    if arguments.command == "generate-variable-lattice":
        for path in generate_fff_graded_gyroid(arguments.side, preview=arguments.preview):
            print(path)
        return 0

    if arguments.command == "generate-organic-lattice":
        for path in generate_organic_strut_lattice(arguments.side, preview=arguments.preview):
            print(path)
        return 0

    if arguments.command == "generate-envelope-lattice":
        for path in generate_envelope_lattice(arguments.side, preview=arguments.preview):
            print(path)
        return 0

    paths = generate_manifests(
        arguments.side,
        arguments.count,
        arguments.seed,
        config_path=arguments.config,
    )
    for path in paths:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
