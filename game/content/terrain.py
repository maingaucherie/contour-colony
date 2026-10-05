"""Terrain generation and contour tables. Plain data: no logic."""

# Site grid. Heights are sampled at GRID_SIZE x GRID_SIZE points, CELL_SIZE_M apart.
GRID_SIZE = 256
CELL_SIZE_M = 400.0

# Fractal value noise (the highland base layer).
NOISE_OCTAVES = 6
NOISE_BASE_PERIOD_CELLS = 64.0
NOISE_LACUNARITY = 2.0
NOISE_PERSISTENCE = 0.5
NOISE_AMPLITUDE_M = 950.0

# Flooded basins (mare-like flats). Each is carved as a smooth bowl, then
# everything below its flood level is flattened toward that level.
BASIN_COUNT_RANGE = (2, 3)
BASIN_RADIUS_RANGE_CELLS = (25.0, 55.0)
BASIN_DEPTH_RANGE_M = (700.0, 1100.0)
BASIN_FLOOD_FRACTION = 0.55       # flood level above the carved floor, as a fraction of depth
BASIN_FLOOD_RESIDUAL = 0.08       # how much relief survives below the flood level

# Craters. Radii follow a power law (N(>r) ~ r^-exponent); a few large
# craters are always placed so every site has deep floors and central peaks.
CRATER_COUNT = 160
CRATER_RADIUS_MIN_CELLS = 1.5
CRATER_RADIUS_MAX_CELLS = 32.0
CRATER_POWER_LAW_EXPONENT = 1.9
CRATER_GUARANTEED_LARGE = 2
CRATER_LARGE_RADIUS_RANGE_CELLS = (14.0, 26.0)
CRATER_DEPTH_PER_DIAMETER = 0.12
CRATER_MAX_DEPTH_M = 1800.0
CRATER_RIM_RATIO = 0.3            # rim height as a fraction of depth
CRATER_EJECTA_EXTENT = 2.0        # ejecta reaches this many radii from the centre
CRATER_RIM_SAMPLES = 16           # points averaged to find the crater's reference height
CRATER_FLOOR_BLEND_INNER = 0.6    # inside this radius fraction the floor is fully levelled
CRATER_COMPLEX_RADIUS_CELLS = 8.0 # at or above this, craters get flat floors and central peaks
CRATER_COMPLEX_FLOOR_FRACTION = 0.45
CRATER_COMPLEX_PEAK_RATIO = 0.35  # central peak height as a fraction of depth
CRATER_COMPLEX_PEAK_RADIUS_FRACTION = 0.18

# Contours. The interval is the "nice" number (NICE_STEPS x 10^n) whose level
# count over the site's height range is closest to CONTOUR_TARGET_LEVELS.
# Levels are integer multiples k of it.
CONTOUR_TARGET_LEVELS = 40
CONTOUR_NICE_STEPS = (1.0, 2.0, 2.5, 5.0)
CONTOUR_CHUNK_CELLS = 32

# Detail tiers, coarsest first. A level k is in a tier when k % level_step == 0.
# Tolerance is the polyline simplification error in cells. min_zoom is the
# camera zoom (screen pixels per cell) from which the tier is used.
CONTOUR_TIERS = (
    {"level_step": 4, "tolerance_cells": 0.75, "min_zoom": 0.0},
    {"level_step": 2, "tolerance_cells": 0.5, "min_zoom": 6.5},
    {"level_step": 1, "tolerance_cells": 0.25, "min_zoom": 13.0},
)
# Contour lines are cut into pieces of at most this many segments so each piece
# can fade on its own (with zoom and with survey knowledge around it).
CONTOUR_PIECE_SEGMENTS = 6
# A tier fades in between min_zoom / FADE_RATIO and min_zoom.
CONTOUR_FADE_RATIO = 1.4
# Survey knowledge around a piece is averaged over a square of this half-size (cells).
CONTOUR_SURVEY_BLUR_CELLS = 6.0
# Brightness of contours over ground nobody has surveyed, relative to fully
# surveyed ground. Survey only brightens: it never hides lines, so none end.
CONTOUR_UNSURVEYED_BRIGHTNESS = 0.55

# Every INDEX_STEP-th level is an index contour, drawn slightly brighter.
CONTOUR_INDEX_STEP = 4

# Seeds for new sites are drawn from [0, SEED_MAX).
SEED_MAX = 1_000_000
