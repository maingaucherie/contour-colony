"""Unit definitions. Plain data: no logic.

Movement cost: a unit crossing one cell of ground with slope s spends
(1 + s / slope_divisor_deg) "cost-cells". Time and battery both scale with
cost-cells, so steep ground is slower and drains more per cell.
"""

UNITS = {
    "scavenger": {
        "name": "scavenger",
        "start_count": 2,
        "base_speed_cells_per_s": 3.0,
        "battery": 100.0,
        "drain_per_cost_cell": 0.4,
        "cargo": 2,                  # scrap
        "sight_cells": 2.5,          # spots debris this close
        "pickup_s": 1.5,
        "pickup_energy": 1.0,
        "unload_s": 2.0,
        "launch_stagger_s": 1.5,     # starting units leave the dock this far apart
        "bay_cost": {"scrap": 6, "parts": 2}, "bay_time_s": 15.0, "unlocked_by": None,
    },
    "constructor": {
        "name": "constructor",
        "start_count": 1,
        "base_speed_cells_per_s": 2.6,
        "battery": 100.0,
        "drain_per_cost_cell": 0.4,
        "cargo": 10,                 # build items, any mix
        "sight_cells": 2.5,
        "load_s": 1.5,
        "build_rate": 1.0,           # seconds of build_time done per second of work
        "build_drain_per_s": 0.3,
        "launch_stagger_s": 0.5,
        "bay_cost": {"scrap": 12, "parts": 6}, "bay_time_s": 25.0, "unlocked_by": None,
    },
    "survey_rover": {
        "name": "survey rover",
        "start_count": 0,
        "base_speed_cells_per_s": 3.4,
        "battery": 100.0,
        "drain_per_cost_cell": 0.35,
        "cargo": 0,
        "sweep_radius_cells": 4.0,   # raised to level 1 around it while driving
        "sight_cells": 7.0,          # spots debris this close
        "linger_s": 5.0,             # standing still this long raises the spot to level 2
        "linger_radius_cells": 3.0,
        "linger_drain_per_s": 0.2,
        "launch_stagger_s": 0.0,
        "bay_cost": {"scrap": 10, "parts": 4}, "bay_time_s": 20.0, "unlocked_by": "field_survey",
    },
    "hauler": {
        "name": "hauler",
        "start_count": 0,
        "base_speed_cells_per_s": 3.4,
        "battery": 100.0,
        "drain_per_cost_cell": 0.35,
        "cargo": 10,                 # items of one type
        "sight_cells": 2.5,
        "load_s": 0.8,
        "launch_stagger_s": 0.0,
        "bay_cost": {"scrap": 12, "parts": 4}, "bay_time_s": 20.0, "unlocked_by": "logistics_1",
    },
}

# Scavengers with no known debris search: they drive to a random reachable
# spot this far away (cells) and look around on the way.
SEARCH_DISTANCE_CELLS = (6.0, 18.0)
SEARCH_ATTEMPTS = 12

# Order of the rover bay's build list.
BAY_MENU = ("scavenger", "constructor", "survey_rover", "hauler")

# Shared unit rules.
SLOPE_DIVISOR_DEG = 5.0              # speed = base / (1 + slope / SLOPE_DIVISOR_DEG)
LOW_BATTERY_FRACTION = 0.2           # below this, drop the job and go charge
TOP_UP_BELOW_FRACTION = 0.6          # when docked below this, charge to full before the next job
TRIP_SAFETY_FACTOR = 1.25            # planned energy is multiplied by this before checking range
STRANDED_TRICKLE_PER_S = 0.3        # battery a stranded unit's emergency panels recover per second, in full sun
STRANDED_RESUME_FRACTION = 0.3       # ... until it has at least this much, and enough to reach a charger
RELAY_PLANNING_FRACTION = 1.0        # a far job is taken via a charger near it if it fits in a full battery
IDLE_RETHINK_S = 2.0                 # idle units look for work this often
# Units with nothing to unload prefer a charging pad over a storage dock (the
# lander) up to this much extra drive (cost-cells), and move off a storage dock
# to a free pad within it, so docks stay open for units bringing cargo.
PARK_AWAY_FROM_STORAGE_COST = 40.0
TOP_UP_IDLE_FRACTION = 0.9           # an idle unit away from a charger goes to charge below this
PARK_OFFSET_CELLS = 1.2              # a charged, idle unit gives up its dock and waits this far further out
TRAIL_POINTS = 40                    # trail history kept per unit, one point per tick

# Driving feel (cosmetic: planning, battery and arrival use the planned path).
# The drawn position steers toward the planned one with a gentle lag, which
# rounds off path corners, plus a slow, shallow weave like small course
# corrections.
WOBBLE_AMPLITUDE_CELLS = (0.08, 0.16)   # per-unit range of the weave
WOBBLE_WAVELENGTH_CELLS = (6.0, 10.0)   # per-unit range
WOBBLE_SECOND_HARMONIC = 0.0            # irregular second wave (0 = off)
WOBBLE_RAMP_CELLS = 1.5                 # the weave fades in after setting off and out before arriving
WOBBLE_TURN_SMOOTHING = 0.12            # how fast the sideways direction follows turns, per tick
STEER_FOLLOW = 0.3                      # fraction of the gap to the planned position closed per tick
HEADING_SMOOTHING = 0.25                # how fast the drawn heading turns, per tick

# Paths keep this far from structures they aren't visiting (beyond the footprint).
STRUCTURE_CLEARANCE_CELLS = 0.6
