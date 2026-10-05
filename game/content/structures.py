"""Structure definitions. Plain data: no logic.

footprint_cells  radius of the structure on the ground, in cells
max_slope_deg    steepest ground under the footprint it can be built on
build_cost       items delivered by constructors; build_time_s of assembly after that
power_kw         generation (lander, solar arrays at full sun)
draw_kw          consumption while built and powered
grid_reach_cells structures within this distance join the power grid through it
storage          items held (any type); docks units can unload at
charge_slots     units charged at once, at charge_per_s battery units per second each
dock_slots       unload-only docks (storage without charging)
requires_field   only on a confirmed (survey level 2) field of this kind
unlocked_by      research node, or None when available from the start
"""

STRUCTURES = {
    "lander": {
        "name": "lander", "footprint_cells": 2.2, "max_slope_deg": 5.0,
        "power_kw": 15.0, "grid_reach_cells": 6.0,
        "storage": 200, "charge_slots": 4, "charge_per_s": 5.0, "dock_radius_cells": 3.2,
        "buildable": False,
    },
    "solar": {
        "name": "solar array", "footprint_cells": 1.0, "max_slope_deg": 5.0,
        "build_cost": {"scrap": 10, "parts": 2}, "build_time_s": 12.0,
        "power_kw": 10.0, "grid_reach_cells": 4.0, "unlocked_by": None,
    },
    "pylon": {
        "name": "power pylon", "footprint_cells": 0.4, "max_slope_deg": 15.0,
        "build_cost": {"scrap": 4}, "build_time_s": 5.0,
        "grid_reach_cells": 6.0, "unlocked_by": None,
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
    "rover_bay": {
        "name": "rover bay", "footprint_cells": 1.3, "max_slope_deg": 5.0,
        "build_cost": {"scrap": 20, "parts": 6}, "build_time_s": 20.0,
        "draw_kw": 5.0, "unlocked_by": "field_survey",
    },
    "ilmenite_mine": {
        "name": "ilmenite mine", "footprint_cells": 1.1, "max_slope_deg": 5.0,
        "build_cost": {"scrap": 20, "parts": 4}, "build_time_s": 18.0,
        "draw_kw": 6.0, "requires_field": "ilmenite", "unlocked_by": "extraction",
    },
    "ice_mine": {
        "name": "ice mine", "footprint_cells": 1.1, "max_slope_deg": 5.0,
        "build_cost": {"scrap": 20, "parts": 4}, "build_time_s": 18.0,
        "draw_kw": 6.0, "requires_field": "ice", "unlocked_by": "extraction",
    },
    "crusher": {
        "name": "crusher", "footprint_cells": 1.1, "max_slope_deg": 5.0,
        "build_cost": {"scrap": 15, "parts": 4}, "build_time_s": 15.0,
        "draw_kw": 8.0, "unlocked_by": "extraction",
    },
    "ice_melter": {
        "name": "ice melter", "footprint_cells": 1.0, "max_slope_deg": 5.0,
        "build_cost": {"scrap": 10, "parts": 2}, "build_time_s": 12.0,
        "draw_kw": 5.0, "unlocked_by": "extraction",
    },
    "sinter_kiln": {
        "name": "sinter kiln", "footprint_cells": 1.1, "max_slope_deg": 5.0,
        "build_cost": {"scrap": 15, "parts": 3}, "build_time_s": 15.0,
        "draw_kw": 10.0, "unlocked_by": "sintering",
    },
}

# Order of the build menu.
BUILD_MENU = ("solar", "pylon", "charging_pad", "depot", "rover_bay",
              "ilmenite_mine", "ice_mine", "crusher", "ice_melter", "sinter_kiln")

# Minimum clear gap between footprints, in cells.
PLACEMENT_GAP_CELLS = 0.4
