"""Research tree. Plain data: no logic.

unlocks lists structure and unit kinds; effects are read by the systems that
use them. phase: the number of mass driver phases that must be finished
before the node can be started (0 = from the landing). Tier I needs none,
Tier II the Foundation (1), the later Tier II industry the Rails (2), Tier
III the Coils (3).
"""

RESEARCH = {
    # Tier I: the scramble.
    "sorting": {"name": "sorting", "requires": (), "phase": 0, "cost": 50, "time_s": 30,
                "unlocks": ("sorter",)},
    "logistics_1": {"name": "logistics i", "requires": (), "phase": 0, "cost": 60, "time_s": 40,
                    "unlocks": ("depot", "outpost", "hauler")},
    "better_batteries": {"name": "better batteries", "requires": ("logistics_1",), "phase": 0, "cost": 100,
                         "time_s": 50, "effects": {"battery_mult": 1.5}},
    # Tier II: industry (after the Foundation).
    "prospecting": {"name": "prospecting", "requires": (), "phase": 1, "cost": 100, "time_s": 45,
                    "unlocks": ("scanner", "survey_rover", "ilmenite_mine", "anorthite_mine", "kreep_mine",
                                "ice_mine")},
    "deep_survey": {"name": "deep survey", "requires": ("prospecting",), "phase": 1, "cost": 120, "time_s": 50,
                    "effects": {"linger_mult": 0.5, "richness_at_level_1": True}},
    "extraction": {"name": "extraction", "requires": (), "phase": 1, "cost": 100, "time_s": 45,
                   "unlocks": ("crusher", "ice_melter", "reduction_furnace")},
    "electrolysis": {"name": "electrolysis", "requires": ("extraction",), "phase": 1, "cost": 100, "time_s": 50,
                     "unlocks": ("electrolyzer",)},
    "conveyors": {"name": "conveyors", "requires": ("logistics_1",), "phase": 1, "cost": 150, "time_s": 60,
                  "unlocks": ("conveyor",)},
    "maintenance": {"name": "maintenance", "requires": (), "phase": 1, "cost": 120, "time_s": 60,
                    "unlocks": ("maintenance_hangar", "maintenance_drone")},
    "hardened_bearings": {"name": "hardened bearings", "requires": ("maintenance",), "phase": 1, "cost": 150,
                          "time_s": 60, "effects": {"wear_mult": 0.6}},
    "overclocking": {"name": "overclocking", "requires": (), "phase": 1, "cost": 200, "time_s": 75,
                     "effects": {"overclock": True}},
    "volatiles": {"name": "volatiles", "requires": ("extraction",), "phase": 1, "cost": 100, "time_s": 50,
                  "unlocks": ("volatiles_oven",)},
    "aluminium": {"name": "aluminium", "requires": (), "phase": 1, "cost": 120, "time_s": 60,
                  "unlocks": ("aluminium_cell", "slag_heap", "power_tower")},
    "fuel_cells": {"name": "fuel cells", "requires": (), "phase": 1, "cost": 120, "time_s": 50,
                   "unlocks": ("fuel_cell_bank",)},
    "fabrication": {"name": "fabrication", "requires": ("aluminium",), "phase": 1, "cost": 150, "time_s": 60,
                    "unlocks": ("fabrication_line",)},
    # Later Tier II (after the Rails).
    "titanium": {"name": "titanium", "requires": ("extraction",), "phase": 2, "cost": 200, "time_s": 75,
                 "unlocks": ("titanium_refinery", "frame_works")},
    "rare_earths": {"name": "rare earths", "requires": (), "phase": 2, "cost": 200, "time_s": 75,
                    "unlocks": ("rare_earth_separator", "electronics_plant")},
    "monorail": {"name": "monorail", "requires": ("conveyors",), "phase": 2, "cost": 200, "time_s": 75,
                 "unlocks": ("monorail",)},
    "solar_thermal": {"name": "solar thermal", "requires": ("aluminium",), "phase": 2, "cost": 180, "time_s": 60,
                      "unlocks": ("heliostat_tower",)},
    "fission": {"name": "fission", "requires": ("rare_earths", "titanium"), "phase": 2, "cost": 300,
                "time_s": 90, "unlocks": ("fuel_fabricator", "fission_reactor", "radiator", "cask_store")},
}

# Order of the research panel (each gets a letter key).
RESEARCH_MENU = ("sorting", "logistics_1", "better_batteries",
                 "prospecting", "deep_survey", "extraction", "electrolysis", "conveyors",
                 "volatiles", "aluminium", "fabrication", "maintenance", "hardened_bearings", "overclocking",
                 "fuel_cells", "titanium", "rare_earths", "monorail", "solar_thermal", "fission")
