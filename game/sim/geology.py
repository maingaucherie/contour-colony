"""Geology zones: what the ground is made of where. Never imports pygame.

The terrain generator plans the zones (terrain.Geology): maria (flooded
basins, the landing mare first), the cold-trap craters near the pole edge and
the KREEP province. Everything else is highland. Zones decide where fields of
each mineral form and what a sorter finds in local regolith.
"""

import math

MARE, HIGHLANDS, KREEP = "mare", "highlands", "kreep"
ZONES = (MARE, HIGHLANDS, KREEP)


def zone_at(geology, x, y, mare_core=0.85):
    """The zone at (x, y): the KREEP province, a mare (within mare_core of its
    radius: the rim belongs to the highlands), or highland."""
    kx, ky, kr = geology.kreep
    if kr and math.hypot(x - kx, y - ky) <= kr:
        return KREEP
    for mx, my, mr in geology.maria:
        if math.hypot(x - mx, y - my) <= mr * mare_core:
            return MARE
    return HIGHLANDS


def in_cold_trap(geology, x, y, reach=1.0):
    """The cold-trap crater (x, y, r) whose floor or wall (x, y) is in, or None."""
    for c in geology.cold_traps:
        if math.hypot(x - c[0], y - c[1]) <= c[2] * reach:
            return c
    return None
