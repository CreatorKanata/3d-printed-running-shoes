# Sole AI input geometry

Place source files here without replacing the existing `3d-models/` prototypes.

```text
left/
  sole-envelope.step
  sole-envelope.stl
  upper-reference.step        # recommended
  upper-reference.stl         # recommended
  landmarks.json              # only when coordinate frames differ
right/
  sole-envelope.step
  sole-envelope.stl
  upper-reference.step        # recommended
  upper-reference.stl         # recommended
  landmarks.json              # only when coordinate frames differ
```

`sole-envelope.stl` must be a watertight binary STL in millimetres. The validation command reads it without modifying the input. The STEP file remains the Fusion source of truth.

For the designer-owned full-volume organic lattice workflow, place these
watertight millimetre solids alongside the older envelope convention:

```text
left/sole-lattice-left.step
left/sole-lattice-left.stl
right/sole-lattice-right.step
right/sole-lattice-right.stl
```

Run `python3 -m sole_ai.cli generate-envelope-lattice --side left`. The STEP
remains the editable CAD master; the matching binary STL is sampled without
modifying either source file. Separated vertical solids are preserved as
separate intervals rather than being joined across their designed air gap.
