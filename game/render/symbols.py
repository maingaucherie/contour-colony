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


_GEAR = [(0.58 * math.cos(2 * math.pi * k / 20) * (1.0 if k % 4 < 2 else 0.72),
          0.58 * math.sin(2 * math.pi * k / 20) * (1.0 if k % 4 < 2 else 0.72)) for k in range(21)]

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
    # A radar: dish circle with a beam stub and a centre pivot.
    "scanner": [_poly(12, 0.95), _poly(6, 0.18), [(0.0, 0.0), (0.0, -0.95)], [(-0.5, -0.55), (0.0, -0.95), (0.5, -0.55)]],
    # A pad: octagon with a bolt.
    "charging_pad": [_poly(8, 0.95, math.pi / 8), [(0.15, -0.55), (-0.2, 0.05), (0.2, 0.0), (-0.15, 0.55)]],
    # Storage: square with a shelf line and a door notch.
    "depot": [_box(-0.85, -0.85, 0.85, 0.85), [(-0.85, -0.1), (0.85, -0.1)], [(-0.25, 0.85), (-0.25, 0.45), (0.25, 0.45), (0.25, 0.85)]],
    # Outpost: a hexagonal hub with a charging bolt and three legs.
    "outpost": [_poly(6, 0.95, math.pi / 6), [(0.1, -0.45), (-0.15, 0.05), (0.15, 0.0), (-0.1, 0.45)],
                [(0.0, -0.95), (0.0, -0.7)], [(-0.82, 0.47), (-0.6, 0.35)], [(0.82, 0.47), (0.6, 0.35)]],
    # Maintenance hangar: a square with an arched door and a wrench.
    "maintenance_hangar": [_box(-0.9, -0.9, 0.9, 0.9),
                           [(-0.45, 0.9), (-0.45, 0.2), (-0.3, -0.05), (0.0, -0.15), (0.3, -0.05), (0.45, 0.2), (0.45, 0.9)],
                           [(-0.6, -0.65), (0.2, -0.35)], [(0.2, -0.35), (0.35, -0.5), (0.5, -0.4)]],
    # Garage: open-fronted bay with an inbound chevron.
    "rover_bay": [[(-0.9, 0.85), (-0.9, -0.85), (0.9, -0.85), (0.9, 0.85)], [(-0.4, 0.75), (0.0, 0.35), (0.4, 0.75)],
                  [(-0.9, 0.3), (-0.55, 0.3)], [(0.9, 0.3), (0.55, 0.3)]],
    # Mines: shaft circle with crossed picks / a snowflake.
    "ilmenite_mine": [_poly(14, 0.95), [(-0.5, 0.5), (0.45, -0.45)], [(0.5, 0.5), (-0.45, -0.45)],
                      [(0.25, -0.62), (0.62, -0.25)], [(-0.25, -0.62), (-0.62, -0.25)]],
    "ice_mine": [_poly(14, 0.95), [(0.0, -0.6), (0.0, 0.6)], [(-0.52, -0.3), (0.52, 0.3)], [(-0.52, 0.3), (0.52, -0.3)]],
    # Anorthite: a shaft with a pale crystal; KREEP: a shaft with a trefoil.
    "anorthite_mine": [_poly(14, 0.95), [(0.0, -0.6), (0.4, 0.0), (0.0, 0.6), (-0.4, 0.0), (0.0, -0.6)],
                       [(-0.4, 0.0), (0.4, 0.0)]],
    "kreep_mine": [_poly(14, 0.95), _poly(6, 0.15), _poly(10, 0.22, 0.0, 0.0, -0.42),
                   _poly(10, 0.22, 0.0, 0.36, 0.21), _poly(10, 0.22, 0.0, -0.36, 0.21)],
    # Scrap furnace: a crucible with a pour spout.
    "scrap_furnace": [[(-0.7, -0.6), (-0.55, 0.7), (0.55, 0.7), (0.7, -0.6)], [(-0.85, -0.6), (0.85, -0.6)],
                      [(0.7, -0.6), (0.95, -0.85)], [(-0.3, 0.1), (0.3, 0.1)]],
    # Sorter: a hopper over three bins.
    "sorter": [[(-0.85, -0.85), (0.85, -0.85), (0.25, -0.1), (-0.25, -0.1), (-0.85, -0.85)],
               _box(-0.85, 0.25, -0.3, 0.85), _box(-0.27, 0.25, 0.27, 0.85), _box(0.3, 0.25, 0.85, 0.85),
               [(0.0, -0.1), (0.0, 0.25)]],
    # Tier II. Oven: a box with heat waves rising; aluminium cell: a tank with
    # electrodes and a slag spout; slag heap: a mound; fabrication line: a
    # conveyor with three presses; refinery: two stacked drums; frame works: a
    # truss; separator: a cyclone cone; electronics: a chip.
    "volatiles_oven": [_box(-0.85, -0.2, 0.85, 0.85), _wave(-0.6, -0.2, -0.55, 0.15, 4), _wave(0.0, 0.4, -0.55, 0.15, 4),
                       [(-0.6, 0.35), (0.6, 0.35)]],
    "aluminium_cell": [_box(-0.85, -0.6, 0.6, 0.85), [(-0.4, -0.85), (-0.4, 0.4)], [(0.15, -0.85), (0.15, 0.4)],
                       [(0.6, 0.5), (0.95, 0.85)]],
    "slag_heap": [[(-0.95, 0.6), (-0.5, -0.1), (-0.1, -0.55), (0.35, -0.2), (0.95, 0.6), (-0.95, 0.6)],
                  [(-0.3, 0.2), (0.2, 0.2)]],
    "fabrication_line": [_box(-0.95, 0.2, 0.95, 0.55), _box(-0.75, -0.6, -0.35, 0.2), _box(-0.2, -0.6, 0.2, 0.2),
                         _box(0.35, -0.6, 0.75, 0.2)],
    "titanium_refinery": [_poly(12, 0.55, 0.0, 0.0, -0.35), _poly(12, 0.55, 0.0, 0.0, 0.4), [(-0.55, -0.35), (-0.55, 0.4)],
                          [(0.55, -0.35), (0.55, 0.4)]],
    "frame_works": [_box(-0.9, -0.7, 0.9, 0.7), [(-0.9, 0.7), (-0.3, -0.7), (0.3, 0.7), (0.9, -0.7)]],
    "rare_earth_separator": [[(-0.8, -0.8), (0.8, -0.8), (0.15, 0.6), (-0.15, 0.6), (-0.8, -0.8)],
                             [(-0.5, -0.4), (0.5, -0.4)], [(0.0, 0.6), (0.0, 0.95)]],
    "electronics_plant": [_box(-0.55, -0.55, 0.55, 0.55)] + [[(-0.9, y), (-0.55, y)] for y in (-0.3, 0.0, 0.3)]
                         + [[(0.55, y), (0.9, y)] for y in (-0.3, 0.0, 0.3)] + [_box(-0.2, -0.2, 0.2, 0.2)],
    # Power ladder. Tower: a tall lattice mast; fuel cells: stacked plates with a
    # bolt; heliostat: a ring of mirrors round a tower; fuel fabricator: a box
    # with a rod; reactor: a dome inside a square with a trefoil hint;
    # radiator: a finned panel; cask store: a row of casks.
    "power_tower": [[(-0.5, 0.95), (0.0, -0.95), (0.5, 0.95)], [(-0.3, 0.2), (0.3, 0.2)], [(-0.9, -0.5), (0.9, -0.5)]],
    "fuel_cell_bank": [_box(-0.8, -0.8, 0.8, 0.8), [(-0.8, -0.3), (0.8, -0.3)], [(-0.8, 0.2), (0.8, 0.2)],
                       [(0.15, -0.65), (-0.15, -0.05), (0.15, -0.05), (-0.15, 0.6)]],
    "heliostat_tower": [_poly(16, 0.95), _poly(6, 0.2)] + [[(0.95 * math.cos(a), 0.95 * math.sin(a)),
                                                            (0.65 * math.cos(a), 0.65 * math.sin(a))]
                                                           for a in [k * math.pi / 4 for k in range(8)]],
    "fuel_fabricator": [_box(-0.85, -0.6, 0.85, 0.6), _box(-0.15, -0.95, 0.15, 0.6), [(-0.85, 0.0), (-0.15, 0.0)]],
    "fission_reactor": [_box(-0.9, -0.9, 0.9, 0.9), _poly(16, 0.6), _poly(8, 0.15),
                        [(0.0, -0.6), (0.0, -0.25)], [(0.52, 0.3), (0.22, 0.13)], [(-0.52, 0.3), (-0.22, 0.13)]],
    "radiator": [_box(-0.9, -0.5, 0.9, 0.5)] + [[(x, -0.5), (x, 0.5)] for x in (-0.6, -0.3, 0.0, 0.3, 0.6)],
    "cask_store": [_box(-0.9, -0.7, 0.9, 0.7), _poly(10, 0.25, 0.0, -0.45, 0.0), _poly(10, 0.25, 0.0, 0.2, 0.0),
                   _poly(10, 0.18, 0.0, 0.65, 0.2)],
    # Mass driver: a long launch rail with coil rings, on a base.
    "mass_driver": [_box(-0.95, -0.25, 0.95, 0.25), [(-0.95, 0.0), (0.95, 0.0)],
                    _poly(10, 0.2, 0.0, -0.45, 0.0), _poly(10, 0.2, 0.0, 0.0, 0.0), _poly(10, 0.2, 0.0, 0.45, 0.0),
                    [(0.95, -0.4), (0.95, 0.4)], [(-0.6, 0.25), (-0.75, 0.6)], [(0.6, 0.25), (0.75, 0.6)]],
    # Plants.
    "crusher": [_box(-0.85, -0.85, 0.85, 0.85), [(-0.7, 0.1), (-0.42, -0.25), (-0.14, 0.1), (0.14, -0.25), (0.42, 0.1), (0.7, -0.25)]],
    "ice_melter": [_poly(14, 0.95), _wave(-0.6, 0.6, -0.15, 0.15), _wave(-0.6, 0.6, 0.25, 0.15)],
    "sinter_kiln": [_box(-0.85, -0.85, 0.85, 0.85), [(-0.4, 0.45), (0.0, -0.45), (0.4, 0.45), (-0.4, 0.45)]],
    # Tier 2: a cell with two electrodes; a furnace with a flame; a shop with a gear.
    "electrolyzer": [_poly(6, 0.95), [(-0.35, -0.55), (-0.35, 0.55)], [(0.35, -0.55), (0.35, 0.55)],
                     [(-0.5, -0.55), (-0.2, -0.55)], [(0.2, -0.55), (0.5, -0.55)]],
    "reduction_furnace": [_box(-0.85, -0.85, 0.85, 0.85), _poly(12, 0.55),
                          [(-0.25, 0.25), (-0.1, -0.1), (0.0, 0.1), (0.12, -0.3), (0.25, 0.25)]],
    "machine_shop": [_box(-0.85, -0.85, 0.85, 0.85), _GEAR, _poly(8, 0.15)],
}

