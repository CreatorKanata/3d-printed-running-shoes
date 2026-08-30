# Left sole TPE-83A running gate

This document defines the minimum physical gate for the left-foot V3.1 candidate.
It does not certify the shoe. Do not perform a human running test until every
gate below passes on a part printed with the intended AD5X profile.

## Fixed design basis

- Runner mass: 28 kg.
- Conservative running peak: 3.0 bodyweights = 824 N on one foot.
- Structural proof target: 824 N x 1.5 = 1,236 N.
- Material: eSUN eLastic TPE-83A, dried at 55 C for more than four hours.
- Geometry: point-top honeycomb with no horizontal internal cell edges, at
  least 48.37-degree diagonals, 1.5--1.8 mm graded walls, two longitudinal
  bottom-to-top vertical rails, and continuous 1.5 mm upper/lower
  load-spreading skins.

## 1. Print-process coupons

Print coupons beside the sole with the same dried spool, nozzle, temperatures,
speed, layer height, cooling, and build orientation. Reject the build for
under-extrusion, wet-filament bubbles, gaps at junctions, or visible layer
separation. Include the upper-skin span over at least four cell crowns so sag is
measured in the intended flat orientation. The Z-direction coupon is mandatory
because eSUN reports much lower Z tensile strength than XY strength for this
material.

## 2. Static proof compression

1. Measure initial height at heel, midfoot, and forefoot.
2. Compress the complete sole between representative upper and outsole plates.
3. Ramp from 0 N to 824 N over at least 10 seconds; record displacement.
4. Continue to 1,236 N and hold for 60 seconds.
5. Unload, wait 30 minutes, then repeat the three height measurements.

Pass only if there is no crack, layer split, skin separation, sudden load drop,
or cell-wall inversion. At 824 N, displacement must not exceed 30% of the local
sole height. After recovery, permanent height loss must be at most 5% locally.

## 3. Running-cycle compression

Cycle the assembled sole from 50 N to 824 N for 10,000 cycles at no more than
3 Hz. Stop every 1,000 cycles to inspect the toe, forefoot, heel, cell junctions,
and both load-spreading skins. Record peak displacement and surface temperature.

Pass only if peak displacement grows by at most 10% from the first 100 cycles,
there is no progressive heating trend, no crack or delamination, and the same
5% permanent-set limit is met 30 minutes after the final cycle.

## 4. Human-use sequence

After all bench gates pass, begin with standing, walking, short straight-line
jogs, and only then a supervised 1 km run. Reinspect after each stage. Any new
noise, asymmetric collapse, bottoming, tear, or permanent lean is a failure.
