# FFF TPU midsole lattice research and manufacturing decision

This note records why the lattice generator must be selected from the print
process first. It prevents a visually attractive DLP or powder-bed lattice from
being copied into a supportless AD5X filament build that cannot manufacture it.

## Executive decision

The blue Nagase ChemteX image supplied with this project remains the **aesthetic
target**, but its free 3D branching topology is not direct evidence of a viable
AD5X manufacturing topology. Nagase's primary material literature confirms that
its related flexible RS family is photocured; it does not independently identify
the exact pictured shoe. This project uses a Flashforge AD5X and material
extrusion (FFF/MEX). Because support trapped inside a closed porous midsole
cannot be removed safely, its internal geometry must be self-supporting and
continuously printable in the selected build orientation.

The leading AD5X candidate is a **gently warped, functionally graded walled
Gyroid (TPMS)**. It has a continuous surface instead of isolated beam joints and
is one of the most credible, well-documented candidates in current FFF TPU
cushioning research. It is not assumed to be optimal until coupon testing.

- lower midsole prints from its 3 mm ground skin toward the plate;
- upper midsole prints inverted, from its 2 mm upper-bonding skin toward the plate;
- the starting cell scale is 7.5 mm;
- the wall range is 2.4--3.2 mm for 0.6 mm-nozzle coupons;
- pressure/FEA data changes wall thickness smoothly, never by deleting regions;
- long-wave phase warping reduces visual repetition without generating arbitrary
  unsupported beams;
- exact wall thickness must be restored after warping and measured on the final mesh;
- the slicer must not generate support inside closed, post-processing-inaccessible
  lattice spaces.

An FFF-constrained stochastic beam network was also prototyped and rejected. It
either looked like vertical curtains when every branch was printable, or became
non-manifold when enough curved branches were added to imitate the reference.
It is retained as research code, not an approved manufacturing source.

The selected TPMS will not exactly reproduce a resin or powder-bed Voronoi
lattice. If exact reproduction of the blue reference becomes the priority, the
print process must change to DLP/DLS elastic resin or MJF/SLS TPU.

## Why the reference cannot be copied directly to AD5X

The exact process used for the pictured shoe has not been independently
identified from a primary source. What Nagase's primary documentation does
establish is that its related flexible RS materials are intended for SLA, DLP,
LCD, and inkjet systems, with high-resolution curing and more than 200%
elongation for the flexible RS family. The image is therefore an aesthetic
reference, not evidence that the same unconstrained network is printable in TPU
filament by FFF.

Carbon footwear lattices are produced by Digital Light Synthesis. Carbon's DfAM
guidance separately calls out gradual geometry, consistent wall thickness,
self-support, cleanability, and lattice-specific parameters. That is a complete
process/material/design system, not just an STL pattern.

OECHSLER's lattice library is another important reference, but the Materialise
case study says its production workflow sends the parts to HP Multi Jet Fusion.
The surrounding powder supports arbitrary branches during fabrication. Magics
then checks millions of surfaces and hundreds of thousands of struts before
nesting. Powder-bed success does not demonstrate supportless FFF success.

## Process comparison

| Process | Material support during build | Appropriate lattice freedom | Relevance here |
| --- | --- | --- | --- |
| DLP/DLS/SLA elastomer | Resin process with process-specific supports and cleaning | Fine freeform branches after DfAM validation | Matches the reference aesthetic, not the AD5X process |
| MJF/SLS TPU | Unsintered powder supports the whole part | Voronoi, Delaunay, and arbitrary 3D networks | Strong outsourcing option |
| FFF/MEX TPU | Only the previous layers support new extrusion | Self-supporting TPMS or build-direction-constrained struts | Required for AD5X |

## Evidence for FFF/MEX TPU

Research on supportless flexible TPU lattices identifies overhang angle and
bridging distance as the two critical geometric constraints. A 45 degree limit
is a safe starting approximation, but the bridge limit is material, temperature,
speed, and cooling dependent. A recent FFF review recommends 45--60 degree
overhang compliance and bridges shorter than 5 mm as an initial design region.

