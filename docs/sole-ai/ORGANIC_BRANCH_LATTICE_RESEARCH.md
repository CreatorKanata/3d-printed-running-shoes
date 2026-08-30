# Organic branch lattice generation decision

This note records the algorithm selected for the locally generated left and
right sole meshes. The goal is an irregular, biological branch network rather
than a repeated Cartesian unit cell.

## Methods considered

- Voronoi and Delaunay methods produce controllable irregular trabecular
  networks, but unconstrained edges can create unsupported horizontal members.
- Spinodal methods create smooth stochastic and often bicontinuous phases, but
  direct control of individual branch diameter and build angle is indirect.
- Space-colonization growth produces recognizably organic branching skeletons,
  but a tree alone lacks the closed loops required for a durable sole.
- Signed-distance implicit modeling can turn a graph of curved branches into a
  closed surface and blend multi-branch nodes without fragile Boolean seams.

## Selected hybrid

The implementation combines these ideas:

1. Poisson-like irregular roots are sampled independently inside each scanned
   left/right envelope.
2. Nodes grow layer by layer toward the opposite solid interface, borrowing the
   attraction-and-growth idea of space colonization while keeping every member
   within the configured FFF angle.
3. Every new node receives three or four printable parent links, so the result
   contains many short load-sharing loops instead of a sparse tree.
4. Quadratic Bezier sampling bows every branch and removes dominant grid
   directions.
5. A variable-radius signed-distance field represents the branches. A smooth
   minimum fuses their junctions into rounded, bone-like nodes.
6. The field is clipped by the measured sole columns and united with ground,
   upper-bonding, and plate-support interfaces.
7. Marching tetrahedra extracts the surface. Export is rejected unless every
   quantized edge has exactly two incident faces.

## Current manufacturing bounds

- requested minimum branch diameter: 1.2 mm;
- conservative designed branch-shaft diameter: 1.6--1.8 mm;
- implicit shaft expansion: 0 mm; only junctions receive a 0.05 mm blend;
- nominal irregular cell scale: 5.0 mm;
- node spacing: 4.0--6.0 mm, graded continuously by the load heuristic;
- build-layer spacing: 3.2 mm;
- scalar grid: 0.6 mm;
- maximum branch angle from the build direction: 45 degrees;
- lower and upper halves are generated separately around the PC-plate pocket;
- left and right are generated independently and are never mirrored.

The 1.6 mm design floor intentionally exceeds the requested 1.2 mm. The extra
margin covers scalar-grid and FFF process error while the 1.8 mm shaft ceiling
limits excess mass. The denser V2 adds material by increasing branch and loop
count, not by violating that shaft ceiling. Junctions are locally wider because
several branches must merge into one connected node. Geometry checks do not replace
TPU coupon, compression, fatigue, thermal, and slicer-support validation.

## Primary references

- Runions, Lane, and Prusinkiewicz, *Modeling Trees with a Space Colonization
  Algorithm* (2007): https://algorithmicbotany.org/papers/colonization.egwnp2007.html
- Wang et al., *Machine learning unifies flexibility and efficiency of spinodal
  structure generation for stochastic biomaterial design* (2023):
  https://www.nature.com/articles/s41598-023-31677-7
- *An improved trabecular bone model based on Voronoi tessellation* (2023):
  https://doi.org/10.1016/j.jmbbm.2023.106172
- *A method for generating large-scale implicit lattice structures for direct
  manufacturing* (2025): https://doi.org/10.1016/j.jmapro.2025.07.010
