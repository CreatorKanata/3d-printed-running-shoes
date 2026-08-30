# fusion_addin.config: tunables shared by the Fusion baseline-geometry generator.

# Fusion API length values are centimetres, while project inputs use millimetres.
MILLIMETRES_PER_FUSION_INTERNAL_UNIT = 10.0

# The selected Fusion body must match the validated candidate mesh this closely.
BODY_DIMENSION_TOLERANCE_MM = 1.0

# A conservative first plate shape stays away from the outer TPU sidewalls.
PLATE_LONGITUDINAL_MARGIN_RATIO = 0.12
PLATE_TRANSVERSE_MARGIN_RATIO = 0.16

# The pocket is larger than the PC plate to make an assembly clearance in TPU.
PLATE_POCKET_CLEARANCE_MM = 0.20

# Scale the actual sole B-Rep in plan view to create an inset, shoe-shaped plate.
# Z stays unscaled so the source sole remains the clipping envelope at every height.
PLATE_TRANSVERSE_SCALE = 0.74
PLATE_LONGITUDINAL_SCALE = 0.92

# Keep the rear cushioning zone free of PC and stop before the very tip.
PLATE_HEEL_RELIEF_PERCENT = 18.0
PLATE_TOE_END_PERCENT = 93.0
PLATE_HEEL_CAP_RADIUS_MM = 40.0

# Follow 45% of the source outsole's rocker amplitude. The remaining amplitude
# preserves a practical foam cover under the plate near the toe.
PLATE_ROCKER_FOLLOW_RATIO = 0.45
ROCKER_PROFILE_SAMPLE_COUNT = 25

# Solid TPU regions around the exposed lattice core.
GROUND_SKIN_THICKNESS_MM = 2.5
TOP_BONDING_SKIN_THICKNESS_MM = 2.0
PLATE_SUPPORT_THICKNESS_MM = 2.0
INTERLOCK_KEY_RADIUS_MM = 3.0
INTERLOCK_KEY_HEIGHT_MM = 2.2
INTERLOCK_KEY_CLEARANCE_MM = 0.30
INTERLOCK_KEY_COUNT = 6

# The longitudinal skins and split are sampled densely enough to keep Fusion's
# fitted profiles smooth without creating an unnecessarily heavy timeline.
STRUCTURE_PROFILE_SAMPLE_COUNT = 35
GROUND_SKIN_TRANSVERSE_ZONE_COUNT = 7

# Preview mode keeps same-material solids overlapping the lattice, which Fusion
# and the slicer can union. Full mesh subtraction is available but is too slow
# for interactive review on the current high-resolution envelopes.
MESH_EXCLUSION_BOOLEAN = False
