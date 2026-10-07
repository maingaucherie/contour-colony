"""Structure definitions. Plain data: no logic.

footprint_cells  radius of the structure on the ground, in cells
max_slope_deg    steepest ground under the footprint it can be built on
build_cost       items delivered by constructors; build_time_s of assembly after that
power_kw         generation (lander, solar arrays at full sun)
generates_kw     generation only while a recipe cycle runs (fuel cells, reactors)
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
chance           {item: odds}: that output appears only with these odds per cycle
chance_by_zone   the same, by the zone of the ground it stands on (see geology.py)
picks_one        the recipe yields ONE of its outputs per cycle, picked at random
                 with the weights in sorts[zone of the ground it stands on]
sun_speed        recipe speed from the darkest to the brightest ground (a solar concentrator)
heat             warms up while working and cools when idle; runs at heat x
                 speed, never slower than cold_speed
waste_heat       runs `speed` times faster within gap_cells of a working one of `from`
wear_per_cycle   wear added by each recipe cycle (0..1 scale; see WEAR)
accepts          storage that takes only these items (the default is anything but waste)
cost_per_cell    conveyors, monorails: build cost per cell of length (rounded up;
                 plus build_time_per_cell_s)
carries          a line that moves items (conveyors.py): max_cells long, items_per_s
snap             tiles edge to edge with others of its kind on a (dx, dy) lattice
                 instead of keeping a gap; farm_bonus per touching neighbour
unique           only one may be built
phases           the mass driver's bills of goods (see massdriver.py)
unlocked_by      research node, or None when available from the start
"""

