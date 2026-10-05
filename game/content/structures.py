"""Structure definitions. Plain data: no logic.

footprint_cells  radius of the structure on the ground, in cells
max_slope_deg    steepest ground under the footprint it can be built on
build_cost       items delivered by constructors; build_time_s of assembly after that
power_kw         generation (lander, solar arrays at full sun)
draw_kw          consumption while built and powered
grid_reach_cells structures within this distance join the power grid through it
scan_radius_cells, sweep_period_s  scanner radar: reach and time per revolution
sight_cells      debris this close is spotted
storage          items held (any type); docks units can unload at
charge_slots     units charged at once, at charge_per_s battery units per second each
dock_slots       unload-only docks (storage without charging)
requires_field   only on a confirmed (survey level 2) field of this kind; mines
                 run their recipe faster on richer fields (time / richness), and
                 slow down as the field's reserves run out (see world.py)
recipe           per cycle: consume "in", after time_s produce "out"
sun_speed        recipe speed from the darkest to the brightest ground (a solar concentrator)
heat             warms up while working and cools when idle; runs at heat x
                 speed, never slower than cold_speed
waste_heat       runs `speed` times faster within gap_cells of a working one of `from`
snap             tiles edge to edge with others of its kind on a (dx, dy) lattice
                 instead of keeping a gap; farm_bonus per touching neighbour
unlocked_by      research node, or None when available from the start
"""

STRUCTURES = {
    "lander": {
        "name": "lander", "footprint_cells": 2.2, "max_slope_deg": 5.0,
        "power_kw": 15.0, "grid_reach_cells": 6.0,
        "storage": 200, "charge_slots": 4, "charge_per_s": 5.0, "dock_radius_cells": 3.2,
        "export_bay": True,          # contract goods delivered here count toward contracts
        "sight_cells": 8.0,          # its own sensors spot debris this close
        "buildable": False,
    },
    "solar": {
        "name": "solar array", "footprint_cells": 1.0, "max_slope_deg": 5.0,
        "build_cost": {"scrap": 10, "parts": 2}, "build_time_s": 12.0,
        "power_kw": 10.0, "grid_reach_cells": 4.0, "unlocked_by": None,
        "snap": {"cell": (1.9, 1.1), "farm_bonus": 0.05},
    },
    "pylon": {
        "name": "power pylon", "footprint_cells": 0.4, "max_slope_deg": 15.0,
        "build_cost": {"scrap": 4}, "build_time_s": 5.0,
        "grid_reach_cells": 9.0, "unlocked_by": None,
    },
    "scanner": {
        "name": "scanner", "footprint_cells": 0.9, "max_slope_deg": 5.0,
        "build_cost": {"scrap": 12, "parts": 2}, "build_time_s": 10.0,
        "draw_kw": 6.0, "scan_radius_cells": 110.0, "sweep_period_s": 30.0, "unlocked_by": None,
    },
    "charging_pad": {
        "name": "charging pad", "footprint_cells": 1.0, "max_slope_deg": 5.0,
        "build_cost": {"scrap": 8, "parts": 2}, "build_time_s": 10.0,
        "draw_kw": 3.0, "charge_slots": 2, "charge_per_s": 5.0, "dock_radius_cells": 1.5,
        "unlocked_by": None,
    },
    "depot": {
        "name": "depot", "footprint_cells": 1.1, "max_slope_deg": 5.0,
        "build_cost": {"scrap": 15}, "build_time_s": 12.0,
        "draw_kw": 1.0, "storage": 100, "dock_slots": 2, "dock_radius_cells": 1.8,
        "unlocked_by": "logistics_1",
    },
    "outpost": {
        # A forward base: its own small power plant (no grid needed), two
        # charging docks and a little storage, so the colony can spread out.
        "name": "outpost", "footprint_cells": 1.3, "max_slope_deg": 5.0,
        "build_cost": {"scrap": 30, "parts": 6}, "build_time_s": 25.0,
        "power_kw": 8.0, "grid_reach_cells": 5.0,
        "charge_slots": 2, "charge_per_s": 5.0, "dock_radius_cells": 1.9, "storage": 40,
        "sight_cells": 5.0, "unlocked_by": "logistics_1",
    },
    "rover_bay": {
        "name": "rover bay", "footprint_cells": 1.3, "max_slope_deg": 5.0,
        "build_cost": {"scrap": 20, "parts": 6}, "build_time_s": 20.0,
        "draw_kw": 5.0, "unlocked_by": "field_survey",
    },
    "ilmenite_mine": {
        "name": "ilmenite mine", "footprint_cells": 1.1, "max_slope_deg": 5.0,
        "build_cost": {"scrap": 20, "parts": 4}, "build_time_s": 18.0,
        "draw_kw": 6.0, "requires_field": "ilmenite", "unlocked_by": "extraction",
        "recipe": {"in": {}, "out": {"ilmenite": 2, "regolith": 1}, "time_s": 6.0},
    },
    "ice_mine": {
        "name": "ice mine", "footprint_cells": 1.1, "max_slope_deg": 5.0,
        "build_cost": {"scrap": 20, "parts": 4}, "build_time_s": 18.0,
        "draw_kw": 6.0, "requires_field": "ice", "unlocked_by": "extraction",
        "recipe": {"in": {}, "out": {"ice": 2, "regolith": 1}, "time_s": 8.0},
    },
    "crusher": {
        "name": "crusher", "footprint_cells": 1.1, "max_slope_deg": 5.0,
        "build_cost": {"scrap": 15, "parts": 4}, "build_time_s": 15.0,
        "draw_kw": 8.0, "unlocked_by": "extraction",
        "recipe": {"in": {"ilmenite": 2}, "out": {"concentrate": 1}, "time_s": 4.0},
    },
    "ice_melter": {
        "name": "ice melter", "footprint_cells": 1.0, "max_slope_deg": 5.0,
        "build_cost": {"scrap": 10, "parts": 2}, "build_time_s": 12.0,
        "draw_kw": 5.0, "unlocked_by": "extraction",
        "recipe": {"in": {"ice": 1}, "out": {"water": 1}, "time_s": 3.0},
        "waste_heat": {"from": ("reduction_furnace", "sinter_kiln"), "gap_cells": 1.5, "speed": 2.0},
    },
    "sinter_kiln": {
        "name": "sinter kiln", "footprint_cells": 1.1, "max_slope_deg": 5.0,
        "build_cost": {"scrap": 15, "parts": 3}, "build_time_s": 15.0,
        "draw_kw": 10.0, "unlocked_by": "sintering",
        "recipe": {"in": {"regolith": 3}, "out": {"sinter": 1}, "time_s": 5.0},
        "sun_speed": (0.5, 1.4),
    },
    "electrolyzer": {
        "name": "electrolyzer", "footprint_cells": 1.2, "max_slope_deg": 5.0,
        "build_cost": {"sinter": 20, "parts": 6}, "build_time_s": 25.0,
        "draw_kw": 14.0, "unlocked_by": "electrolysis",
        "recipe": {"in": {"water": 1}, "out": {"hydrogen": 2, "oxygen": 1}, "time_s": 4.0},
    },
    "reduction_furnace": {
        "name": "reduction furnace", "footprint_cells": 1.3, "max_slope_deg": 5.0,
        "build_cost": {"sinter": 30, "parts": 8}, "build_time_s": 30.0,
        "draw_kw": 16.0, "unlocked_by": "reduction",
        "recipe": {"in": {"concentrate": 2, "hydrogen": 2}, "out": {"iron": 1, "titania": 1, "water": 1}, "time_s": 6.0},
        "heat": {"warm_up_s": 60.0, "cool_s": 90.0, "cold_speed": 0.25},
    },
    "machine_shop": {
        "name": "machine shop", "footprint_cells": 1.2, "max_slope_deg": 5.0,
        "build_cost": {"sinter": 20, "parts": 6}, "build_time_s": 25.0,
        "draw_kw": 8.0, "unlocked_by": "reduction",
        "recipe": {"in": {"iron": 2}, "out": {"parts": 1}, "time_s": 6.0},
    },
}

