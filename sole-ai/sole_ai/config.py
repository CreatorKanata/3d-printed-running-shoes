# sole_ai.config: central runtime tunables and input locations for sole design.
from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BLENDER_EXECUTABLE = Path("/Applications/Blender.app/Contents/MacOS/Blender")
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs" / "baseline.json"
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

# STL stores one triangle in 50 bytes after its fixed 84-byte header.
STL_HEADER_BYTES = 84
STL_TRIANGLE_BYTES = 50
MAX_STL_TRIANGLES = 10_000_000

# Sanity limits catch common unit mistakes: metres interpreted as millimetres,
# millimetres interpreted as metres, or a non-sole file passed to the pipeline.
MIN_SOLE_LENGTH_MM = 120.0
MAX_SOLE_LENGTH_MM = 400.0
MIN_SOLE_WIDTH_MM = 45.0
MAX_SOLE_WIDTH_MM = 180.0

# Mesh-split tolerances are in millimetres and protect cap-loop reconstruction.
MESH_INTERSECTION_EPSILON_MM = 1e-7
MESH_VERTEX_QUANTISATION_MM = 1e-5

# Fixed V1 plate-profile defaults shared by every generated candidate manifest.
PLATE_HEEL_RELIEF_PERCENT = 18.0
PLATE_TOE_END_PERCENT = 93.0
PLATE_ROCKER_FOLLOW_RATIO = 0.45
PLATE_HEEL_CAP_RADIUS_MM = 40.0

# FFF TPU Gyroid scale. Small connected openings avoid unsupported long bridges.
GYROID_CELL_SIZE_MM = 7.5
GYROID_SHEET_LEVEL = 0.32
GYROID_GRID_STEP_MM = 3.0

# Smooth variable-density TPMS baseline. Density is increased only along the
# forefoot propulsion zone, midfoot stability band, rim, and plate load path.
VARIABLE_LATTICE_GRID_STEP_MM = 0.5
VARIABLE_LATTICE_PREVIEW_GRID_STEP_MM = 0.8
VARIABLE_DENSITY_MIN = 0.18
VARIABLE_DENSITY_MAX = 0.55
VARIABLE_DENSITY_BASE = 0.20
VARIABLE_FOREFOOT_GAIN = 0.23
VARIABLE_MIDFOOT_GAIN = 0.10
VARIABLE_HEEL_RIM_GAIN = 0.08
VARIABLE_PLATE_PATH_GAIN = 0.08
GROUND_SKIN_THICKNESS_MM = 3.0
TOP_SKIN_THICKNESS_MM = 2.0
PLATE_CRADLE_THICKNESS_MM = 2.0
PLATE_THICKNESS_MM = 1.23
PLATE_POCKET_CLEARANCE_MM = 0.20
TPMS_WALL_MIN_MM = 2.4
TPMS_WALL_MAX_MM = 3.2
TPMS_WARP_AMPLITUDE_MM = 0.55
TPMS_WARP_WAVELENGTH_X_MM = 61.0
TPMS_WARP_WAVELENGTH_Y_MM = 89.0
TPMS_WARP_WAVELENGTH_Z_MM = 47.0
TPMS_REPAIR_VOXEL_MM = 0.4

# FFF-aware stochastic cellular foam. Nodes advance in the local build
# direction so every free branch is supported by the previous node layer.
# A 0.6 mm field keeps at least two to three samples across 1.6--1.8 mm shafts.
# The requested 1.2 mm floor remains a rejection bound, not the design target.
# Density comes from short, redundant branches rather than thicker shafts.
ORGANIC_STRUT_GRID_STEP_MM = 0.6
ORGANIC_STRUT_PREVIEW_GRID_STEP_MM = 0.8
ORGANIC_CELL_SIZE_MM = 5.0
ORGANIC_GROWTH_SEED = 260814
ORGANIC_NODE_FACTOR = 0.90
ORGANIC_MIN_PARENT_LINKS = 3
ORGANIC_MAX_PARENT_LINKS = 4
ORGANIC_MIN_NODE_SPACING_MM = 4.0
ORGANIC_MAX_NODE_SPACING_MM = 6.0
ORGANIC_LAYER_HEIGHT_MM = 3.2
ORGANIC_LAYER_JITTER_MM = 0.55
ORGANIC_MIN_LATERAL_SHIFT_MM = 1.4
ORGANIC_MAX_LATERAL_SHIFT_MM = 2.8
ORGANIC_MAX_BRANCH_ANGLE_DEG = 45.0
ORGANIC_MAX_BRIDGE_MM = 5.0
ORGANIC_CURVE_RATIO = 0.12
ORGANIC_CURVE_SAMPLES = 8
ORGANIC_MIN_BRANCH_DIAMETER_MM = 1.2
ORGANIC_DESIGN_BRANCH_DIAMETER_MM = 1.6
ORGANIC_MAX_BRANCH_DIAMETER_MM = 1.8
# Implicit overlap rounds every junction and protects the diameter floor.
ORGANIC_IMPLICIT_MERGE_MM = 0.0
ORGANIC_SMOOTH_UNION_MM = 0.05
# Keep a sampled surface away from an exact grid vertex. A positive bias can
# only shrink a shaft microscopically, so the 1.8 mm upper bound is preserved.
ORGANIC_SURFACE_VERTEX_BIAS_MM = 0.01
# Avoid exact zeroes at lattice junctions. Exact zero samples can collapse
# several marching-tetra faces onto one vertex and create non-manifold edges.
IMPLICIT_FIELD_ZERO_BIAS_MM = 1e-6
PLATE_VISIBLE_LATTICE_MARGIN_MM = 6.0
FLASH_STUDIO_BED_SIZE_MM = 220.0
FLASH_STUDIO_BED_MARGIN_MM = 5.0