STRUCTURES = {
    "lander": {
        "name": "lander", "footprint_cells": 2.2, "max_slope_deg": 5.0,
        "power_kw": 15.0, "grid_reach_cells": 6.0,
        "storage": 300, "charge_slots": 4, "charge_per_s": 5.0, "dock_radius_cells": 3.2,
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
        "build_cost": {"sinter": 12, "parts": 2}, "build_time_s": 10.0,
        "draw_kw": 6.0, "scan_radius_cells": 240.0, "sweep_period_s": 30.0, "unlocked_by": "prospecting",
    },
    "charging_pad": {
        "name": "charging pad", "footprint_cells": 1.0, "max_slope_deg": 5.0,
        "build_cost": {"sinter": 8, "parts": 1}, "build_time_s": 10.0,
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
        "build_cost": {"sinter": 30, "parts": 4}, "build_time_s": 25.0,
        "power_kw": 8.0, "grid_reach_cells": 5.0,
        "charge_slots": 2, "charge_per_s": 5.0, "dock_radius_cells": 1.9, "storage": 40,
        "sight_cells": 5.0, "unlocked_by": "logistics_1",
    },
    "rover_bay": {
        "name": "rover bay", "footprint_cells": 1.3, "max_slope_deg": 5.0,
        "build_cost": {"scrap": 20, "parts": 4}, "build_time_s": 20.0,
        "draw_kw": 5.0, "unlocked_by": None,
    },
    "scrap_furnace": {
        # The first iron: melts down wreckage. As fast as the scavengers can feed it.
        "name": "scrap furnace", "footprint_cells": 1.0, "max_slope_deg": 5.0,
        "build_cost": {"scrap": 15, "parts": 2}, "build_time_s": 12.0,
        "draw_kw": 4.0, "unlocked_by": None,
        "recipe": {"in": {"scrap": 2}, "out": {"iron": 1}, "time_s": 6.0}, "wear_per_cycle": 0.001,
    },
    "sorter": {
        # Sifts regolith for mineral grains. Each cycle yields ONE of its
        # outputs, picked at random with the weights of the ground the sorter
        # stands on (sorts: zone -> weights), so where it is built matters.
        "name": "sorter", "footprint_cells": 1.0, "max_slope_deg": 5.0,
        "build_cost": {"scrap": 15, "parts": 3}, "build_time_s": 14.0,
        "draw_kw": 5.0, "unlocked_by": "sorting",
        "recipe": {"in": {"regolith": 3}, "out": {"ilmenite": 1, "anorthite": 1, "kreep": 1}, "time_s": 3.0},
        "picks_one": True,
        "sorts": {"mare": {"ilmenite": 0.65, "anorthite": 0.3, "kreep": 0.05},
                  "highlands": {"ilmenite": 0.2, "anorthite": 0.75, "kreep": 0.05},
                  "kreep": {"ilmenite": 0.15, "anorthite": 0.35, "kreep": 0.5}},
        "wear_per_cycle": 0.001,
    },
    "ilmenite_mine": {
        "name": "ilmenite drill", "footprint_cells": 1.1, "max_slope_deg": 5.0,
        "build_cost": {"sinter": 15, "parts": 2}, "build_time_s": 18.0,
        "draw_kw": 6.0, "requires_field": "ilmenite", "unlocked_by": "prospecting",
        "recipe": {"in": {}, "out": {"ilmenite": 2}, "time_s": 6.0}, "wear_per_cycle": 0.0012,
    },
    "anorthite_mine": {
        "name": "anorthite drill", "footprint_cells": 1.1, "max_slope_deg": 5.0,
        "build_cost": {"sinter": 15, "parts": 2}, "build_time_s": 18.0,
        "draw_kw": 6.0, "requires_field": "anorthite", "unlocked_by": "prospecting",
        "recipe": {"in": {}, "out": {"anorthite": 2}, "time_s": 6.0}, "wear_per_cycle": 0.0012,
    },
    "kreep_mine": {
        "name": "KREEP drill", "footprint_cells": 1.1, "max_slope_deg": 5.0,
        "build_cost": {"sinter": 15, "parts": 2}, "build_time_s": 18.0,
        "draw_kw": 6.0, "requires_field": "kreep", "unlocked_by": "prospecting",
        "recipe": {"in": {}, "out": {"kreep": 1}, "time_s": 6.0}, "wear_per_cycle": 0.0012,
    },
    "ice_mine": {
        "name": "ice drill", "footprint_cells": 1.1, "max_slope_deg": 5.0,
        "build_cost": {"sinter": 15, "parts": 2}, "build_time_s": 18.0,
        "draw_kw": 6.0, "requires_field": "ice", "unlocked_by": "prospecting",
        "recipe": {"in": {}, "out": {"ice": 2}, "time_s": 8.0}, "wear_per_cycle": 0.0012,
    },
    "crusher": {
        "name": "crusher", "footprint_cells": 1.1, "max_slope_deg": 5.0,
        "build_cost": {"sinter": 15, "parts": 2}, "build_time_s": 15.0,
        "draw_kw": 8.0, "unlocked_by": "extraction",
        "recipe": {"in": {"ilmenite": 2}, "out": {"concentrate": 1}, "time_s": 4.0}, "wear_per_cycle": 0.0012,
    },
    "ice_melter": {
        "name": "ice melter", "footprint_cells": 1.0, "max_slope_deg": 5.0,
        "build_cost": {"sinter": 10, "parts": 1}, "build_time_s": 12.0,
        "draw_kw": 5.0, "unlocked_by": "extraction",
        "recipe": {"in": {"ice": 1}, "out": {"water": 1}, "time_s": 3.0}, "wear_per_cycle": 0.0006,
        "waste_heat": {"from": ("reduction_furnace", "sinter_kiln"), "gap_cells": 1.5, "speed": 2.0},
    },
    "sinter_kiln": {
        "name": "sinter kiln", "footprint_cells": 1.1, "max_slope_deg": 5.0,
        "build_cost": {"scrap": 15, "parts": 3}, "build_time_s": 15.0,
        "draw_kw": 10.0, "unlocked_by": None,
        "recipe": {"in": {"regolith": 3}, "out": {"sinter": 1}, "time_s": 5.0}, "wear_per_cycle": 0.001,
        "sun_speed": (0.5, 1.4),
    },
    "electrolyzer": {
        "name": "electrolyzer", "footprint_cells": 1.2, "max_slope_deg": 5.0,
        "build_cost": {"sinter": 20, "parts": 3}, "build_time_s": 25.0,
        "draw_kw": 14.0, "unlocked_by": "electrolysis",
        "recipe": {"in": {"water": 1}, "out": {"hydrogen": 2, "oxygen": 1}, "time_s": 4.0}, "wear_per_cycle": 0.001,
    },
    "reduction_furnace": {
        "name": "reduction furnace", "footprint_cells": 1.3, "max_slope_deg": 5.0,
        "build_cost": {"sinter": 30, "iron": 10, "parts": 3}, "build_time_s": 30.0,
        "draw_kw": 16.0, "unlocked_by": "extraction",
        "recipe": {"in": {"concentrate": 2, "hydrogen": 2}, "out": {"iron": 1, "titania": 1, "water": 1}, "time_s": 6.0},
        "wear_per_cycle": 0.0015,
        "heat": {"warm_up_s": 60.0, "cool_s": 90.0, "cold_speed": 0.25},
    },
    "machine_shop": {
        "name": "machine shop", "footprint_cells": 1.2, "max_slope_deg": 5.0,
        "build_cost": {"scrap": 20, "parts": 4}, "build_time_s": 25.0,
        "draw_kw": 8.0, "unlocked_by": None,
        "recipe": {"in": {"iron": 1}, "out": {"parts": 1}, "time_s": 6.0}, "wear_per_cycle": 0.0012,
    },
    "maintenance_hangar": {
        # Home for maintenance drones: charges them and keeps machine parts for repairs.
        "name": "maintenance hangar", "footprint_cells": 1.3, "max_slope_deg": 5.0,
        "build_cost": {"sinter": 20, "parts": 3}, "build_time_s": 25.0,
        "draw_kw": 3.0, "charge_slots": 2, "charge_per_s": 6.0, "dock_radius_cells": 1.9,
        "storage": 30, "accepts": ("parts",), "unlocked_by": "maintenance",
    },
    # Tier II industry ----------------------------------------------------------
    "volatiles_oven": {
        # Bakes regolith for the gases the solar wind left in it: hydrogen without
        # any ice, and now and then a trace of helium-3 (chance: odds per cycle).
        "name": "volatiles oven", "footprint_cells": 1.1, "max_slope_deg": 5.0,
        "build_cost": {"sinter": 20, "parts": 2}, "build_time_s": 20.0,
        "draw_kw": 12.0, "unlocked_by": "volatiles",
        "recipe": {"in": {"regolith": 6}, "out": {"hydrogen": 2, "he3": 1}, "time_s": 6.0},
        "chance": {"he3": 0.1}, "wear_per_cycle": 0.001,
    },
    "aluminium_cell": {
        # Molten-salt electrolysis of anorthite: aluminium and oxygen, and slag to cart away.
        "name": "aluminium cell", "footprint_cells": 1.3, "max_slope_deg": 5.0,
        "build_cost": {"sinter": 25, "iron": 10, "parts": 2}, "build_time_s": 25.0,
        "draw_kw": 18.0, "unlocked_by": "aluminium",
        "recipe": {"in": {"anorthite": 2}, "out": {"aluminium": 1, "oxygen": 1, "slag": 1}, "time_s": 6.0},
        "wear_per_cycle": 0.0015,
    },
    "slag_heap": {
        # Where waste goes: takes slag only, and fills up.
        "name": "slag heap", "footprint_cells": 1.4, "max_slope_deg": 12.0,
        "build_cost": {"sinter": 10}, "build_time_s": 10.0,
        "storage": 300, "accepts": ("slag",), "dock_slots": 2, "dock_radius_cells": 2.0,
        "unlocked_by": "aluminium",
    },
    "fabrication_line": {
        # Parts from iron and aluminium, four at a time, with offcuts (scrap) left over.
        "name": "fabrication line", "footprint_cells": 1.4, "max_slope_deg": 5.0,
        "build_cost": {"sinter": 30, "parts": 4, "aluminium": 10}, "build_time_s": 30.0,
        "draw_kw": 15.0, "unlocked_by": "fabrication",
        "recipe": {"in": {"iron": 2, "aluminium": 1}, "out": {"parts": 4, "scrap": 1}, "time_s": 6.0},
        "wear_per_cycle": 0.0015,
    },
    "titanium_refinery": {
        "name": "titanium refinery", "footprint_cells": 1.3, "max_slope_deg": 5.0,
        "build_cost": {"sinter": 30, "parts": 4, "aluminium": 10}, "build_time_s": 30.0,
        "draw_kw": 20.0, "unlocked_by": "titanium",
        "recipe": {"in": {"titania": 2}, "out": {"titanium": 1, "oxygen": 1}, "time_s": 8.0},
        "wear_per_cycle": 0.0015,
    },
    "frame_works": {
        "name": "frame works", "footprint_cells": 1.3, "max_slope_deg": 5.0,
        "build_cost": {"sinter": 30, "parts": 6}, "build_time_s": 30.0,
        "draw_kw": 10.0, "unlocked_by": "titanium",
        "recipe": {"in": {"titanium": 1, "aluminium": 1}, "out": {"frames": 1}, "time_s": 8.0},
        "wear_per_cycle": 0.0012,
    },
    "rare_earth_separator": {
        "name": "rare-earth separator", "footprint_cells": 1.2, "max_slope_deg": 5.0,
        "build_cost": {"sinter": 25, "parts": 4, "aluminium": 5}, "build_time_s": 25.0,
        "draw_kw": 12.0, "unlocked_by": "rare_earths",
        "recipe": {"in": {"kreep": 2}, "out": {"rare_earths": 2, "thorium": 1}, "time_s": 8.0},
        "wear_per_cycle": 0.0012,
    },
    "electronics_plant": {
        "name": "electronics plant", "footprint_cells": 1.2, "max_slope_deg": 5.0,
        "build_cost": {"sinter": 25, "parts": 6, "aluminium": 10}, "build_time_s": 30.0,
        "draw_kw": 12.0, "unlocked_by": "rare_earths",
        "recipe": {"in": {"rare_earths": 1, "parts": 1}, "out": {"electronics": 2}, "time_s": 8.0},
        "wear_per_cycle": 0.001,
    },
    # Power ladder ---------------------------------------------------------------
    "power_tower": {
        # A tall, long-reach pylon: carries power across the site.
        "name": "power tower", "footprint_cells": 0.5, "max_slope_deg": 20.0,
        "build_cost": {"sinter": 4, "aluminium": 4}, "build_time_s": 8.0,
        "grid_reach_cells": 24.0, "unlocked_by": "aluminium",
    },
    "fuel_cell_bank": {
        # Burns hydrogen and oxygen back into power (and water): gas that would
        # otherwise vent. Generates only while it has fuel (generates_kw).
        "name": "fuel cell bank", "footprint_cells": 1.0, "max_slope_deg": 5.0,
        "build_cost": {"sinter": 15, "parts": 3, "aluminium": 4}, "build_time_s": 15.0,
        "grid_reach_cells": 4.0, "generates_kw": 15.0, "unlocked_by": "fuel_cells",
        "recipe": {"in": {"hydrogen": 2, "oxygen": 1}, "out": {"water": 1}, "time_s": 6.0},
        "wear_per_cycle": 0.0005,
    },
    "heliostat_tower": {
        # A ring of mirrors focused on a Stirling engine: about three times a
        # solar array's power for its ground, but it needs a wide flat circle.
        "name": "heliostat tower", "footprint_cells": 2.4, "max_slope_deg": 5.0,
        "build_cost": {"sinter": 40, "parts": 6, "aluminium": 15}, "build_time_s": 35.0,
        "power_kw": 60.0, "grid_reach_cells": 6.0, "unlocked_by": "solar_thermal",
    },
    "fuel_fabricator": {
        "name": "fuel fabricator", "footprint_cells": 1.1, "max_slope_deg": 5.0,
        "build_cost": {"sinter": 25, "parts": 6, "aluminium": 10}, "build_time_s": 25.0,
        "draw_kw": 10.0, "unlocked_by": "fission",
        "recipe": {"in": {"thorium": 2}, "out": {"fuel_rods": 1}, "time_s": 10.0}, "wear_per_cycle": 0.001,
    },
    "fission_reactor": {
        # Kilopower-style: steady power from fuel rods, one every two minutes,
        # leaving spent fuel. It needs radiator panels close by to shed its
        # heat: cooling_radiators for full output, half output with none.
        "name": "fission reactor", "footprint_cells": 1.3, "max_slope_deg": 5.0,
        "build_cost": {"sinter": 40, "parts": 10, "aluminium": 20, "titanium": 10}, "build_time_s": 40.0,
        "grid_reach_cells": 6.0, "generates_kw": 60.0, "unlocked_by": "fission",
        "recipe": {"in": {"fuel_rods": 1}, "out": {"spent_fuel": 1}, "time_s": 120.0},
        "cooling_radiators": 2, "cooling_reach_cells": 1.5, "wear_per_cycle": 0.004,
    },
    "radiator": {
        # Sheds a reactor's heat. Panels snap edge to edge like solar arrays.
        "name": "radiator panel", "footprint_cells": 0.8, "max_slope_deg": 8.0,
        "build_cost": {"aluminium": 4, "sinter": 2}, "build_time_s": 6.0,
        "unlocked_by": "fission", "snap": {"cell": (1.5, 0.9), "farm_bonus": 0.0},
    },
    "cask_store": {
        "name": "cask store", "footprint_cells": 1.1, "max_slope_deg": 5.0,
        "build_cost": {"sinter": 20, "parts": 2}, "build_time_s": 12.0,
        "storage": 40, "accepts": ("spent_fuel",), "dock_slots": 1, "dock_radius_cells": 1.7,
        "unlocked_by": "fission",
    },
    # Tier III (after the Coils).
    "molten_regolith_cell": {
        # Molten regolith electrolysis: melt raw regolith at 1600 C and pull
        # the metals out with current. No sorting, crushing or reducing: the
        # whole ore chain in one hungry box. What metal comes out depends on
        # the ground (mare: titania; highlands: aluminium), and it leaves slag.
        "name": "molten regolith cell", "footprint_cells": 1.6, "max_slope_deg": 5.0,
        "build_cost": {"sinter": 40, "parts": 8, "titanium": 15, "electronics": 6}, "build_time_s": 40.0,
        "draw_kw": 80.0, "unlocked_by": "molten_regolith",
        "recipe": {"in": {"regolith": 5}, "out": {"iron": 1, "titania": 1, "aluminium": 1, "oxygen": 2, "slag": 2},
                   "time_s": 6.0},
        "chance_by_zone": {"mare": {"titania": 0.9, "aluminium": 0.3},
                           "highlands": {"titania": 0.2, "aluminium": 0.9},
                           "kreep": {"titania": 0.5, "aluminium": 0.5}},
        "wear_per_cycle": 0.003,
    },
    "deuterium_still": {
        # Cryogenic distillation of water for its heavy fraction. Lunar ice is
        # rich in deuterium, but it still takes a lot of water for a little.
        "name": "deuterium still", "footprint_cells": 1.1, "max_slope_deg": 5.0,
        "build_cost": {"sinter": 25, "parts": 4, "aluminium": 10, "titanium": 5}, "build_time_s": 25.0,
        "draw_kw": 20.0, "unlocked_by": "fusion",
        "recipe": {"in": {"water": 4}, "out": {"deuterium": 1}, "time_s": 10.0}, "wear_per_cycle": 0.001,
    },
    "fusion_reactor": {
        # Deuterium and helium-3: aneutronic fusion, so no spent fuel, only heat.
        # Five times a fission reactor, and it needs three times the radiators.
        "name": "fusion reactor", "footprint_cells": 1.8, "max_slope_deg": 5.0,
        "build_cost": {"sinter": 60, "parts": 10, "aluminium": 30, "titanium": 30, "electronics": 20},
        "build_time_s": 60.0, "grid_reach_cells": 7.0, "generates_kw": 300.0, "unlocked_by": "fusion",
        "recipe": {"in": {"he3": 1, "deuterium": 1}, "out": {}, "time_s": 20.0},
        "cooling_radiators": 6, "cooling_reach_cells": 2.0, "wear_per_cycle": 0.002,
    },
    "mass_driver": {
        # The goal. Built once, then completed in phases: each phase is a bill
        # of goods delivered like any other (haulers, conveyors), and each one
        # finished opens the next tier of research. After the last bill it
        # charges for launch_charge_s, drawing launch_kw, and fires: the site
        # is won.
        "name": "mass driver", "footprint_cells": 3.0, "max_slope_deg": 5.0,
        "build_cost": {"scrap": 40, "parts": 8}, "build_time_s": 40.0,
        "unlocked_by": None, "unique": True,
        "phases": (
            {"name": "foundation", "needs": {"sinter": 150, "iron": 40}},
            {"name": "rails", "needs": {"iron": 300, "parts": 150, "aluminium": 120}},
            {"name": "coils", "needs": {"parts": 300, "titanium": 150, "electronics": 100}},
            {"name": "launch", "needs": {"frames": 200, "electronics": 150}},
        ),
        "launch_kw": 300.0, "launch_charge_s": 60.0,
        # After the launch it ships exports: hauled into a hold of ship_hold
        # items, ship_batch launched every ship_every_s while it has ship_kw,
        # each paid at ship_price_mult times the market price.
        "ships": ("frames", "electronics", "titanium", "aluminium", "he3", "fuel_rods"),
        "ship_hold": 40, "ship_batch": 10, "ship_every_s": 20.0, "ship_kw": 120.0, "ship_price_mult": 2.0,
    },
    "conveyor": {
        # A belt from one building to another (see conveyors.py), placed by
        # clicking its source and then its destination. footprint_cells is
        # only its width; its length comes from the two buildings.
        "name": "conveyor", "footprint_cells": 0.5, "max_slope_deg": 5.0,
        "cost_per_cell": {"sinter": 1}, "build_time_s": 4.0, "build_time_per_cell_s": 1.0,
        "draw_kw": 0.5, "unlocked_by": "conveyors", "line": True,
        "carries": True, "max_cells": 10.0, "items_per_s": 1.0,
    },
    "monorail": {
        # A line on pillars between two buildings, for bulk over long distances:
        # cars run back and forth carrying items_per_s. Unlike a belt it may join
        # two stores (store_to_store: a far depot emptied into one at home), it
        # stands clear of the ground (elevated: crosses anything, no grading, up
        # to max_slope_deg), and it costs aluminium as well as sinter.
        "name": "monorail", "footprint_cells": 0.5, "max_slope_deg": 20.0,
        "cost_per_cell": {"sinter": 1, "aluminium": 0.25}, "build_time_s": 10.0, "build_time_per_cell_s": 0.3,
        "draw_kw": 6.0, "unlocked_by": "monorail", "line": True,
        "carries": True, "max_cells": 120.0, "items_per_s": 3.0, "store_to_store": True, "elevated": True,
    },
    "road": {
        # A graded strip rovers drive twice as fast on (see roads.py), placed
        # by clicking its two ends. Paid in credits: credits_per_cell, plus
        # grading for ground steeper than max_slope_deg (up to ROAD_MAX_SLOPE_DEG).
        "name": "road", "footprint_cells": 0.4, "max_slope_deg": 5.0,
        "credits_per_cell": 2, "build_time_s": 2.0, "build_time_per_cell_s": 0.5,
        "unlocked_by": None, "line": True,
    },
}

