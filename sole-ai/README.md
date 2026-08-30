# Sole AI

`sole-ai` is the starting point for designing left and right 3D-printed racing-shoe soles from scanned geometry, runner intent, and measured test results.

It deliberately separates two jobs:

1. Fusion owns the editable B-Rep master model: sole envelope, upper interface, plate pocket, rocker, and assembly.
2. This project preserves the supplied thick outsole/midsole envelope and creates bounded internal design candidates: a continuous TPU-density field, a curved upper/bottom-midsole split surface, and PC-plate placement. The selected baseline derives the plate outline from the actual left or right sole, leaves the rear cushioning zone plate-free, and follows a moderated version of the outsole rocker. Those candidates are later evaluated by FEA and running tests.

The current manufacturing direction is an FFF-oriented, gently warped, functionally graded walled Gyroid. The earlier stochastic beam network is retained only as rejected research: once constrained for FFF it looked like vertical curtains, and when made visually denser it did not produce a reliable manufacturing mesh. Fusion remains the reference for the locked envelope, curved split, and plate. The density field is a documented load-path heuristic until runner pressure, coupon tests, and FEA data are available, so it does **not** yet predict running performance.

## Geometry to supply

Keep the original Fusion archive (`.f3d`) if it exists. For every side, export the following into `data/raw/<side>/`:

| Priority | Format | Purpose |
| --- | --- | --- |
| Required master | `sole-envelope.step` (AP242, millimetres) | Fusion-editable B-Rep source for all later CAD operations. |
| Required mesh companion | `sole-envelope.stl` (binary, millimetres, watertight) | Mesh validation and implicit growth-lattice generation. |
| Optional | `sole-envelope.3mf` | Preserves slicer/material/print metadata; it is not the CAD master. |
| Strongly recommended | `upper-reference.step` and/or `upper-reference.stl` | Locks the sole to the existing custom upper coordinate frame. |

Export a **closed solid** that includes the entire intended sole envelope—not a 2D outline, an open top surface, or a sliced print plate. The initial Fusion exports use this valid source convention:

```text
X: transverse / width
Y: toe (-) to heel (+)
Z: ground/bottom (-) to upper (+)
units: millimetres
```

The validator infers these axes from the mesh dimensions and records them in each candidate manifest; it never rotates the source CAD. In the Fusion side view used for review, negative Y is screen-right, so the raised plate end is the visible toe. If the upper and sole were exported from different coordinate systems, also place `landmarks.json` next to each side. It must contain at least `heel_center`, `first_met_head`, `fifth_met_head`, and `toe_center` in millimetres. The project will use this later to register the two parts safely.

Do not rely on STL alone for editable Fusion work: STL contains triangles, normally lacks unit metadata, and loses feature history. STEP plus the original `.f3d` is the correct source-of-truth combination. A high-resolution binary STL remains useful for implicit-field work.

## Quick start

This project uses only the Python standard library. Python 3.11 or later is required.
Before physics scoring, replace the `null` runner fields in `configs/baseline.json` with measured values.

```bash
cd sole-ai
python3 -m sole_ai.cli validate --side left
python3 -m sole_ai.cli generate --side left --count 12 --seed 42
python3 -m sole_ai.cli generate-variable-lattice --side left
python3 -m sole_ai.cli generate-organic-lattice --side left
python3 -m sole_ai.cli generate-envelope-lattice --side left
python3 -m unittest discover -s tests -v
```

Copy the generated `outputs/<side>/candidate-*.json` values into the named parameters of the Fusion master model. They are design intents, not a manufacturing model. Do not print a candidate until it has passed the future geometry, FEA, and physical-test gates.

`generate-variable-lattice` writes closed upper/lower STLs and a constraint manifest under `outputs/<side>/lattice/cellular-foam-v2/`. It also writes `*-flashstudio.stl` copies rotated diagonally and moved to Z=0 inside the AD5X 220×220 mm plate. Add `--preview` for Fusion visual-review meshes. Both the manufacturing pair and current high-detail preview use a 1 mm scalar grid.

To create the first actual B-Rep bodies, run the Fusion script in [fusion_addin/README.md](fusion_addin/README.md) after opening the matching STEP. It exports separate Upper Midsole, Bottom Midsole, and PC Plate STEP/3MF files.

When Fusion is unavailable, this project can still create watertight baseline STL bodies that preserve the supplied thick outer shape. This output has no PC-plate pocket or lattice, so use it for visual, fit, and split-line review—not for a final assembled shoe.

```bash
python3 -m sole_ai.cli generate-mesh \
  --candidate outputs/left/candidate-left-0042-001.json
```

## FFF TPU lattice core

