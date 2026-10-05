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
        "linger_s": 5.0,             # standing still this long raises the spot to level 2
        "linger_radius_cells": 3.0,
        "linger_drain_per_s": 0.2,
        "launch_stagger_s": 0.0,
        "bay_cost": {"scrap": 10, "parts": 4}, "bay_time_s": 20.0, "unlocked_by": "field_survey",
    },
}

# Order of the rover bay's build list.
BAY_MENU = ("scavenger", "constructor", "survey_rover")

# Shared unit rules.
SLOPE_DIVISOR_DEG = 5.0              # speed = base / (1 + slope / SLOPE_DIVISOR_DEG)
LOW_BATTERY_FRACTION = 0.2           # below this, drop the job and go charge
TOP_UP_BELOW_FRACTION = 0.6          # when docked below this, charge to full before the next job
TRIP_SAFETY_FACTOR = 1.25            # planned energy is multiplied by this before checking range
IDLE_RETHINK_S = 2.0                 # idle units look for work this often
TRAIL_POINTS = 40                    # trail history kept per unit, one point per tick

# Wandering: units weave around their planned path on a low sine wave. Purely
# cosmetic: planning, battery and arrival use the planned path.
WOBBLE_AMPLITUDE_CELLS = (0.25, 0.45)   # per-unit range
WOBBLE_WAVELENGTH_CELLS = (2.5, 4.0)    # per-unit range
WOBBLE_SECOND_HARMONIC = 0.4            # weight of a faster, irregular second wave
WOBBLE_RAMP_CELLS = 1.0                 # fades in after setting off and out before arriving
WOBBLE_TURN_SMOOTHING = 0.25            # how fast the sideways direction follows turns, per tick
