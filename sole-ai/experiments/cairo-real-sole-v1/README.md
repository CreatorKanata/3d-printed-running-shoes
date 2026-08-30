# Cairo Bio-Cell Side-Reveal — actual sole candidate

This generator uses the supplied `sole-lattice-left.stl` and
`sole-lattice-right.stl` directly. It does not scale a cube, mirror one foot, or
replace the scanned outline with a generic shoe shape.

The solid is a row of large side-facing pentagonal arches clipped independently
to every vertical solid interval in the source STL. There are no full top or
bottom skins: every arch leg lands on the lower surface and every arch apex lands
on the upper surface. The lateral faces are left open so the printed cellular
construction is visible and no cut branch tips are created there.

The default 1.2 mm walls and 22 mm pitch are an intentionally sparse first
full-size print candidate. The output is geometry-checked for a closed
two-manifold STL, but running use still requires print, compression, peel, and
fatigue tests.

Run the fast unit gates with:

```sh
python3 -m unittest discover -s tests
```

Generate a coarse visual-review STL with `--preview`; omit it for the 0.70 mm
production mesh.
