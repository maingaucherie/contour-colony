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
