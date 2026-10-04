"""Unit definitions. Plain data: no logic.

Movement cost: a unit crossing one cell of ground with slope s spends
(1 + s / slope_divisor_deg) "cost-cells". Time and battery both scale with
cost-cells, so steep ground is slower and drains more per cell.
"""

UNITS = {
    "scavenger": {
        "start_count": 2,
        "base_speed_cells_per_s": 3.0,
        "battery": 100.0,
        "drain_per_cost_cell": 0.4,
        "cargo": 2,                  # scrap
        "pickup_s": 1.5,
        "pickup_energy": 1.0,
        "unload_s": 2.0,
        "launch_stagger_s": 1.5,     # starting units leave the dock this far apart
    },
}

# Shared unit rules.
SLOPE_DIVISOR_DEG = 5.0              # speed = base / (1 + slope / SLOPE_DIVISOR_DEG)
LOW_BATTERY_FRACTION = 0.2           # below this, drop the job and go charge
TOP_UP_BELOW_FRACTION = 0.6          # when docked below this, charge to full before the next job
TRIP_SAFETY_FACTOR = 1.25            # planned energy is multiplied by this before checking range
IDLE_RETHINK_S = 2.0                 # idle units look for work this often
TRAIL_POINTS = 40                    # trail history kept per unit, one point per tick