# Order of the build menu.
BUILD_MENU = ("solar", "pylon", "scanner", "charging_pad", "depot", "outpost", "rover_bay",
              "ilmenite_mine", "ice_mine", "crusher", "ice_melter", "sinter_kiln",
              "electrolyzer", "reduction_furnace", "machine_shop")

# Production buffers: inputs hold this many cycles' worth of each ingredient,
# but at least INPUT_BUFFER_MIN (so a full hauler load fits); outputs hold
# OUTPUT_BUFFER of each product. A full output stops production.
INPUT_BUFFER_CYCLES = 3
INPUT_BUFFER_MIN = 10
OUTPUT_BUFFER = 10

# Deconstruction: a constructor dismantles a marked structure in this fraction of
# its build time and this fraction of its build cost returns to storage.
DECONSTRUCT_TIME_FRACTION = 0.5
DECONSTRUCT_REFUND = 0.75

# Minimum clear gap between footprints, in cells.
PLACEMENT_GAP_CELLS = 0.4
SNAP_RADIUS_CELLS = 3.0              # a snapping structure this close to one of its kind clicks onto it

# Direct feed: a producer touching (within FEED_REACH_CELLS of footprint
# edges) a building that consumes one of its outputs hands it over directly,
# FEED_ITEMS_PER_S, with no hauler.
FEED_REACH_CELLS = 0.9
FEED_ITEMS_PER_S = 1.0

# Grading: ground steeper than a structure allows, up to GRADE_MAX_DEG, can be
# graded for credits and extra build time, per degree over the limit and per
# cell of footprint radius squared. Grading turns up regolith.
GRADE_MAX_DEG = 15.0
GRADE_CREDITS_PER_DEG = 3.0
GRADE_SECONDS_PER_DEG = 2.0
GRADE_REGOLITH_PER_DEG = 1.0
