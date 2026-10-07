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
        "repair_rate": 0.5,          # repairs at half a maintenance drone's speed
        "launch_stagger_s": 0.5,
        "bay_cost": {"scrap": 12, "parts": 4}, "bay_time_s": 25.0, "unlocked_by": None,
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
        "bay_cost": {"scrap": 10, "parts": 2}, "bay_time_s": 20.0, "unlocked_by": "prospecting",
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
        "bay_cost": {"scrap": 10, "parts": 2}, "bay_time_s": 20.0, "unlocked_by": "logistics_1",
    },
}

UNITS["scraper"] = {
    # Sweeps a zone around its home (a point the player can move) in long
    # back-and-forth passes, scooping regolith, and tips it into the nearest
    # storage. Lumpy ground it passes over enough is levelled (see SCRAPE_*).
    "name": "surface scraper",
    "start_count": 1,
    "base_speed_cells_per_s": 2.4,
    "scrape_speed_fraction": 0.6,    # slower while its blade is down
    "battery": 100.0,
    "drain_per_cost_cell": 0.3,
    "cargo": 40,                     # regolith
    "cells_per_load": 0.5,           # one regolith per this many cells scraped
    "zone_radius_cells": 10.0,
    "lane_spacing_cells": 1.6,
    "min_lane_cells": 4.0,           # shorter clear stretches aren't worth a pass
    "sight_cells": 2.0,
    "unload_s": 2.0,
    "launch_stagger_s": 2.5,
    "bay_cost": {"scrap": 10, "parts": 2}, "bay_time_s": 18.0, "unlocked_by": None,
}

UNITS["maintenance_drone"] = {
    # Flies straight over everything (no slope, no pathing) to repair worn structures.
    "name": "maintenance drone",
    "start_count": 0,
    "base_speed_cells_per_s": 4.5,
    "battery": 100.0,
    "drain_per_cost_cell": 0.3,      # per cell flown
    "cargo": 6,                      # machine parts
    "flies": True,
    "docks_at": ("maintenance_hangar", "lander"),
    "sight_cells": 2.5,
    "load_s": 1.0,
    "repair_rate": 1.0,
    "repair_drain_per_s": 0.2,
    "launch_stagger_s": 0.0,
    "bay_cost": {"sinter": 8, "parts": 6}, "bay_time_s": 20.0, "unlocked_by": "maintenance",
}

UNITS["harvester"] = {
    # A roaming helium-3 plant on treads: it scrapes like a scraper, bakes the
    # regolith on board and drops it behind, keeping only the helium-3. The
    # solar wind left most of it in titanium-rich mare soil (yield_by_zone).
    "name": "helium harvester",
    "start_count": 0,
    "base_speed_cells_per_s": 2.0,
    "scrape_speed_fraction": 0.5,
    "battery": 140.0,
    "drain_per_cost_cell": 0.35,
    "cargo": 12,                     # helium-3 canisters
    "gathers": "he3",
    "cells_per_load": 6.0,           # cells scraped per canister, on mare ground
    "yield_by_zone": {"mare": 1.0, "kreep": 0.6, "highlands": 0.35},
    "zone_radius_cells": 14.0,
    "lane_spacing_cells": 1.8,
    "min_lane_cells": 4.0,
    "sight_cells": 2.5,
    "unload_s": 2.0,
    "launch_stagger_s": 0.0,
    "bay_cost": {"parts": 8, "titanium": 12, "electronics": 4}, "bay_time_s": 40.0, "unlocked_by": "harvesters",
}

UNITS["construction_drone"] = {
    # A flying constructor: straight over cliffs and craters, so far sites go up
    # without roads or relays. Smaller loads than a constructor.
    "name": "construction drone",
    "start_count": 0,
    "base_speed_cells_per_s": 5.0,
    "battery": 100.0,
    "drain_per_cost_cell": 0.25,     # per cell flown
    "cargo": 8,                      # build items, any mix
    "flies": True,
    "docks_at": ("maintenance_hangar", "lander", "outpost"),
    "sight_cells": 2.5,
    "load_s": 1.0,
    "build_rate": 1.2,
    "build_drain_per_s": 0.25,
    "repair_rate": 0.5,
    "launch_stagger_s": 0.0,
    "bay_cost": {"sinter": 10, "parts": 4, "aluminium": 6}, "bay_time_s": 25.0, "unlocked_by": "drones",
}

# Scavengers with no known debris search: they drive to a random reachable
# spot this far away (cells) and look around on the way.
SEARCH_DISTANCE_CELLS = (6.0, 18.0)
SEARCH_ATTEMPTS = 12

# Order of the rover bay's build list.
BAY_MENU = ("scavenger", "scraper", "constructor", "survey_rover", "hauler", "maintenance_drone",
            "construction_drone", "harvester")

# Shared unit rules.
SLOPE_DIVISOR_DEG = 5.0              # speed = base / (1 + slope / SLOPE_DIVISOR_DEG)
ROAD_SPEED_MULT = 2.0                # on graded roads: twice as fast (and half the battery per cell)
ROAD_SLOPE_FACTOR = 0.5              # ... and slope slows them half as much
LOW_BATTERY_FRACTION = 0.2           # below this, drop the job and go charge
TOP_UP_BELOW_FRACTION = 0.6          # when docked below this, charge to full before the next job
# Scrapers level lumpy ground: a cell steeper than SCRAPE_FLATTEN_FROM_DEG but
# no steeper than SCRAPE_FLATTEN_MAX_DEG becomes SCRAPE_FLATTEN_TO_DEG (buildable)
# once scraped over SCRAPE_PASSES times. Cliffs stay cliffs.
SCRAPE_FLATTEN_FROM_DEG = 5.0
SCRAPE_FLATTEN_MAX_DEG = 12.0
SCRAPE_FLATTEN_TO_DEG = 4.5
SCRAPE_PASSES = 3
SCRAPE_REPRICE_EVERY_S = 30          # levelled ground is re-costed for routes this often

FIELD_RANGE_MARGIN = 1.1             # a rover's route search reaches this times its full-battery range
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
BUSY_DOCK_COST = 30.0                # a charger with no free dock counts as this much further away (cost-cells)
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
