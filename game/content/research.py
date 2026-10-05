"""Research tree. Plain data: no logic.

unlocks lists structure and unit kinds; effects are read by the systems that
use them. Effects of systems from later milestones are listed but inert.
"""

RESEARCH = {
    "field_survey": {"name": "field survey", "requires": (), "cost": 50, "time_s": 30,
                     "unlocks": ("rover_bay", "survey_rover")},
    "extraction": {"name": "extraction", "requires": ("field_survey",), "cost": 80, "time_s": 45,
                   "unlocks": ("ilmenite_mine", "ice_mine", "crusher", "ice_melter")},
    "sintering": {"name": "sintering", "requires": ("extraction",), "cost": 80, "time_s": 45,
                  "unlocks": ("sinter_kiln",)},
    "logistics_1": {"name": "logistics i", "requires": (), "cost": 60, "time_s": 40,
                    "unlocks": ("depot", "outpost", "hauler")},
    "electrolysis": {"name": "electrolysis", "requires": ("sintering",), "cost": 150, "time_s": 60,
                     "unlocks": ("electrolyzer",)},
    "reduction": {"name": "reduction", "requires": ("electrolysis",), "cost": 200, "time_s": 75,
                  "unlocks": ("reduction_furnace", "machine_shop")},
    "conveyors": {"name": "conveyors", "requires": ("sintering", "logistics_1"), "cost": 150, "time_s": 60,
                  "unlocks": ("conveyor",)},
    "maintenance": {"name": "maintenance", "requires": ("reduction",), "cost": 120, "time_s": 60,
                    "unlocks": ("maintenance_hangar", "maintenance_drone")},
    "titanium": {"name": "titanium", "requires": ("reduction",), "cost": 300, "time_s": 90,
                 "unlocks": ("titanium_refinery", "frame_works")},
    "fuel_cells": {"name": "fuel cells", "requires": ("titanium",), "cost": 300, "time_s": 90,
                   "unlocks": ("fuel_cell_plant",)},
    "better_batteries": {"name": "better batteries", "requires": ("logistics_1",), "cost": 100, "time_s": 50,
                         "effects": {"battery_mult": 1.5}},
    "hardened_bearings": {"name": "hardened bearings", "requires": ("maintenance",), "cost": 150, "time_s": 60,
                          "effects": {"wear_mult": 0.6}},
    "deep_survey": {"name": "deep survey", "requires": ("field_survey",), "cost": 120, "time_s": 50,
                    "effects": {"linger_mult": 0.5, "richness_at_level_1": True}},
    "overclocking": {"name": "overclocking", "requires": ("reduction",), "cost": 200, "time_s": 75,
                     "effects": {"overclock": True}},
}

# Order of the research panel (each gets a letter key).
RESEARCH_MENU = ("field_survey", "extraction", "sintering", "logistics_1", "better_batteries",
                 "deep_survey", "electrolysis", "reduction", "conveyors", "maintenance",
                 "titanium", "fuel_cells", "hardened_bearings", "overclocking")