# Unit markers: one silhouette per type, drawn facing +x and rotated to the
# unit's heading. Blunt, boxy outlines with the "front" told by a feature
# (scoop, cab, boom, dish) rather than a point, so nothing reads as a ship.
UNITS = {
    # Squat body with a V-notched scoop at the front.
    "scavenger": [[(-0.75, -0.55), (0.35, -0.55), (0.8, -0.3), (0.45, 0.0), (0.8, 0.3), (0.35, 0.55),
                   (-0.75, 0.55), (-0.9, 0.0), (-0.75, -0.55)]],
    # Wide, low body with a broad blade across the front, wider than the body.
    "scraper": [_box(-0.85, -0.5, 0.45, 0.5), [(0.75, -0.85), (0.75, 0.85)], [(0.45, -0.3), (0.75, -0.3)],
                [(0.45, 0.3), (0.75, 0.3)], [(-0.5, -0.5), (-0.5, 0.5)]],
    # Long trailer box and a narrower cab ahead of it.
    "hauler": [_box(-1.0, -0.5, 0.35, 0.5), [(0.35, -0.35), (0.85, -0.3), (0.95, 0.0), (0.85, 0.3), (0.35, 0.35)],
               [(-0.35, -0.5), (-0.35, 0.5)]],
    # Square chassis with a crane boom reaching forward.
    "constructor": [_box(-0.7, -0.6, 0.4, 0.6), [(-0.2, 0.0), (1.0, 0.0)], [(0.85, -0.2), (1.0, 0.0), (0.85, 0.2)]],
    # Rounded body with a sensor dish ring towards the front.
    # A quad-rotor: a cross frame with four rotor rings; the front pair is closer together.
    "maintenance_drone": [[(-0.7, -0.7), (0.7, 0.7)], [(-0.7, 0.7), (0.7, -0.7)],
                          _poly(6, 0.3, 0.0, 0.7, 0.7), _poly(6, 0.3, 0.0, 0.7, -0.7),
                          _poly(6, 0.3, 0.0, -0.7, 0.7), _poly(6, 0.3, 0.0, -0.7, -0.7),
                          [(0.15, 0.0), (0.45, 0.0)]],
    # A hexa-rotor: six rotor rings round a hub with a hook below.
    "construction_drone": [_poly(6, 0.32, 0.0, 0.0, 0.0)] + [
        _poly(6, 0.22, 0.0, 0.78 * _c, 0.78 * _s) for _c, _s in
        ((1.0, 0.0), (0.5, 0.866), (-0.5, 0.866), (-1.0, 0.0), (-0.5, -0.866), (0.5, -0.866))]
        + [[(0.32, 0.0), (0.56, 0.0)]],
    "survey_rover": [[(-0.85, -0.35), (-0.5, -0.6), (0.4, -0.6), (0.65, -0.3), (0.65, 0.3), (0.4, 0.6),
                      (-0.5, 0.6), (-0.85, 0.35), (-0.85, -0.35)], _poly(8, 0.28, 0.0, 0.15, 0.0)],
}
