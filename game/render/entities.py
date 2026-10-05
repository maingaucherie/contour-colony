"""Fields, power links, debris, structures, trails, rovers, selection and the
placement ghost, drawn as vector glyphs over the terrain."""

import math

import pygame

from game.content import display as D
from game.render import glyphs as G
from game.render import symbols as SYM
from game.render.hershey import draw_text
from game.content import contracts as CT
from game.sim import production as P
from game.sim import units as US

_facing = {}  # unit id -> +1 / -1, with a deadband so rovers don't flip-flop
style = D.ICON_STYLES[0]  # set by the app


def interp(unit, alpha):
    return unit.prev_vx + (unit.vx - unit.prev_vx) * alpha, unit.prev_vy + (unit.vy - unit.prev_vy) * alpha


def _scale(color, k):
    return tuple(max(0, min(255, int(c * k))) for c in color)


def _on_screen(sx, sy, margin, w, h):
    return -margin <= sx <= w + margin and -margin <= sy <= h + margin


def structure_half_px(spec, zoom, is_lander):
    """Half-size of a structure icon on screen. Symbols follow the footprint
    (they scale with zoom); pictorial glyphs keep a readable minimum."""
    if style == "symbols":
        return max(spec["footprint_cells"] * D.SYMBOL_STRUCTURE_SCALE * zoom, D.SYMBOL_STRUCTURE_MIN_PX)
    return max(spec["footprint_cells"] * D.STRUCTURE_SCALE * zoom, D.LANDER_MIN_PX if is_lander else D.STRUCTURE_MIN_PX)


def structure_shape(kind):
    return SYM.STRUCTURES[kind] if style == "symbols" else G.STRUCTURE_SHAPES[kind]


def unit_half_px(zoom):
    if style == "symbols":
        lo, hi = D.UNIT_SYMBOL_PX
        return min(max(D.UNIT_SYMBOL_CELLS * zoom, lo), hi)
    return max(D.ROVER_SIZE_CELLS * zoom, D.ROVER_MIN_PX)


def _draw_unit_symbol(surface, color, unit, sx, sy, half, carrying):
    spec = SYM.UNITS[unit.kind]
    pygame.draw.aalines(surface, color, False, [(sx + x * half, sy + y * half) for x, y in spec["outline"]])
    r0, r1 = spec["tick"]
    c, s = math.cos(unit.vis_heading), math.sin(unit.vis_heading)
    pygame.draw.aaline(surface, color, (sx + c * r0 * half, sy + s * r0 * half), (sx + c * r1 * half, sy + s * r1 * half))
    if carrying:
        pygame.draw.circle(surface, D.COLOR_FLOW, (int(sx), int(sy)), D.CARGO_DOT_PX)
    return len(spec["outline"])


def _flicker(now_s, key):
    lo, hi = D.UNPOWERED_FLICKER
    wave = (math.sin(now_s * 23.0 + key * 1.7) + math.sin(now_s * 41.0 + key)) / 4 + 0.5
    return lo + (hi - lo) * wave