# The build menu: one tab per category, in this order.
BUILD_CATEGORIES = (
    ("goal", ("mass_driver",)),
    ("power", ("solar", "pylon", "power_tower", "fuel_cell_bank", "heliostat_tower", "fuel_fabricator",
               "fission_reactor", "radiator", "deuterium_still", "fusion_reactor")),
    ("gather", ("rover_bay", "scanner", "ilmenite_mine", "anorthite_mine", "kreep_mine", "ice_mine")),
    ("process", ("scrap_furnace", "sinter_kiln", "sorter", "crusher", "ice_melter", "electrolyzer",
                 "reduction_furnace", "volatiles_oven", "aluminium_cell", "titanium_refinery",
                 "rare_earth_separator", "molten_regolith_cell")),
    ("make", ("machine_shop", "fabrication_line", "frame_works", "electronics_plant")),
    ("logistics", ("charging_pad", "depot", "outpost", "road", "conveyor", "monorail", "maintenance_hangar",
                   "slag_heap", "cask_store")),
)
BUILD_MENU = tuple(kind for _, kinds in BUILD_CATEGORIES for kind in kinds)

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

# Wear: production buildings wear with every cycle (wear_per_cycle, times the
# clock's wear factor and research). Past slow_from they slow down, to
# worn_speed at 100%; only in pressure mode do they break at 100%. From
# repair_at they post a repair: one machine part per `step` of wear, taking
# seconds_per_step (constructors work at half that rate, drones at full).
WEAR = {"slow_from": 0.5, "worn_speed": 0.5, "repair_at": 0.5, "step": 0.1, "seconds_per_step": 4.0}

