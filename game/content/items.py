"""Item definitions. Plain data: no logic.

value is what contracts pay per item (before the contract bonus); sell_price,
if given, is the market price, otherwise a fraction of value (see world.py).
vents: a gas a full output buffer releases instead of stopping the plant.
cap_fraction: share of colony storage this item may fill (default in world.py).
"""

ITEMS = {
    "scrap": {"name": "scrap", "tier": "raw", "sell_price": 2, "value": 2, "cap_fraction": 0.6},
    "ilmenite": {"name": "ilmenite ore", "tier": "raw", "value": 3},
    "ice": {"name": "ice", "tier": "raw", "value": 3},
    "regolith": {"name": "regolith", "tier": "raw", "value": 1},
    "concentrate": {"name": "concentrate", "tier": "processed", "value": 8},
    "water": {"name": "water", "tier": "processed", "value": 6},
    "sinter": {"name": "sinter blocks", "tier": "processed", "value": 6},
    "hydrogen": {"name": "hydrogen", "tier": "refined", "value": 5, "vents": True},
    "oxygen": {"name": "oxygen", "tier": "refined", "value": 7, "vents": True},
    "iron": {"name": "iron", "tier": "refined", "value": 18},
    "titania": {"name": "titania", "tier": "refined", "value": 8},
    "titanium": {"name": "titanium", "tier": "refined", "value": 30},
    "parts": {"name": "machine parts", "tier": "manufactured", "value": 45},
    "frames": {"name": "frames", "tier": "manufactured", "value": 90},
    "fuel_cells": {"name": "fuel cells", "tier": "manufactured", "value": 120},
}
