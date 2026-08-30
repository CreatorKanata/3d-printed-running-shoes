# Graded Multi-Row Honeycomb V3 — left sole

This generator uses the supplied `sole-lattice-left.stl` directly. It does not
mirror the opposite foot, scale a cube, or replace the scanned outline with a
generic shoe shape. V2 remains available separately and is not overwritten.

## Architecture

V3 replaces V2's long lower vertical legs and top-only triangular braces with a
flat-top hexagonal network spanning the complete sole height. On the 40 mm left
designer volume the network contains four staggered rows, 26 longitudinal
columns, and 154 cells. Every internal node joins three short walls, and no
unbraced segment is longer than the 5.5 mm cell edge.

The 5.5 mm edge produces 9.5 mm-tall cells. Steep diagonal walls are friendly
to flat-bed FFF printing; each short horizontal bridge is supported at both
ends. Side openings intentionally expose the printed honeycomb.

Wall thickness provides the smooth density grade without breaking cell
continuity:

- central arch: 1.5 mm;
- heel and forefoot: 1.8 mm;
- transitions use a smooth cubic curve rather than a hard boundary.

Continuous 1.5 mm upper and lower skins spread landing load. Two 1.5 mm
internal longitudinal rails link the transverse honeycomb plates and resist
out-of-plane buckling. The proof-load design target remains 1.24 kN: 28 kg,
three bodyweights, and a 1.5 safety factor.

A 0.2 mm lateral raster guard keeps the generated mesh inside the supplied STL
envelope instead of allowing coarse-grid interpolation to protrude beyond it.

## Material and qualification boundary

The selected material is eSUN eLastic TPE-83A. eSUN reports 1.14 g/cm3 density,
29 MPa XY tensile strength, 7.53 MPa Z tensile strength, over 400% XY
elongation, and 129.7% Z elongation. The official baseline is 220--250 C nozzle,
45--60 C bed, 100% fan, below 50 mm/s, and drying at 55 C for more than four
hours.

Official material page:
https://www.esun3d.com/elastic-tpe-83a-product/

The geometry is checked for a closed two-manifold STL and a single connected
material body. Those checks do not prove running safety. The intended AD5X
profile must pass coupons, a 1,236 N static proof, and the cyclic sequence in
`LEFT_TPE83A_TEST_PLAN.md` before human running.

## Reproducibility

Run the fast geometry gates with:

```sh
python3 -m unittest discover -s tests
```

Generate a visual-review STL with `--preview`; omit it for the 0.70 mm
production mesh.
