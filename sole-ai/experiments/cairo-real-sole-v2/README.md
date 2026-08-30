# Cairo Bio-Cell Side-Reveal — actual sole candidate

This generator uses the supplied `sole-lattice-left.stl` and
`sole-lattice-right.stl` directly. It does not scale a cube, mirror one foot, or
replace the scanned outline with a generic shoe shape.

The solid is a row of side-facing pentagonal arches clipped independently to
every vertical solid interval in the source STL. V2 adds continuous 1.5 mm upper
and lower load-spreading skins; the lateral faces remain open so the printed
cellular construction is visible.

V2 raises the walls to the project's 1.5 mm minimum and reduces the pitch from
V1's 22 mm to about 7.3 mm.
That produces roughly thirty transverse arches across a 218 mm sole, tripling
the support frequency without thickening each wall. Two internal longitudinal
rails tie the arch legs together and resist progressive lateral buckling. The
proof-load target is 1.24 kN: 28 kg, three bodyweights, and a 1.5 safety factor.
The anti-buckling rails terminate into transverse arch legs rather than being
clipped by the external toe, heel, top, or bottom surfaces.
The scalar grid uses a non-rational phase offset so source faces do not coincide
with marching-grid vertices and create point-contact non-manifold edges.
Field samples within 0.005 mm of the isosurface are moved away from zero without
changing material/void classification. This prevents sub-resolution triangles
at grid nodes and is one third of one percent of the 1.5 mm structural wall.
Numerical marching slivers are removed at the project's 0.00001 mm mesh-QA
tolerance, five orders of magnitude below the 1.5 mm structural wall.
This target must be verified on the selected printed TPE before running. The output is geometry-checked for a closed
two-manifold STL, but running use still requires print, compression, peel, and
fatigue tests.

The selected material is eSUN eLastic TPE-83A, not the earlier TPU-95A
assumption. eSUN reports 1.14 g/cm3 density, 29 MPa XY tensile strength, 7.53
MPa Z tensile strength, over 400% XY elongation, and 129.7% Z elongation. The
large directional difference makes layer adhesion a required test item. The
official baseline is 220--250 C nozzle, 45--60 C bed, 100% fan, below 50 mm/s,
and drying at 55 C for more than four hours. These are starting settings, not a
substitute for AD5X coupons and a full-sole proof/fatigue test.

Official material page:
https://www.esun3d.com/elastic-tpe-83a-product/

The left-foot physical acceptance sequence is documented in
`LEFT_TPE83A_TEST_PLAN.md`.

Run the fast unit gates with:

```sh
python3 -m unittest discover -s tests
```

Generate a coarse visual-review STL with `--preview`; omit it for the 0.70 mm
production mesh.
