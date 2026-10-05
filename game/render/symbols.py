"""Operator-console symbols: plan-view (top-down) marks for structures and units.

Structure symbols live in a unit circle scaled to the footprint, so they grow
and shrink with zoom like the terrain. Unit symbols are small markers with a
heading tick. The pictorial glyphs in glyphs.py remain as an alternative style.
"""

import math


def _poly(n, r, rot=0.0, cx=0.0, cy=0.0):
    pts = [(cx + r * math.cos(rot + 2 * math.pi * k / n), cy + r * math.sin(rot + 2 * math.pi * k / n)) for k in range(n)]
    return pts + [pts[0]]


def _box(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]


def _wave(x0, x1, y, amp, n=8):
    return [(x0 + (x1 - x0) * k / n, y + amp * math.sin(math.pi * k / 2)) for k in range(n + 1)]


_LEG = 0.55
_LANDER = [_poly(16, _LEG), _poly(8, 0.18)]
for _a in (45, 135, 225, 315):
    _r = math.radians(_a)
    _c, _s = math.cos(_r), math.sin(_r)
    _LANDER.append([(_LEG * _c, _LEG * _s), (0.95 * _c, 0.95 * _s)])
    _LANDER.append([(0.95 * _c - 0.12 * _s, 0.95 * _s + 0.12 * _c), (0.95 * _c + 0.12 * _s, 0.95 * _s - 0.12 * _c)])

STRUCTURES = {
    # Ring with four splayed legs and footpads.
    "lander": _LANDER,
    # A panel array: rectangle of cells.
    "solar": [_box(-0.95, -0.55, 0.95, 0.55), [(-0.32, -0.55), (-0.32, 0.55)], [(0.32, -0.55), (0.32, 0.55)],
              [(-0.95, 0.0), (0.95, 0.0)]],
    # A tower: small square with cross-arms.
    "pylon": [_box(-0.35, -0.35, 0.35, 0.35), [(-0.9, 0.0), (0.9, 0.0)], [(0.0, -0.9), (0.0, 0.9)]],
    # A pad: octagon with a bolt.
    "charging_pad": [_poly(8, 0.95, math.pi / 8), [(0.15, -0.55), (-0.2, 0.05), (0.2, 0.0), (-0.15, 0.55)]],
    # Storage: square with a shelf line and a door notch.
    "depot": [_box(-0.85, -0.85, 0.85, 0.85), [(-0.85, -0.1), (0.85, -0.1)], [(-0.25, 0.85), (-0.25, 0.45), (0.25, 0.45), (0.25, 0.85)]],
    # Garage: open-fronted bay with an inbound chevron.
    "rover_bay": [[(-0.9, 0.85), (-0.9, -0.85), (0.9, -0.85), (0.9, 0.85)], [(-0.4, 0.75), (0.0, 0.35), (0.4, 0.75)],
                  [(-0.9, 0.3), (-0.55, 0.3)], [(0.9, 0.3), (0.55, 0.3)]],
    # Mines: shaft circle with crossed picks / a snowflake.
    "ilmenite_mine": [_poly(14, 0.95), [(-0.5, 0.5), (0.45, -0.45)], [(0.5, 0.5), (-0.45, -0.45)],
                      [(0.25, -0.62), (0.62, -0.25)], [(-0.25, -0.62), (-0.62, -0.25)]],
    "ice_mine": [_poly(14, 0.95), [(0.0, -0.6), (0.0, 0.6)], [(-0.52, -0.3), (0.52, 0.3)], [(-0.52, 0.3), (0.52, -0.3)]],
    # Plants.
    "crusher": [_box(-0.85, -0.85, 0.85, 0.85), [(-0.7, 0.1), (-0.42, -0.25), (-0.14, 0.1), (0.14, -0.25), (0.42, 0.1), (0.7, -0.25)]],
    "ice_melter": [_poly(14, 0.95), _wave(-0.6, 0.6, -0.15, 0.15), _wave(-0.6, 0.6, 0.25, 0.15)],
    "sinter_kiln": [_box(-0.85, -0.85, 0.85, 0.85), [(-0.4, 0.45), (0.0, -0.45), (0.4, 0.45), (-0.4, 0.45)]],
}

# Unit markers: outline (unit box) and where the heading tick starts and ends.
UNITS = {
    "scavenger": {"outline": _poly(10, 0.7), "tick": (0.7, 1.45)},
    "survey_rover": {"outline": _poly(4, 0.85), "tick": (0.85, 1.55)},
    "constructor": {"outline": _poly(4, 0.85, math.pi / 4), "tick": (0.6, 1.45)},
}
