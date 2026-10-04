"""Structures, units, debris, trails and selection, drawn as vector glyphs."""

import math

import pygame

from game.content import display as D
from game.sim import units as US

# Glyph shapes in unit coordinates (roughly -1..1, y down). Each is a list of
# polylines; a polyline whose first and last points match is closed.
_LANDER = [
    # body: oblique hexagonal prism
    [(-0.6, 0.0), (-0.3, -0.25), (0.3, -0.25), (0.6, 0.0), (0.3, 0.25), (-0.3, 0.25), (-0.6, 0.0)],
    [(-0.6, -0.5), (-0.3, -0.75), (0.3, -0.75), (0.6, -0.5), (0.3, -0.25), (-0.3, -0.25), (-0.6, -0.5)],
    [(-0.6, 0.0), (-0.6, -0.5)], [(0.6, 0.0), (0.6, -0.5)],
    [(0.3, -0.75), (0.3, -0.95)], [(0.15, -1.0), (0.45, -0.9)],          # antenna
    # legs and pads
    [(-0.6, 0.0), (-1.0, 0.55)], [(0.6, 0.0), (1.0, 0.55)],
    [(-0.3, 0.25), (-0.45, 0.8)], [(0.3, 0.25), (0.45, 0.8)],
    [(-1.15, 0.55), (-0.85, 0.55)], [(0.85, 0.55), (1.15, 0.55)],
    [(-0.6, 0.8), (-0.3, 0.8)], [(0.3, 0.8), (0.6, 0.8)],
]
_DEBRIS = {
    "rock": [[(-0.9, 0.3), (-0.5, -0.6), (0.3, -0.8), (0.9, -0.1), (0.5, 0.7), (-0.4, 0.8), (-0.9, 0.3)]],
    "panel": [[(-0.9, -0.5), (0.9, -0.5), (0.9, 0.5), (-0.9, 0.5), (-0.9, -0.5)], [(0.0, -0.5), (0.0, 0.5)]],
    "fragment": [[(-0.8, 0.7), (0.0, -0.9), (0.6, 0.6), (-0.8, 0.7)], [(0.6, 0.6), (0.95, 0.95)]],
}
_CHEVRON = [(1.0, 0.0), (-0.7, 0.65), (-0.3, 0.0), (-0.7, -0.65), (1.0, 0.0)]


def _size_px(cells, zoom, min_px):
    return max(cells * zoom, min_px)


def _draw_shape(surface, color, shape, cx, cy, scale):
    for line in shape:
        pts = [(cx + x * scale, cy + y * scale) for x, y in line]
        pygame.draw.aalines(surface, color, False, pts)


def _on_screen(sx, sy, margin, w, h):
    return -margin <= sx <= w + margin and -margin <= sy <= h + margin


def _scale_color(color, k):
    return tuple(int(c * k) for c in color)


def _dashed(surface, color, points):
    """Dashed polyline (cyan routes use this line style as their colourblind backup)."""
    on, left = True, D.DASH_PX
    for (ax, ay), (bx, by) in zip(points, points[1:]):
        length = math.hypot(bx - ax, by - ay)
        pos = 0.0
        while pos < length:
            step = min(left, length - pos)
            if on:
                f0, f1 = pos / length, (pos + step) / length
                pygame.draw.aaline(surface, color, (ax + (bx - ax) * f0, ay + (by - ay) * f0),
                                   (ax + (bx - ax) * f1, ay + (by - ay) * f1))
            pos += step
            left -= step
            if left <= 0:
                on = not on
                left = D.DASH_PX if on else D.GAP_PX


def _dotted(surface, color, a, b):
    """Dotted line (amber power links use this as their colourblind backup)."""
    (ax, ay), (bx, by) = a, b
    n = max(1, int(math.hypot(bx - ax, by - ay) / D.DOT_SPACING_PX))
    for i in range(n + 1):
        t = i / n
        surface.set_at((int(ax + (bx - ax) * t), int(ay + (by - ay) * t)), color)


def interp(unit, alpha):
    return unit.prev_x + (unit.x - unit.prev_x) * alpha, unit.prev_y + (unit.y - unit.prev_y) * alpha


