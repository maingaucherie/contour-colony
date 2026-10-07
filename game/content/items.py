"""Item definitions. Plain data: no logic.

value is what contracts pay per item (before the contract bonus); sell_price,
if given, is the market price, otherwise a fraction of value (see world.py).
vents: a gas a full output buffer releases instead of stopping the plant.
cap_fraction: share of colony storage this item may fill (default in world.py).
"""

ITEMS = {
    # Gathered.
    "scrap": {"name": "scrap", "tier": "raw", "sell_price": 2, "value": 2, "cap_fraction": 0.4},
    "regolith": {"name": "regolith", "tier": "raw", "value": 1, "cap_fraction": 0.4},
    "ilmenite": {"name": "ilmenite ore", "tier": "raw", "value": 3},
    "anorthite": {"name": "anorthite ore", "tier": "raw", "value": 3},
    "kreep": {"name": "KREEP ore", "tier": "raw", "value": 5},
    "ice": {"name": "ice", "tier": "raw", "value": 3},
    # Processed.
    "concentrate": {"name": "concentrate", "tier": "processed", "value": 8},
    "water": {"name": "water", "tier": "processed", "value": 6},
    "sinter": {"name": "sinter blocks", "tier": "processed", "value": 6},
    "hydrogen": {"name": "hydrogen", "tier": "refined", "value": 5, "vents": True},
    "oxygen": {"name": "oxygen", "tier": "refined", "value": 7, "vents": True},
    "iron": {"name": "iron", "tier": "refined", "value": 18},
    "titania": {"name": "titania", "tier": "refined", "value": 8},
    "titanium": {"name": "titanium", "tier": "refined", "value": 30},
    "aluminium": {"name": "aluminium", "tier": "refined", "value": 24},
    "rare_earths": {"name": "rare earths", "tier": "refined", "value": 35},
    "thorium": {"name": "thorium", "tier": "refined", "value": 40},
    "he3": {"name": "helium-3", "tier": "refined", "value": 80},
    "deuterium": {"name": "deuterium", "tier": "refined", "value": 60},
    # Manufactured.
    "parts": {"name": "machine parts", "tier": "manufactured", "value": 45},
    "frames": {"name": "frames", "tier": "manufactured", "value": 90},
    "electronics": {"name": "electronics", "tier": "manufactured", "value": 110},
    "fuel_rods": {"name": "fuel rods", "tier": "manufactured", "value": 150},
    # Waste: nothing pays for it; it has to go somewhere.
    "slag": {"name": "slag", "tier": "waste", "value": 0, "sell_price": 0},
    "spent_fuel": {"name": "spent fuel", "tier": "waste", "value": 0, "sell_price": 0},
}