def draw_fields(surface, world, camera, now_s):
    z = camera.zoom
    to_screen = camera.world_to_screen
    level_at = world.survey.level_at
    show_richness_at_1 = world.research.effect("richness_at_level_1", False)
    for f in world.fields:
        if not f.hinted:
            continue
        color = D.COLOR_FIELD_ICE if f.kind == "ice" else D.COLOR_FIELD
        # Revealed boundary: segments whose midpoint is surveyed to level 2.
        revealed = 0
        run = []
        for a, b in zip(f.boundary, f.boundary[1:]):
            if level_at((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) >= 2:
                if not run:
                    run.append(to_screen(*a))
                run.append(to_screen(*b))
                revealed += 1
            elif run:
                G.dashed(surface, color, run, D.FIELD_LONG_DASH_PX, D.FIELD_GAP_PX)
                run = []
        if run:
            G.dashed(surface, color, run, D.FIELD_LONG_DASH_PX, D.FIELD_GAP_PX)
        if revealed < len(f.boundary) - 1:
            # Still uncertain: a flickering dotted ring around roughly the right place.
            hx, hy = to_screen(f.cx + f.hint_dx, f.cy + f.hint_dy)
            if int(now_s * D.FIELD_HINT_FLICKER_HZ * 2 + f.id) % 3:
                G.dotted_circle(surface, _scale(color, 0.7), hx, hy, f.radius * 1.3 * z, D.DOT_SPACING_PX,
                                phase=now_s * 0.3)
            if not f.confirmed:
                draw_text(surface, f"{f.kind.upper()} SIGNAL?", (hx, hy - 6), 1, _scale(color, 0.8), "center",
                          additive=True)
        if f.confirmed or show_richness_at_1:
            sx, sy = to_screen(f.cx, f.cy)
            label = f"{f.kind.upper()} {f.richness:.1f}X" if (f.confirmed or show_richness_at_1) else f.kind.upper()
            draw_text(surface, label, (sx, sy - 6), 1, color, "center", additive=True)


def draw_grid_links(surface, world, camera):
    to_screen = camera.world_to_screen
    for s in world.structures.values():
        if s.built and s.grid_parent is not None and s.grid_parent in world.structures:
            p = world.structures[s.grid_parent]
            G.dotted(surface, D.COLOR_GRID_LINK, to_screen(s.x, s.y), to_screen(p.x, p.y), D.DOT_SPACING_PX)


def _draw_structure(surface, world, s, camera, now_s, selected):
    w, h = surface.get_size()
    sx, sy = camera.world_to_screen(s.x, s.y)
    half = structure_half_px(s.spec, camera.zoom, s.kind == "lander")
    if not _on_screen(sx, sy, half * 2, w, h):
        return 0
    shape = structure_shape(s.kind)
    if not s.built:
        G.dotted_circle(surface, D.COLOR_SITE, sx, sy, s.spec["footprint_cells"] * camera.zoom, D.DOT_SPACING_PX)
        return G.draw_shape(surface, D.COLOR_SITE, shape, sx, sy, half, s.build_progress())
    color = D.COLOR_STRUCTURE
    if s.status in (P.STARVED, P.BLOCKED) and P.recipe(s):
        color = _scale(D.COLOR_STARVED, 0.6 + 0.4 * (int(now_s * 2) % 2))
    if not s.powered:
        color = _scale(color, _flicker(now_s, s.id))
    if s.deconstruct:
        color = _scale(D.COLOR_ALERT, 0.5 + 0.5 * (int(now_s * 2) % 2))
        segs = G.draw_shape(surface, color, shape, sx, sy, half, 1.0 - min(1.0, s.teardown_progress()))
    else:
        segs = G.draw_shape(surface, color, shape, sx, sy, half)
    r = P.recipe(s)
    if r and half >= D.GAUGE_MIN_HALF_PX:
        segs += _draw_gauges(surface, s, r, sx, sy, half)
    if s.kind == "lander" and int(now_s * D.BEACON_BLINK_HZ * 2) % 2 == 0:
        bx, by = G.LANDER_BEACON if style == "pictorial" else (0.0, 0.0)
        pygame.draw.circle(surface, D.COLOR_SELECT, (int(sx + bx * half), int(sy + by * half)), 1)
    return segs


def _draw_gauges(surface, s, r, sx, sy, half):
    """Thin vertical buffer gauges: inputs on the left, outputs on the right."""
    h = int(half * 1.6)
    top = int(sy - h / 2)
    gw, gap = D.GAUGE_WIDTH_PX, D.GAUGE_GAP_PX
    n = 0
    for side, items, held, cap in ((-1, list(r["in"]), s.inputs, lambda k: P.input_cap(s, k)),
                                   (1, list(r["out"]), s.outputs, lambda k: P.output_cap(s, k))):
        for i, k in enumerate(items):
            x = int(sx + side * (half + gap + 1 + i * (gw + gap + 1))) - (gw if side < 0 else 0)
            frac = held.get(k, 0) / max(1, cap(k))
            pygame.draw.rect(surface, D.COLOR_FRAME, (x - 1, top - 1, gw + 2, h + 2), 1)
            fill = int(h * min(1.0, frac))
            if fill:
                pygame.draw.rect(surface, D.COLOR_FLOW, (x, top + h - fill, gw, fill))
            n += 1
    return n


def draw_pods(surface, world, camera):
    """Supply pods on their way down: a marker sliding to its landing ring."""
    now = world.time_s()
    n = 0
    for pod in world.orbit.falling:
        k = max(0.0, min(1.0, (pod.land_s - now) / CT.DROP_FALL_S))
        gx, gy = camera.world_to_screen(pod.x, pod.y)
        px, py = gx, gy - k * D.POD_FALL_PX
        G.dotted_circle(surface, D.COLOR_POWER, gx, gy, D.POD_SIZE_PX + 6 * k, D.DOT_SPACING_PX)
        G.dotted(surface, D.COLOR_POWER, (px, py), (gx, gy), D.DOT_SPACING_PX)
        r = D.POD_SIZE_PX
        pygame.draw.aalines(surface, D.COLOR_POWER, True, [(px, py - r), (px + r, py), (px, py + r), (px - r, py)])
        n += 5
    return n


def _draw_scan_beam(surface, s, camera):
    """Radar sweep: a faint beam with a short fading trail."""
    sx, sy = camera.world_to_screen(s.x, s.y)
    r = s.spec["scan_radius_cells"] * camera.zoom
    n = D.SCAN_BEAM_TRAIL
    for i in range(n):
        a = s.sweep_angle - i * D.SCAN_BEAM_TRAIL_STEP
        k = (1 - i / n) ** 2
        pygame.draw.aaline(surface, _scale(D.COLOR_SCAN, k), (sx, sy), (sx + r * math.cos(a), sy + r * math.sin(a)))
    return n


def _rover_facing(unit):
    c = math.cos(unit.vis_heading)
    f = _facing.get(unit.id, 1 if c >= 0 else -1)
    if c > D.ROVER_FACING_DEADBAND:
        f = 1
    elif c < -D.ROVER_FACING_DEADBAND:
        f = -1
    _facing[unit.id] = f
    return f


def draw_world(surface, world, camera, alpha, now_s, selected, ghost=None):
    """Draw everything above the terrain. Returns the number of line segments drawn."""
    w, h = surface.get_size()
    z = camera.zoom
    to_screen = camera.world_to_screen
    segments = 0

    draw_fields(surface, world, camera, now_s)
    draw_grid_links(surface, world, camera)

    size = max(D.DEBRIS_SIZE_CELLS * z, D.DEBRIS_MIN_PX) / 2
    for piece in world.debris.values():
        if not piece.seen:
            continue
        sx, sy = to_screen(piece.x, piece.y)
        if _on_screen(sx, sy, size, w, h):
            segments += G.draw_shape(surface, D.COLOR_DEBRIS, G.DEBRIS_SHAPES[piece.kind], sx, sy, size)

    for s in world.structures.values():
        if s.kind == "scanner" and s.built and s.powered:
            segments += _draw_scan_beam(surface, s, camera)
        segments += _draw_structure(surface, world, s, camera, now_s, selected)

    segments += draw_pods(surface, world, camera)

    # Phosphor trails (world space, so they survive panning and zooming).
    for unit in world.units.values():
        rx, ry = interp(unit, alpha)
        points = list(unit.trail)
        n = len(points)
        prev = None
        for i, (x, y) in enumerate(points + [(rx, ry)]):
            p = to_screen(x, y)
            if prev is not None and (p[0] != prev[0] or p[1] != prev[1]):
                k = i / n if n else 1.0
                color = tuple(int(o + (f - o) * k) for o, f in zip(D.TRAIL_COLOR_OLD, D.TRAIL_COLOR_FRESH))
                pygame.draw.aaline(surface, _scale(color, k), prev, p)
                segments += 1
            prev = p

    rover_half = unit_half_px(z)
    for unit in world.units.values():
        rx, ry = interp(unit, alpha)
        sx, sy = to_screen(rx, ry)
        if not _on_screen(sx, sy, rover_half * 2, w, h):
            continue
        frac = unit.battery / US.capacity(world, unit)
        color = D.COLOR_UNIT
        visible = True
        if unit.state == US.STRANDED:
            color = D.COLOR_ALERT
            visible = int(now_s * 2 * D.IDLE_BLINK_HZ) % 2 == 0
        elif unit.state == US.WORKING and unit.activity == "pickup":
            visible = int(now_s * 2 * D.PICKUP_BLINK_HZ) % 2 == 0
        elif unit.state == US.IDLE:
            color = _scale(color, 0.55 + 0.45 * (int(now_s * 2 * D.IDLE_BLINK_HZ) % 2))
        elif frac < D.LOW_BATTERY_FLICKER_BELOW:
            wave = (math.sin(now_s * D.LOW_BATTERY_FLICKER_RATE + unit.id) + 1) / 2
            color = _scale(color, D.LOW_BATTERY_FLICKER_MIN + (1 - D.LOW_BATTERY_FLICKER_MIN) * wave)
        if unit.state == US.CHARGING and unit.dock in world.structures:
            dock = world.structures[unit.dock]
            G.dotted(surface, D.COLOR_POWER, (sx, sy), to_screen(dock.x, dock.y), D.DOT_SPACING_PX)
        if unit.kind == "survey_rover" and unit.state == US.WORKING:
            r = unit.spec["linger_radius_cells"] * z
            G.dotted_circle(surface, D.COLOR_FIELD, sx, sy, r * (0.4 + 0.6 * ((now_s * 0.8) % 1.0)), D.DOT_SPACING_PX)
        if visible and style == "symbols":
            segments += _draw_unit_symbol(surface, color, unit, sx, sy, rover_half, unit.cargo_total() > 0)
        elif visible:
            moving = unit.state == US.MOVING
            bob = D.ROVER_BOB * math.sin(2 * math.pi * unit.odometer / D.ROVER_BOB_WAVELENGTH_CELLS) if moving else 0.0
            segments += G.draw_rover(surface, color, unit.kind, sx, sy - rover_half * 0.25, rover_half,
                                     _rover_facing(unit), unit.odometer, bob,
                                     D.COLOR_FLOW, unit.cargo_total() > 0)

    if selected is not None:
        kind, eid = selected
        if kind == "unit" and eid in world.units:
            unit = world.units[eid]
            sx, sy = to_screen(*interp(unit, alpha))
            if unit.path:
                G.dashed(surface, D.COLOR_FLOW, [(sx, sy)] + [to_screen(x, y) for x, y in unit.path], D.DASH_PX, D.GAP_PX)
            _brackets(surface, sx, sy, rover_half * (1.9 if style == "symbols" else 1.4))
        elif kind == "structure" and eid in world.structures:
            s = world.structures[eid]
            sx, sy = to_screen(s.x, s.y)
            _brackets(surface, sx, sy, structure_half_px(s.spec, z, s.kind == "lander") * 1.15)
            reach = s.spec.get("grid_reach_cells", 0)
            if reach and s.built:
                G.dotted_circle(surface, D.COLOR_GRID_LINK, sx, sy, reach * z, D.DOT_SPACING_PX * 2)

    if ghost is not None:
        segments += draw_ghost(surface, world, camera, ghost)
    return segments


def draw_ghost(surface, world, camera, ghost):
    """Placement preview: the structure where it would go, its grid reach, and why not."""
    kind, x, y, ok, reason, spec = ghost
    z = camera.zoom
    sx, sy = camera.world_to_screen(x, y)
    color = D.COLOR_GHOST_OK if ok else D.COLOR_ALERT
    half = structure_half_px(spec, z, False)
    segs = G.draw_shape(surface, _scale(color, 0.8), structure_shape(kind), sx, sy, half)
    G.dotted_circle(surface, color, sx, sy, spec["footprint_cells"] * z, D.DOT_SPACING_PX)
    reach = spec.get("grid_reach_cells", 0)
    if reach:
        G.dotted_circle(surface, D.COLOR_GRID_LINK, sx, sy, reach * z, D.DOT_SPACING_PX * 2)
    # Where it would draw power from.
    best = None
    for s in world.structures.values():
        r = max(s.spec.get("grid_reach_cells", 0), reach) if s.built else 0
        d = math.hypot(s.x - x, s.y - y)
        if r and d <= r and s.spec.get("grid_reach_cells", 0) and (best is None or d < best[0]):
            best = (d, s)
    if best:
        G.dotted(surface, D.COLOR_POWER, (sx, sy), camera.world_to_screen(best[1].x, best[1].y), D.DOT_SPACING_PX)
    note = reason if not ok else ("ON GRID" if best else "NO POWER HERE")
    if ok and kind == "solar":
        note = f"+{spec['power_kw'] * world.illumination_at(x, y):.1f} KW  " + note
    draw_text(surface, f"{spec['name'].upper()}  {note}", (sx, sy + half + 6), 1,
              color if not ok else D.COLOR_TEXT, "center")
    return segs


def _brackets(surface, sx, sy, r):
    n = max(3, r * 0.4)
    for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        x, y = sx + dx * r, sy + dy * r
        pygame.draw.lines(surface, D.COLOR_SELECT, False, [(x - dx * n, y), (x, y), (x, y - dy * n)])


def pick(world, camera, alpha, pos):
    """Entity under a screen position: ('unit', id), ('structure', id) or None."""
    mx, my = pos
    best, best_d = None, D.SELECT_PICK_RADIUS_PX
    rover_half = unit_half_px(camera.zoom)
    lift = rover_half * 0.25 if style == "pictorial" else 0.0
    for unit in world.units.values():
        sx, sy = camera.world_to_screen(*interp(unit, alpha))
        d = math.hypot(sx - mx, sy - lift - my)
        if d <= max(best_d, rover_half) and (best is None or d < best_d):
            best, best_d = ("unit", unit.id), d
    if best is not None:
        return best
    for s in world.structures.values():
        sx, sy = camera.world_to_screen(s.x, s.y)
        r = max(structure_half_px(s.spec, camera.zoom, s.kind == "lander"), D.SELECT_PICK_RADIUS_PX)
        if math.hypot(sx - mx, sy - my) <= r:
            return ("structure", s.id)
    return None
