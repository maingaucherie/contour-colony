"""Structure definitions. Plain data: no logic."""

STRUCTURES = {
    "lander": {
        "footprint_cells": 2.0,      # drawn size; units dock around it
        "storage": 200,              # total items held, any type
        "charge_slots": 4,           # units charged at once
        "charge_per_s": 5.0,         # battery units per second, per slot
        "dock_radius_cells": 2.3,    # dock points sit on this circle around the centre
        "power_kw": 15,
    },
}