# Clock speed: production buildings can be underclocked (less power and wear)
# any time, and overclocked once researched. speed x clock, power x "power",
# wear x "wear". The order is the order J cycles through.
CLOCKS = (
    (1.0, {"power": 1.0, "wear": 1.0}),
    (1.5, {"power": 2.0, "wear": 2.0, "research": "overclock"}),
    (0.5, {"power": 0.45, "wear": 0.4}),
)

# Minimum clear gap between footprints, in cells.
PLACEMENT_GAP_CELLS = 0.4
SNAP_RADIUS_CELLS = 3.0              # a snapping structure this close to one of its kind clicks onto it

# Direct feed: a producer touching (within FEED_REACH_CELLS of footprint
# edges) a building that consumes one of its outputs hands it over directly,
# FEED_ITEMS_PER_S, with no hauler.
FEED_REACH_CELLS = 0.9
FEED_ITEMS_PER_S = 1.0

# Conveyors and monorails (max_cells, items_per_s in their specs): placement
# shows CONVEYOR_PICK_CELLS around the cursor as the building it would pick.
CONVEYOR_PICK_CELLS = 2.5

# Roads: at most ROAD_MAX_CELLS long, ROAD_WIDTH_CELLS wide, over ground up to
# ROAD_MAX_SLOPE_DEG (steeper than rovers can otherwise drive: a road can open
# a pass). Shift-click lays the next one on from where the last one ended.
ROAD_MAX_CELLS = 24.0
ROAD_WIDTH_CELLS = 1.5
ROAD_MAX_SLOPE_DEG = 25.0

# Grading: ground steeper than a structure allows, up to GRADE_MAX_DEG, can be
# graded for credits and extra build time, per degree over the limit and per
# cell of footprint radius squared. Grading turns up regolith.
GRADE_MAX_DEG = 15.0
GRADE_CREDITS_PER_DEG = 3.0
GRADE_SECONDS_PER_DEG = 2.0
GRADE_REGOLITH_PER_DEG = 1.0
