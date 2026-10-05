"""Simulation-wide tables: tick rate, slope rules, pathing, debris. Plain data."""

TICK_RATE = 10                       # simulation ticks per second
MAX_TICKS_PER_FRAME = 5              # catch-up limit when a frame runs long
SIM_SPEEDS = (1, 2, 4)               # player-selectable time multipliers

# Slope rules (degrees).
SLOPE_BUILDABLE_DEG = 5.0
SLOPE_ROAD_ONLY_DEG = 15.0
SLOPE_IMPASSABLE_DEG = 25.0

# Pathing grid: one node per NODE_CELLS x NODE_CELLS block of terrain cells.
# A node is blocked for ground units when more than BLOCKED_FRACTION of its
# cells are steeper than SLOPE_ROAD_ONLY_DEG (no roads exist yet).
PATH_NODE_CELLS = 4
PATH_BLOCKED_FRACTION = 0.5
PATH_CACHE_SIZE = 256
PATH_LOS_STEP_NODES = 0.25           # sampling step for straight-line shortcut checks

# Lander placement: lowest-cost open node near the centre that can reach
# at least LANDER_MIN_REACH_FRACTION of all nodes.
LANDER_SEARCH_RADIUS_FRACTION = 0.3  # of the site size, around the centre
LANDER_CENTRE_PENALTY = 0.02         # node cost added per node of distance from centre
LANDER_MIN_REACH_FRACTION = 0.3

# Debris.
DEBRIS_MAX = 40
DEBRIS_INITIAL = 40
DEBRIS_SPAWN_INTERVAL_S = 20.0
DEBRIS_SCRAP_VALUE = 1
DEBRIS_MIN_SPACING_CELLS = 1.0
DEBRIS_SPAWN_ATTEMPTS = 20
DEBRIS_KINDS = ("rock", "panel", "fragment")
# Spawn weight per cell = flat bonus x rim bonus x proximity to the lander,
# where proximity = max(exp(-d^2 / (2 sigma^2)), floor). Cells a scavenger
# could not reach and return from on a full battery get no weight, so
# unreachable debris never clogs the cap.
DEBRIS_FLAT_BONUS = 3.0
DEBRIS_RIM_BONUS = 4.0
DEBRIS_RIM_RANGE = (0.85, 1.35)      # crater rim band, in crater radii
DEBRIS_PROXIMITY_SIGMA_CELLS = 20.0
DEBRIS_PROXIMITY_FLOOR = 0.05

# Starting stock. Machine parts only come from the lander's hold (and, from
# Milestone 4, supply drops) until a machine shop runs.
START_CREDITS = 60
START_STORAGE = {"scrap": 20, "parts": 30}

# Survey: levels are tracked on a grid of SURVEY_CELLS x SURVEY_CELLS terrain cells.
SURVEY_CELLS = 2
LANDING_SURVEY_RADIUS_CELLS = (16.0, 5.0)  # level 1, level 2 around the lander at touchdown
SURVEY_LEVEL_TO_TIER = (0, 1, 2)           # highest contour detail tier shown per survey level

# Resource fields (hidden until surveyed).
ILMENITE_FIELD_COUNT = (4, 6)
ICE_FIELD_COUNT = (2, 3)
ILMENITE_RADIUS_CELLS = (4.0, 7.0)
ICE_RADIUS_FRACTION = (0.2, 0.3)           # of the host crater's radius
ICE_MIN_CRATER_RADIUS_CELLS = 6.0
ICE_MIN_RADIUS_CELLS = 3.0
ICE_FLOOR_RING = (0.2, 0.45)               # floor band between central peak and wall, in crater radii
ICE_FLOOR_SAMPLES = 40
FIELD_RICHNESS = (0.6, 1.5)
FIELD_EDGE_WOBBLE = 0.25                   # boundary irregularity, fraction of radius
FIELD_MAX_SLOPE_DEG = 5.0                  # a field's centre must be buildable
FIELD_CANDIDATES = 400                     # random spots tried per field
FIELD_NEAR_LANDER_CELLS = (15.0, 45.0)     # the first ilmenite field lies this far out
FIELD_MIN_SPACING_CELLS = 10.0

# Illumination: fixed sun, a horizon march toward it, and a slope-facing term.
SUN_AZIMUTH_DEG = 135.0                    # direction the light comes from (0 = +x, 90 = +y)
SUN_ELEVATION_DEG = 12.0
ILLUMINATION_STEP_CELLS = 2
ILLUMINATION_MAX_STEPS = 24
ILLUMINATION_RANGE = (0.4, 1.0)            # shadowed .. fully lit
ILLUMINATION_GRID = 2                      # computed every this many cells

# Power.
PRIORITIES = ("high", "normal", "low")

# Debris now spawns around every charging point, not just the lander.

# Event log.
EVENT_LOG_LENGTH = 6
EVENT_SHOW_S = 12.0
