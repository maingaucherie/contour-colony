"""Simulation-wide tables: tick rate, slope rules, pathing, debris. Plain data."""

TICK_RATE = 10                       # simulation ticks per second
MAX_TICKS_PER_FRAME = 5              # catch-up limit when a frame runs long (x speed)
SIM_BUDGET_MS = 24.0                 # most simulation time per frame; fast speeds slow down past it
SIM_SPEEDS = (1, 2, 4, 8, 16, 32, 64)  # player-selectable time multipliers (, and .)

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
# Steep ground (over SLOPE_ROAD_ONLY_DEG) costs this much extra per cell, so
# routes curve around cliff bands when there's a reasonable way round.
PATH_STEEP_CELL_PENALTY = 10.0
PATH_SHORTCUT_TOLERANCE = 0.05       # a straight shortcut may cost this much more than the route it replaces
PATH_COST_SAMPLE_CELLS = 0.5         # sampling step when costing a straight segment

# Lander placement: lowest-cost open node near the centre that can reach
# at least LANDER_MIN_REACH_FRACTION of all nodes.
LANDER_SEARCH_RADIUS_FRACTION = 0.3  # of the site size, around the centre
LANDER_CENTRE_PENALTY = 0.02         # node cost added per node of distance from centre
LANDER_MIN_REACH_FRACTION = 0.3

# Debris.
DEBRIS_MAX = 80
DEBRIS_INITIAL = 80
DEBRIS_SPAWN_INTERVAL_S = 8.0
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
START_CREDITS = 300
START_STORAGE = {"scrap": 100, "parts": 50}

# Survey: levels are tracked on a grid of SURVEY_CELLS x SURVEY_CELLS terrain cells.
SURVEY_CELLS = 2
LANDING_SURVEY_RADIUS_CELLS = (16.0, 5.0)  # level 1, level 2 around the lander at touchdown
SURVEY_LEVEL_TO_TIER = (0, 1, 2)           # highest contour detail tier shown per survey level

# Resource fields (hidden until found by the scanner and confirmed by survey).
# Counts are for a FIELD_COUNT_SIZE site and scale with its area (at least
# one of each). Each mineral forms in its own geology zone (see geology.py):
# ilmenite on the maria, anorthite in the highlands, KREEP in its province,
# ice in the cold-trap craters near the pole edge.
FIELD_COUNT_SIZE = 512
FIELD_COUNTS = {"ilmenite": (6, 8), "anorthite": (5, 7), "ice": (3, 4), "kreep": (2, 3)}
FIELD_RADIUS_CELLS = {"ilmenite": (4.0, 7.0), "anorthite": (4.0, 7.0), "kreep": (3.5, 6.0)}
ICE_RADIUS_FRACTION = (0.2, 0.3)           # of the host crater's radius
ICE_MIN_CRATER_RADIUS_CELLS = 6.0
ICE_MIN_RADIUS_CELLS = 3.0
ICE_FLOOR_RING = (0.2, 1.5)                # searched band around a crater's centre, in crater radii (floor, wall foot, rim)
ICE_FLOOR_SAMPLES = 80
FIELD_RICHNESS = (0.6, 1.5)
# Field reserves: mine cycles a field yields at full richness, scaled by
# richness and area (radius / 5 cells, squared). Past that a mine keeps
# working at FIELD_DEPLETED_FLOOR of its speed, so moving to a fresh field pays.
FIELD_RESERVE_CYCLES = 500
FIELD_DEPLETED_FLOOR = 0.35
FIELD_EDGE_WOBBLE = 0.25                   # boundary irregularity, fraction of radius
FIELD_MAX_SLOPE_DEG = 5.0                  # a field's centre must be buildable ...
FIELD_FLAT_RADIUS_CELLS = 1.3             # ... over this radius, so a mine fits there
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

# Scanner: a field becomes a "signal" (hinted) after the beam passes over it this often.
FIELD_SIGNAL_PASSES = 3

# Power.
PRIORITIES = ("high", "normal", "low")

# Debris now spawns around every charging point, not just the lander.

# Colony storage: the lander and every depot form one pool. No single item may
# take more than ITEM_CAP_FRACTION of the pool (at least ITEM_CAP_MIN); haulers
# won't bring more, so its producer backs up instead of filling the colony.
# Scrap over its cap, or that doesn't fit, is sold on arrival. Any stored good
# can be sold on the market at SPOT_PRICE_FRACTION of its contract value.
ITEM_CAP_FRACTION = 0.3
ITEM_CAP_MIN = 30
SPOT_PRICE_FRACTION = 0.3
SELL_EVENT_EVERY = 10                # report automatic scrap sales in batches of this many

# Worn tracks (drawn on frequently driven ground). Wear is one point per tick
# a unit spends driving in a TRACK_CELLS square: one pass is about 7 points.
TRACK_CELLS = 2
TRACK_SHOW_WEAR = 60                 # about eight passes before a track shows ...
TRACK_FULL_WEAR = 300                # ... and this much for full strength
TRACK_WEAR_MAX = 600
TRACK_FADE_EVERY_S = 30
TRACK_FADE = 0.95                    # wear kept per fade: an unused track fades over ~20 minutes
TRACK_FORGET = 5.0

# Saves: a save from another version is refused (no conversion until the game is finished).
SAVE_VERSION = 1

# Throughput shown in the flow view and inspect panel: counted every
# RATE_SAMPLE_S over the last RATE_WINDOW_S.
RATE_SAMPLE_S = 10
RATE_WINDOW_S = 60

# Storage warning: checked every STORAGE_CHECK_S; warns once it passes this fraction.
STORAGE_CHECK_S = 5
STORAGE_FULL_FRACTION = 0.95

# Event log.
EVENT_LOG_LENGTH = 6
EVENT_SHOW_S = 12.0

# Job board (haulers). Production outputs are offered once they hold at least
# JOB_OFFER_MIN items (or are full). Score = amount / (trip cost + JOB_DISTANCE_BIAS)
# x a multiplier: the destination's priority, low for plain storage, high for
# goods an open contract needs.
JOB_OFFER_MIN = 5
JOB_DISTANCE_BIAS = 10.0
JOB_PRIORITY_MULT = {"high": 2.0, "normal": 1.0, "low": 0.5}
JOB_STORAGE_MULT = 0.25
JOB_EXPORT_MULT = 3.0
JOB_MASS_DRIVER_MULT = 2.5           # goods for the mass driver's current phase (ahead of production)
