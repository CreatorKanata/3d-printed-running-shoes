# Fusion baseline-geometry generator

`sole_ai_fusion.py` is a Fusion script, not a command-line program. It creates real editable B-Rep components from a selected `sole-envelope.step` body and one Sole AI candidate JSON.

## What it generates

- `BOTTOM_MIDSOLE`: the supplied thick sole envelope below the candidate split surface.
- `UPPER_MIDSOLE`: the same envelope above that split surface.
- `PC_PLATE`: a clearance-pocketed PC plate whose planform is trimmed by a scaled copy of the actual left or right sole. It starts after the heel cushion, has a smooth semicircular rear cap, and follows a moderated version of the measured outsole rocker toward the negative-Y toe.
- `*.step`, `*.3mf`, and `sole-ai-assembly.f3d` under `outputs/<side>/geometry/<candidate-id>/`.

The source sole envelope is copied before it is split; it is hidden after a successful run but not deleted. The visible white exterior stays exactly as supplied. The generator creates an internal clearance pocket in both TPU components for the PC plate.

## Lattice responsibility

Fusion owns the reference CAD: locked sole envelope, approved rocker-following plate, and curved upper/lower split. The 2 mm upper skin, 3 mm ground skin, 2 mm plate supports, and biological open-cell lattice are fused into closed meshes outside Fusion by `python3 -m sole_ai.cli generate-variable-lattice --side <side>`.

Import the `lower/upper-organic-strut-preview.stl` pair only for visual review in Fusion. Use the matching non-preview pair as the high-resolution manufacturing source after slicer and coupon validation. Both pairs come from the same deterministic growth history; only surface sampling resolution differs.

Run `import_variable_lattice_preview.py` from **Utilities → Scripts and Add-Ins** to load that generated pair into the current Fusion design. The importer performs no lattice Boolean or density calculation in Fusion.

## Run it in Fusion

1. Open `data/raw/left/sole-envelope.step` or the matching right-side STEP in Fusion's **Design** workspace.
2. Open **Utilities → Scripts and Add-Ins**, add/run `sole_ai_fusion.py` from this folder.
3. Paste the absolute path to the matching candidate JSON when prompted, for example:

   ```text
   /Users/hide/src/github.com/CreatorKanata/3d-printed-running-shoes/sole-ai/outputs/left/candidate-left-0042-001.json
   ```

4. Select the imported closed sole B-Rep body.
5. Inspect the generated `SOLE_AI_<candidate-id>` component: ensure that the plate pocket remains inside the thick sole and that the outer silhouette has not changed.
6. Use the generated STEP files for edits and the 3MF files only after reviewing the clearance and print orientation.

## Fusion MCP execution

Fusion MCP can run the same workflow without modifying the source model that is already open. Import the matching STEP into a new, unsaved document, generate the assembly there, and export the result. This keeps the original scan-lock document untouched.

The low, rocker-following, heel-relieved pair has been generated from candidate `0042-001`:

| Side | Candidate | Generated directory |
| --- | --- | --- |
| Left | `left-0042-001` | `outputs/left/geometry/left-0042-001-low-rocker-smooth-heel/` |
| Right | `right-0042-001` | `outputs/right/geometry/right-0042-001-low-rocker-smooth-heel/` |

Each directory contains separate bottom-midsole, upper-midsole, and PC-plate STEP/3MF files, `sole-ai-assembly.f3d`, and `generation-report.json` with the sampled rocker coordinates. The plate starts 18% forward of the heel, stops at 93% of the heel-to-toe length, and has a 40 mm rounded rear cap. Its deepest centre is 17.5 mm above the global ground minimum—5.72 mm lower than the previous version—and it follows 45% of the measured outsole rocker amplitude. Its planform is the actual side-specific sole B-Rep scaled to 74% in width and 92% in length so the FFF lattice remains visible and printable beside the 2 mm cradle. The F3D is a generated artifact; the unsaved Fusion document can be discarded after confirming the exports.

## Current boundary

This is a genuine B-Rep reference assembly plus a script-grown, variable-density branch network. The PC plate has a side-specific inset footprint, heel-cushion relief, and a measured rocker-following profile. Growth is currently guided by smooth biomechanical zones rather than measured plantar pressure, so coupon tests, FEA, and running validation are still required before the sole is treated as race-ready.
