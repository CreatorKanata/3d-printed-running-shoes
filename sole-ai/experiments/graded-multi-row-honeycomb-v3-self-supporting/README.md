# Self-Supporting Graded Honeycomb V3.1 — independent left/right soles

This generator uses the supplied `sole-lattice-left.stl` directly. It does not
mirror the opposite foot, scale a cube, or replace the scanned outline with a
generic shoe shape. Left and right inputs are processed independently rather
than mirrored. Earlier designs remain available separately and are not
overwritten.

## Architecture

V3.1 uses a
point-top hexagonal network spans the complete sole height. Each cell is 8 mm
wide and 13 mm tall, with 4 mm vertical sides and four 6.02 mm diagonal sides.
The diagonals rise 48.37 degrees from the build plate. Therefore the internal
honeycomb contains zero build-plate-parallel edges: every cell segment is
vertical or rises above 45 degrees. Every internal node still joins three short
walls. The supplied 40 mm left volume is covered by 28 columns, four rows, and
171 cells; the side openings expose the printed structure.

The continuous upper skin remains a horizontal surface by design, so the
finished sole is not literally bridge-free. Pointed cell crowns support that
skin at short intervals. The actual AD5X/TPE profile still needs a print coupon
to confirm that those local spans close without sagging.

Wall thickness provides the smooth density grade without breaking cell
continuity:

- central arch: 1.5 mm;
- heel and forefoot: 1.8 mm;
- transitions use a smooth cubic curve rather than a hard boundary.

Continuous 1.5 mm upper and lower skins spread landing load. Two 1.5 mm
internal longitudinal rails rise continuously from the lower skin to the upper
skin. The proof-load design target remains 1.24 kN: 28 kg, three bodyweights,
and a 1.5 safety factor.

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

The geometry is checked for a closed two-manifold STL, one connected material
body, zero horizontal internal honeycomb edges, and a minimum 45 degree rising
wall angle. Those checks do not prove running safety. The intended AD5X
profile must pass coupons, a 1,236 N static proof, and the cyclic sequence in
`LEFT_TPE83A_TEST_PLAN.md` before human running.

## Reproducibility

Run the fast geometry gates with:

```sh
python3 -m unittest discover -s tests
```

Generate a visual-review STL with `--preview`; omit it for the 0.70 mm
production mesh. Print flat with Z as the layer-stack direction.

## 30 mm printability box

`cairo_real_sole.coupon` creates a rail-free V3.2 sample after the first physical
coupon showed excessive stiffness from the two longitudinal rails. The rail-
free sample retains the V3.1 honeycomb and upper/lower skins in a nominal
30 x 30 x 30 mm cube. Its production grid is
0.50 mm so the 1.5 mm minimum wall is represented by at least three samples.
Place the lower 30 x 30 mm face on the build plate. The coupon checks support-
free geometry and comparative stiffness only; it is not a running-load proof.

## New base-STL full sole with plate pocket

`cairo_real_sole.honeycomb_base` processes
`sole-honeycomb-base-left.stl` and `sole-honeycomb-base-right.stl`
independently. It does not mirror either foot. This V3.2 variant removes the
two internal longitudinal rails after the 30 mm physical sample showed that
they made the structure too stiff.

The region above the nested 2.2 mm cutter remains the original solid upper.
The lower honeycomb retains a continuous 1.5 mm pocket-floor skin and a
continuous 1.5 mm ground-facing skin. A 1.5 mm solid perimeter encloses the
plate pocket for a pause-and-insert print. No solid lateral skins are added to
the lower section, so its honeycomb cross-section remains visible on both
sides. The supplied STL remains the clipping envelope and controls the actual
outline and vertical profile. Generate the left preview with:

```sh
python3 -m cairo_real_sole.honeycomb_base \
  sole-honeycomb-base-left.stl sole-honeycomb-left-preview.stl \
  --sole-ai-root /path/to/sole-ai --side left --preview
```
