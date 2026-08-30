# Cosmic-biological variable-density sole lattice

The printable lattice is generated as mesh data rather than thousands of Fusion timeline features. Fusion supplies the immutable scanned envelope and approved rocker-following plate path. The Python pipeline builds a dense non-periodic cellular foam, unites it with required solid TPU interfaces, and writes closed binary STL files.

## Generative model

This is not a repeated Cartesian cell and it is not a TPMS formula. It uses a deterministic stochastic-cell construction:

1. Non-periodic nodes fill each sole half with a nominal 8.8 mm cell scale.
2. The biomechanical field smoothly reduces local spacing where more support is needed.
3. Each node connects to six irregular neighbours, creating many small interlocking cells.
4. Every connection becomes a five-segment quadratic Bezier curve instead of a kinked wire.
5. The load field also changes branch diameter without abrupt zone boundaries.
6. An implicit union rounds every junction and blends the network, skins, and plate support before one closed surface is extracted.

The result is deliberately non-aligned and densely connected. It should resemble stochastic foam, trabecular bone, and the reference blue cellular midsole more than a manufactured grid.

## Load-guided variation

| Region | Relative growth | Intent |
| --- | --- | --- |
| Forefoot around toe-off | Smaller cells and thicker branches | Transfer load and limit excess collapse |
| Approved plate path | Smaller cells fused to solid support | Carry load without isolated plate-to-lattice contacts |
| Midfoot and outer rim | Medium | Torsional and lateral stability |
| Central heel | Larger cells, while retaining a connected minimum density | Preserve cushioning and reduce mass |

This is a design heuristic, not a measured material model. Printed coupons, plantar pressure, FEA, and running tests must calibrate it.

## Manufacturing constraints

- Requested minimum branch diameter: 1.5 mm.
- Nominal generated branch floor: 1.8 mm.
- Implicit fusion overlap: 0.12 mm per side; effective isolated floor is about 2.04 mm.
- Ground-contact solid TPU: 3.0 mm nominal.
- Upper bonding solid TPU: 2.0 mm nominal.
- PC-plate support: 2.0 mm on each face plus a 2.0 mm closed edge support.
- Sidewall: open cellular foam, with no cosmetic solid skin.
- Manufacturing scalar grid: 1.0 mm.
- Fusion visual-review scalar grid: 1.0 mm, matching the manufacturing mesh.

## Outputs

```text
sole-ai/outputs/<side>/lattice/cellular-foam-v2/
├── lower-cellular-foam.stl
├── upper-cellular-foam.stl
├── lower-cellular-foam-flashstudio.stl
├── upper-cellular-foam-flashstudio.stl
├── cellular-foam-manifest.json
├── lower-cellular-foam-preview.stl
├── upper-cellular-foam-preview.stl
└── cellular-foam-preview-manifest.json
```

The engineering-coordinate pair remains aligned with the Fusion envelope and plate. The `flashstudio` copies are rotated diagonally, translated so Z starts at 0, and checked against the AD5X 220×220 mm bed with a 5 mm margin.

Generate both resolutions with:

```bash
python3 -m sole_ai.cli generate-variable-lattice --side right
python3 -m sole_ai.cli generate-variable-lattice --side right --preview
```

## Validation boundary

Every exported component must have exactly two faces sharing every mesh edge. The pipeline rejects open or non-manifold meshes and rejects Flash Studio copies outside the configured bed. This follows the manufacturing lesson in the [Materialise/OECHSLER case study](https://www.materialise.com/ja/inspiration/articles/oechsler-3d-printed-lattices-magics): complex lattice data requires automated failure checks and nesting, not visual confidence alone.

The multi-zone variation and conformal boundary strategy are informed by [Carbon Design Engine](https://www.carbon3d.com/resources/blog/carbon-advanced-lattices), while the non-periodic point-density concept is related to the Voronoi and custom-lattice categories described by [Evort](https://evort.jp/article/lattice-structure). The present cellular algorithm is project-specific and does not claim to reproduce either proprietary tool.

Geometry validity does not prove durability or running performance. Do not run in the prototype until material coupons, plate-clearance inspection, quasi-static compression FEA, and a low-speed physical test have passed.