def draw_world(surface, world, camera, alpha, now_s, selected):
    """Draw everything above the terrain. Returns the number of line segments drawn."""
    w, h = surface.get_size()
    z = camera.zoom
    to_screen = camera.world_to_screen
    segments = 0

    # Debris.
    size = _size_px(D.DEBRIS_SIZE_CELLS, z, D.DEBRIS_MIN_PX) / 2
    for piece in world.debris.values():
        sx, sy = to_screen(piece.x, piece.y)
        if _on_screen(sx, sy, size, w, h):
            shape = _DEBRIS[piece.kind]
            _draw_shape(surface, D.COLOR_DEBRIS, shape, sx, sy, size)
            segments += sum(len(line) - 1 for line in shape)

    # Structures.
    for s in world.structures.values():
        sx, sy = to_screen(s.x, s.y)
        half = _size_px(D.LANDER_SIZE_CELLS, z, D.LANDER_MIN_PX) / 2
        if _on_screen(sx, sy, half * 2, w, h):
            _draw_shape(surface, D.COLOR_STRUCTURE, _LANDER, sx, sy, half)
            segments += sum(len(line) - 1 for line in _LANDER)

    # Trails, then units on top.
    unit_half = _size_px(D.UNIT_SIZE_CELLS, z, D.UNIT_MIN_PX) / 2
    for unit in world.units.values():
        rx, ry = interp(unit, alpha)
        points = list(unit.trail)
        n = len(points)
        prev = None
        for i, (x, y) in enumerate(points + [(rx, ry)]):
            p = to_screen(x, y)
            if prev is not None and (p[0] != prev[0] or p[1] != prev[1]):
                k = i / n if n else 1.0  # 0 = oldest, 1 = newest
                color = tuple(int(o + (f - o) * k) for o, f in zip(D.TRAIL_COLOR_OLD, D.TRAIL_COLOR_FRESH))
                pygame.draw.aaline(surface, _scale_color(color, k), prev, p)
                segments += 1
            prev = p

    for unit in world.units.values():
        rx, ry = interp(unit, alpha)
        sx, sy = to_screen(rx, ry)
        if not _on_screen(sx, sy, unit_half * 2, w, h):
            continue
        frac = unit.battery / unit.spec["battery"]
        color = D.COLOR_UNIT
        visible = True
        if unit.state == US.STRANDED:
            color = D.COLOR_ALERT
            visible = int(now_s * 2 * D.IDLE_BLINK_HZ) % 2 == 0
        elif unit.state == US.PICKUP:
            visible = int(now_s * 2 * D.PICKUP_BLINK_HZ) % 2 == 0
        elif unit.state == US.IDLE:
            visible = int(now_s * 2 * D.IDLE_BLINK_HZ) % 2 == 0
        elif frac < D.LOW_BATTERY_FLICKER_BELOW:
            wave = (math.sin(now_s * D.LOW_BATTERY_FLICKER_RATE + unit.id) + 1) / 2
            k = D.LOW_BATTERY_FLICKER_MIN + (1 - D.LOW_BATTERY_FLICKER_MIN) * wave
            color = _scale_color(color, k)
        if unit.state == US.CHARGING and unit.dock is not None:
            dock = world.structures[unit.dock]
            _dotted(surface, D.COLOR_POWER, (sx, sy), to_screen(dock.x, dock.y))
        if visible:
            c, s_ = math.cos(unit.heading), math.sin(unit.heading)
            pts = [(sx + (x * c - y * s_) * unit_half, sy + (x * s_ + y * c) * unit_half) for x, y in _CHEVRON]
            pygame.draw.aalines(surface, color, False, pts)
            segments += len(pts) - 1
            for i in range(unit.cargo):
                px = sx - c * unit_half * (1.2 + 0.6 * i)
                py = sy - s_ * unit_half * (1.2 + 0.6 * i)
                pygame.draw.rect(surface, D.COLOR_FLOW, (px - D.CARGO_PIP_PX // 2, py - D.CARGO_PIP_PX // 2,
                                                         D.CARGO_PIP_PX, D.CARGO_PIP_PX))

    # Selection: brackets around the entity, and the selected unit's route.
    if selected is not None:
        kind, eid = selected
        if kind == "unit" and eid in world.units:
            unit = world.units[eid]
            rx, ry = interp(unit, alpha)
            sx, sy = to_screen(rx, ry)
            if unit.path:
                _dashed(surface, D.COLOR_FLOW, [(sx, sy)] + [to_screen(x, y) for x, y in unit.path])
            _brackets(surface, sx, sy, unit_half * 1.8)
        elif kind == "structure" and eid in world.structures:
            s = world.structures[eid]
            sx, sy = to_screen(s.x, s.y)
            _brackets(surface, sx, sy, _size_px(D.LANDER_SIZE_CELLS, z, D.LANDER_MIN_PX) * 0.75)
    return segments


def _brackets(surface, sx, sy, r):
    n = max(3, r * 0.4)
    for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        x, y = sx + dx * r, sy + dy * r
        pygame.draw.lines(surface, D.COLOR_SELECT, False, [(x - dx * n, y), (x, y), (x, y - dy * n)])


def pick(world, camera, alpha, pos):
    """Entity under a screen position: ('unit', id), ('structure', id) or None."""
    mx, my = pos
    best, best_d = None, D.SELECT_PICK_RADIUS_PX
    for unit in world.units.values():
        sx, sy = camera.world_to_screen(*interp(unit, alpha))
        d = math.hypot(sx - mx, sy - my)
        if d <= best_d:
            best, best_d = ("unit", unit.id), d
    if best is not None:
        return best
    for s in world.structures.values():
        sx, sy = camera.world_to_screen(s.x, s.y)
        r = max(_size_px(D.LANDER_SIZE_CELLS, camera.zoom, D.LANDER_MIN_PX) / 2, D.SELECT_PICK_RADIUS_PX)
        if math.hypot(sx - mx, sy - my) <= r:
            return ("structure", s.id)
    return None