# Full-volume lattice envelopes supplied explicitly by the designer. The
# topology stays connected through redundant links. V10 keeps 50% of the V8
# plan-view network density while increasing free shafts to 1.5--2.0 mm.
# Spacing scales by 1/sqrt(density), preserving the requested area ratio.
ENVELOPE_LATTICE_GRID_STEP_MM = 0.5
ENVELOPE_LATTICE_PREVIEW_GRID_STEP_MM = 0.6
ENVELOPE_LATTICE_CELL_SIZE_MM = 4.0
ENVELOPE_LATTICE_NETWORK_DENSITY_RATIO = 0.50
ENVELOPE_LATTICE_SPACING_SCALE = ENVELOPE_LATTICE_NETWORK_DENSITY_RATIO ** -0.5
ENVELOPE_LATTICE_NODE_FACTOR = 1.10 * ENVELOPE_LATTICE_NETWORK_DENSITY_RATIO
ENVELOPE_LATTICE_MIN_NODE_SPACING_MM = 3.0 * ENVELOPE_LATTICE_SPACING_SCALE
ENVELOPE_LATTICE_MAX_NODE_SPACING_MM = 4.2 * ENVELOPE_LATTICE_SPACING_SCALE
ENVELOPE_LATTICE_EDGE_NODE_SPACING_MM = 2.4 * ENVELOPE_LATTICE_SPACING_SCALE
ENVELOPE_LATTICE_LAYER_HEIGHT_MM = 4.6
ENVELOPE_LATTICE_LAYER_JITTER_MM = 0.75
ENVELOPE_LATTICE_MIN_PARENT_LINKS = 2
ENVELOPE_LATTICE_MAX_PARENT_LINKS = 3
ENVELOPE_LATTICE_MIN_EFFECTIVE_PARENT_LINKS = 2
ENVELOPE_LATTICE_MIN_AVERAGE_PARENT_LINKS = 2.2
# Sparse 2.0 mm branches cannot always take a second legal path near narrow
# boundaries. Keep the measured left/right ceiling below 9% while retaining
# the average-link, no-dead-end, side-clearance, and 45-degree build gates.
ENVELOPE_LATTICE_MAX_UNDERLINKED_NODE_RATIO = 0.09
ENVELOPE_LATTICE_CURVE_RATIO = 0.24
ENVELOPE_LATTICE_CURVE_SAMPLES = 10
ENVELOPE_LATTICE_MAX_BRANCH_ANGLE_DEG = 45.0
ENVELOPE_LATTICE_MIN_BRANCH_DIAMETER_MM = 1.5
ENVELOPE_LATTICE_MAX_BRANCH_DIAMETER_MM = 2.0
# Loads at or below this smooth-field value use the exact minimum diameter.
ENVELOPE_LATTICE_DIAMETER_LOAD_FLOOR = 0.40
ENVELOPE_LATTICE_EDGE_DIAMETER_GAIN = 0.55
ENVELOPE_LATTICE_SIDE_CLEARANCE_MM = 0.25
ENVELOPE_LATTICE_EDGE_BAND_MM = 8.0
ENVELOPE_LATTICE_EDGE_COVERAGE_TARGET_RADIUS_MM = (
    2.3 * ENVELOPE_LATTICE_SPACING_SCALE
)
ENVELOPE_LATTICE_EDGE_MAX_COVERAGE_RADIUS_MM = (
    2.8 * ENVELOPE_LATTICE_SPACING_SCALE
)
ENVELOPE_LATTICE_INTERIOR_MAX_COVERAGE_RADIUS_MM = (
    3.85 * ENVELOPE_LATTICE_SPACING_SCALE
)
ENVELOPE_LATTICE_ANCHOR_SKIN_MM = 1.2
ENVELOPE_LATTICE_THIN_SOLID_THRESHOLD_MM = 6.0
ENVELOPE_LATTICE_SMOOTH_UNION_MM = 0.22
ENVELOPE_LATTICE_SURFACE_VERTEX_BIAS_MM = 0.01

# Smooth load-zone heuristics: (longitudinal centre, Gaussian width, gain).
# Longitudinal is 0 at the heel and 1 at the toe.
ENVELOPE_LOAD_BASE = 0.16
ENVELOPE_LOAD_HEEL = (0.10, 0.14, 0.48)
ENVELOPE_LOAD_ARCH = (0.46, 0.16, 0.24)
ENVELOPE_LOAD_FOREFOOT = (0.75, 0.16, 0.62)
ENVELOPE_LOAD_TOE = (0.94, 0.08, 0.22)
ENVELOPE_LOAD_RIM_GAIN = 0.20
