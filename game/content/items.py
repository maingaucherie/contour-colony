"""Item definitions. Plain data: no logic.

sell_price is in credits per item for goods the lander can sell directly.
"""

ITEMS = {
    "scrap": {"name": "scrap", "tier": "raw", "sell_price": 2},
    "ilmenite": {"name": "ilmenite ore", "tier": "raw"},
    "ice": {"name": "ice", "tier": "raw"},
    "regolith": {"name": "regolith", "tier": "raw"},
    "concentrate": {"name": "concentrate", "tier": "processed"},
    "water": {"name": "water", "tier": "processed"},
    "sinter": {"name": "sinter blocks", "tier": "processed"},
    "hydrogen": {"name": "hydrogen", "tier": "refined"},
    "oxygen": {"name": "oxygen", "tier": "refined"},
    "iron": {"name": "iron", "tier": "refined"},
    "titania": {"name": "titania", "tier": "refined"},
    "titanium": {"name": "titanium", "tier": "refined"},
    "parts": {"name": "machine parts", "tier": "manufactured"},
    "frames": {"name": "frames", "tier": "manufactured"},
    "fuel_cells": {"name": "fuel cells", "tier": "manufactured"},
}