TPU honeycomb and gyroid specimens have been printed support-free when their
open areas are small enough and the process has sufficient bridging capability.
TPU gyroids are especially well represented in footwear/cushion research because
they provide continuous load paths, can be graded smoothly, and avoid isolated
beam joints. Functionally graded TPU gyroid testing also found that smooth wall-
thickness transitions can outperform abrupt density transitions in fatigue.

These results do **not** justify sending a full shoe directly to the printer.
They justify generating coupons, mapping the printable window, measuring their
stress--strain response, and only then selecting the sole field parameters.

## AD5X-specific constraints

Flashforge specifies a 220 x 220 x 220 mm build volume, 0.1--0.4 mm layers, and
0.4 mm standard plus 0.6/0.8 mm optional nozzles. TPU 95A is supported for
single-colour printing. The current Flashforge TPU/PEBA guide recommends 0.4,
0.6, or 0.8 mm nozzles for TPU 95A on AD5X, thorough drying, a dedicated clean
nozzle, and reduced feed resistance.

The same guide warns that TPU support removal is difficult and may deform the
part. It recommends PLA when support is unavoidable, while also listing TPU 95A
as incompatible with IFS. A sealed internal midsole must therefore not depend on
disposable support material.

## Geometry acceptance criteria

The next preview is not accepted until it meets all of these checks:

1. **Build direction:** lower `+Z`; upper inverted so its manufacturing direction
   is engineering `-Z`.
2. **Self-support:** slicer overhang and bridge analysis must use the actual
   upper/lower manufacturing orientations; no generated support may remain in
   a closed internal space from which it cannot be removed.
3. **No floating paths:** layer preview must contain no islands disconnected
   from the preceding material.
4. **Wall thickness:** 2.4 mm nominal floor for the first 0.6 mm-nozzle coupon;
   the finished mesh must measure at least 1.5 mm everywhere.
5. **Cell scale:** 6--9 mm initial Gyroid cells with smooth spatial grading.
6. **Interfaces:** upper bonding skin 2 mm, ground skin 3 mm, plate support 2 mm
   on each face, all fused into closed two-manifold bodies.
7. **Visible sidewall:** the plate cradle remains at least 6 mm inboard of the
   visible side lattice; no long external horizontal support band.
8. **Mesh tolerance:** at most one third of the minimum feature size; the final
   2.4 mm minimum-wall model therefore uses 0.8 mm or finer surface tolerance.
9. **Slicer gate:** no support generated in closed, post-processing-inaccessible
   lattice spaces, no floating paths, build bounds valid, and an explicit
   print-time/material estimate.
10. **Physical gate:** print three coupons before the sole, then inspect bridges,
    strand fusion, dimensional error, 40% compression, recovery, and heat build-up.

## Generation methods surveyed

### Repeated beam cells

BCC, FCC, octet, diamond, and auxetic cells are easy to parameterize and simulate.
They can be supportless when oriented deliberately, but an unwarped array looks
regular and artificial. They are useful as calibrated coupon baselines.

### TPMS surfaces

Gyroid, Diamond, and related TPMS structures are implicit continuous surfaces.
They avoid weak beam-to-node contacts and are easy to grade by wall thickness.
For AD5X, a field-warped gyroid is the leading coupon candidate after rejection
of the stochastic strut concept. Exact thickness must be restored after warping
or remapping; nTop documents normalization and exact-thickness workflows for
this purpose.

### Voronoi/Delaunay lattices

Changing point density gives attractive non-periodic geometry, and nTop documents
field-driven volume-mesh-to-lattice shoe workflows. However, unconstrained 3D
edges include horizontal and downward-facing members. Such examples are suitable
for powder-bed or resin processes unless an FFF overhang constraint is added.

### Topology-optimized and field-driven lattices

Pressure and FEA fields should drive cell scale and member diameter. nTop's shoe
workflow imports a pressure scalar point map, remeshes the volume using a smooth
edge-length field, then converts the volume mesh to lattice. For this project the
same field concept is retained, but an FFF build-direction filter is mandatory.

## Coupon programme before a wearable sole

Generate 60 x 60 x 30 mm walled-Gyroid coupons before another full sole:

| Coupon | Cell scale | Wall thickness | Purpose |
| --- | ---: | ---: | --- |
| Soft | 9 mm | 2.4 mm | Heel cushioning baseline |
| Medium | 7.5 mm | 2.7 mm | General midsole baseline |
| Firm | 6 mm | 3.0 mm | Forefoot/plate load-path baseline |

Print using a dedicated 0.6 mm nozzle and dry filament. Fix and record the TPU
brand, hardness, drying cycle, layer height, line width, temperature, speed,
cooling, retraction, and build orientation across all coupons. Record actual
mass, dimensions, inaccessible-support count, failed spans, compression force
at 10/20/30/40%, permanent set after rest, and surface temperature during
repeated compression. These measurements replace guessed density-to-stiffness
values in the optimizer.

## Required production workflow

1. Lock the machine, material hardness, nozzle, layer height, cooling, and build
   orientation before selecting geometry.
2. Print the three Gyroid coupons and an overhang/bridge coupon on the AD5X.
3. Measure as-printed mass, wall error, pore closure, stiffness, recovery, and
   temperature rise; do not calibrate FEA from datasheet TPU alone.
4. Fit a response surface from cell scale and wall thickness to compression behaviour.
5. Import plantar pressure and FEA results as a smooth scalar field.
6. Generate a normalized, exact-thickness implicit Gyroid; clip it to each sole
   half and unite it with the 3/2/2 mm solid interfaces.
7. Repair and validate the final mesh with an industrial lattice/mesh tool or a
   proven equivalent. Every edge must have exactly two incident faces.
8. Slice the actual upper and lower orientations. Reject support generated in
   inaccessible internal spaces, floating paths, excessive bridges, closed
   drainage volumes, or bed overflow.
9. Print a heel/forefoot section before committing to the complete sole.
10. Run quasi-static compression and cyclic testing before any running test.

## Current project status

- Terra image review rejected both experimental beam-network previews.
- The FFF-constrained version met its 45 degree branch-angle rule and nominal
  diameter rule but still looked like vertical curtains rather than the reference.
- The first graded-Gyroid implementation is research code only. Its raw surface
  intersects the sampled source envelope with a small number of non-manifold
  edges, and the attempted local voxel repair has not yet passed the project's
  strict two-faces-per-edge test.
- Therefore no generated STL is labelled print-ready, and Fusion/Flash Studio
  should not receive a replacement final model yet.

## Sources

- [Nagase ChemteX visible-light-curing 3D printing material](https://group.nagase.com/nagasechemtex/en/products/catalog/pdf/3dpe.pdf)
- [Carbon Design for DLS](https://learn.carbon3d.com/design)
- [Materialise/OECHSLER lattice production with Magics and HP MJF](https://www.materialise.com/ja/inspiration/articles/oechsler-3d-printed-lattices-magics)
- [Flashforge AD5X specifications](https://www.flashforge.com/products/flashforge-ad5x-3d-printer)
- [Flashforge TPU/PEBA Usage Guide](https://wiki.flashforge.com/resource/pictures/filament/print_defect_and_solution/tpu_usage_guide.pdf)
- [Design of Flexible TPU-Based Lattice Structures for 3D Printing](https://doi.org/10.3390/polym17091133)
- [Mechanical Properties of Flexible TPU-Based 3D Printed Lattice Structures](https://doi.org/10.3390/polym13172782)
- [Functionally graded TPU gyroid structures for cushioning applications](https://doi.org/10.1080/15376494.2025.2530146)
- [Development of Periodic Cell Structures that Can Adjust Young's Modulus](https://doi.org/10.2472/jsms.73.949)
- [nTop: vary density to create a custom shoe sole](https://support.ntop.com/hc/en-us/articles/360043876354-How-to-vary-density-to-create-a-custom-shoe-sole)
- [nTop: measure TPMS wall thickness](https://support.ntop.com/hc/en-us/articles/18669009073555-How-to-measure-TPMS-wall-thickness)
- [Autodesk Fusion volumetric lattice properties](https://help.autodesk.com/view/fusion360/ENU/?contextId=SLD-VOLUMETRIC-LATTICE)