The manufacturing-process review and acceptance criteria are recorded in
[../docs/sole-ai/FFF_TPU_LATTICE_RESEARCH.md](../docs/sole-ai/FFF_TPU_LATTICE_RESEARCH.md). The blue
Nagase reference is a photopolymer aesthetic target; AD5X output must additionally
satisfy FFF build-direction, overhang, and bridge constraints.

The selected AD5X topology is a continuous Gyroid surface with gentle long-wave phase warping. Pressure and FEA data will vary exact wall thickness smoothly, while a minimum wall is preserved everywhere. This sacrifices exact visual reproduction of the blue Nagase photopolymer reference in exchange for the FFF TPU printability and fatigue evidence documented in the research note.

An explicitly requested organic alternative is also available through
`generate-organic-lattice`. It grows irregular curved branches independently
inside each scanned left/right envelope, blends their junctions as one implicit
field, and rejects any non-watertight output. Its requested minimum branch
diameter is 1.2 mm; current branch shafts are designed between 1.6 and 1.8 mm.
The dense V2 uses a 5.0 mm nominal cell scale, 4.0--6.0 mm graded node spacing,
and three or four parent branches per node. Only the multi-branch nodes become
locally wider as the branches merge. It remains a test candidate until coupon
and cyclic-compression validation are complete.

When the designer supplies `sole-lattice-left/right.step` plus matching closed
STLs, `generate-envelope-lattice` fills each dedicated volume directly. It does
not split the volume at a plate plane. Every disjoint vertical solid interval is
sampled separately, so a designed gap between stacked or stepped source parts
remains empty. V10 uses independently sampled attraction points in every build
layer. An orthotropic k-nearest graph grows toward them, then adds anastomosis
links so branches split and merge instead of forming a regular vertical grid.
Curved branches are fused by a smooth implicit union. This research basis and
the implementation choices are recorded in
[`../docs/sole-ai/BIOLOGICAL_LATTICE_RESEARCH.md`](../docs/sole-ai/BIOLOGICAL_LATTICE_RESEARCH.md).

The 1.2 mm conformal top/bottom anchors eliminate free branch tips at the two
assembly interfaces. No side anchor or side shell is added. Every complete
branch cross-section stays inward from the lateral boundary, so a free branch
cannot terminate by being clipped on a left/right side face. Free branch shafts
vary continuously across the requested 1.5--2.0 mm range. The V10 branch/node
plan-view density target is 50% of V8: node targets are multiplied by 0.50,
while spacings and coverage radii are multiplied by `1/sqrt(0.50)`. This changes
network count density rather than promising a proportional material reduction.
Intervals 6 mm thick or thinner remain solid to preserve their designed edge
shape. The production-grid single-parent-node ratio is 8.15% left and 8.83%
right, so V10 caps it at 9% while retaining the average-link,
no-dead-end, side-clearance, and 45-degree build-angle gates.

- Forefoot propulsion zone: thickest TPMS walls near toe-off.
- Plate load path: locally reinforced around the approved low rocker-following PC plate.
- Midfoot and heel rim: moderate wall reinforcement.
- Central heel and lightly loaded transitions: thinner walls without disconnected gaps.

The requested minimum feature is 1.5 mm. The first 0.6 mm-nozzle coupon range is deliberately more conservative: 2.4--3.2 mm TPMS wall thickness. A 3 mm ground skin, 2 mm upper bonding skin, and 2 mm solid TPU support on both faces and around the edge of the PC-plate pocket remain mandatory. No full-sole STL is currently labelled print-ready; see the research note for the failed gates and coupon plan.

## Thick-sole constraint

The supplied shoes use a thick, smooth rocker midsole. In V1, `sole-envelope.step` remains the external boundary: the AI must not reduce stack height or change the approved rocker. It may open the side volume to reveal the growth lattice while preserving solid top, ground, and plate interfaces. The plate is centred on a curved split surface derived from the measured outsole underside, so both printed TPU parts capture it.

## Project layout

```text
data/raw/                 input CAD and mesh files, never generated files
configs/                  runner and manufacturing constraints
outputs/                  reproducible candidate manifests
../docs/sole-ai/          research and manufacturing notes
sole_ai/                  standard-library Python package
tests/                    regression tests
```

## Development sequence

1. Add left and right STEP/STL envelope pairs and validate their bounds.
2. Build the Fusion master model by retaining the supplied outer envelope and using the internal named parameters emitted by this project.
3. Replace the design-manifest export with a geometry adapter for the Fusion API.
4. Calibrate the cell-spacing-and-diameter-to-stiffness relation with printed coupons.
5. Add quasi-static FEA and plantar-pressure data, then replace the current smooth heuristic field with optimized runner-specific weights.

This order keeps the first prototypes inspectable and avoids training an "AI" on unverified assumptions.
