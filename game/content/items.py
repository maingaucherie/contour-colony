"""Item definitions. Plain data: no logic.

sell_price is in credits per item for goods the lander can sell directly;
value is what contracts pay per item (before the contract bonus).
"""

ITEMS = {
    "scrap": {"name": "scrap", "tier": "raw", "sell_price": 2, "value": 2},
    "ilmenite": {"name": "ilmenite ore", "tier": "raw", "value": 3},
    "ice": {"name": "ice", "tier": "raw", "value": 3},
    "regolith": {"name": "regolith", "tier": "raw", "value": 1},
    "concentrate": {"name": "concentrate", "tier": "processed", "value": 8},
    "water": {"name": "water", "tier": "processed", "value": 6},
    "sinter": {"name": "sinter blocks", "tier": "processed", "value": 6},
    "hydrogen": {"name": "hydrogen", "tier": "refined", "value": 5},
    "oxygen": {"name": "oxygen", "tier": "refined", "value": 7},
    "iron": {"name": "iron", "tier": "refined", "value": 18},
    "titania": {"name": "titania", "tier": "refined", "value": 8},
    "titanium": {"name": "titanium", "tier": "refined", "value": 30},
    "parts": {"name": "machine parts", "tier": "manufactured", "value": 45},
    "frames": {"name": "frames", "tier": "manufactured", "value": 90},
    "fuel_cells": {"name": "fuel cells", "tier": "manufactured", "value": 120},
}
