"""Fields, power links, debris, structures, trails, rovers, selection and the
placement ghost, drawn as vector glyphs over the terrain."""

import math

import pygame

from game.content import display as D
from game.render import glyphs as G
from game.render import symbols as SYM
from game.render.hershey import draw_text
from game.content import contracts as CT
from game.content import structures as S
from game.content import units as U
from game.sim import conveyors as CONV
from game.sim import feeds as FEEDS
from game.sim import roads as ROADS
from game.sim import production as P
from game.sim import structures as ST
from game.sim import units as US

_facing = {}  # unit id -> +1 / -1, with a deadband so rovers don't flip-flop
style = D.ICON_STYLES[0]  # set by the app
lander_lift = 0.0         # pixels above its spot, while it lands in the intro (set by the app)


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
    """The unit's silhouette, rotated to where it's heading."""
    c, s = math.cos(unit.vis_heading) * half, math.sin(unit.vis_heading) * half
    n = 0
    for line in SYM.UNITS[unit.kind]:
        pygame.draw.aalines(surface, color, False, [(sx + x * c - y * s, sy + x * s + y * c) for x, y in line])
        n += len(line) - 1
    if carrying:
        bx, by = -0.3, 0.0  # cargo shown in the middle of the body
        pygame.draw.circle(surface, D.COLOR_FLOW, (int(sx + bx * c), int(sy + bx * s)), D.CARGO_DOT_PX)
    return n


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
            if f.survey_done or level_at((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) >= 2:
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
            label = f"{f.kind.upper()} {f.richness:.1f}X"
            if f.mined:
                label += f"  {f.reserves_left() * 100:.0f}% LEFT"
            draw_text(surface, label, (sx, sy - 6), 1, color, "center", additive=True)


_tracks_cache = {"key": None, "items": []}


def draw_tracks(surface, world, camera):
    """Worn tracks: short tread marks along the usual direction of travel."""
    t = world.tracks
    key = (id(t), t.version, world.tick_count // D.TRACK_REFRESH_TICKS)
    if _tracks_cache["key"] != key:
        _tracks_cache["key"], _tracks_cache["items"] = key, t.visible()
    w, h = surface.get_size()
    z = camera.zoom
    half = t.res * z * 0.55
    twin = z >= D.TRACK_TWIN_ZOOM
    gap = D.TRACK_TWIN_GAP_CELLS * z
    n = 0
    for x, y, a, k in _tracks_cache["items"]:
        sx, sy = camera.world_to_screen(x, y)
        if not _on_screen(sx, sy, half, w, h):
            continue
        color = _scale(D.COLOR_TRACK, D.TRACK_MIN_BRIGHTNESS + (1 - D.TRACK_MIN_BRIGHTNESS) * k)
        dx, dy = math.cos(a) * half, math.sin(a) * half
        if twin:
            ox, oy = -math.sin(a) * gap, math.cos(a) * gap
            pygame.draw.line(surface, color, (sx - dx + ox, sy - dy + oy), (sx + dx + ox, sy + dy + oy))
            pygame.draw.line(surface, color, (sx - dx - ox, sy - dy - oy), (sx + dx - ox, sy + dy - oy))
            n += 2
        else:
            pygame.draw.line(surface, color, (sx - dx, sy - dy), (sx + dx, sy + dy))
            n += 1
    return n


def draw_feed_links(surface, world, camera, now_s):
    """Direct feeds: a short cyan link between touching buildings, with a dot
    running along it in the direction the items go."""
    n = 0
    for a, b, item in world.feed_links():
        ax, ay = camera.world_to_screen(a.x, a.y)
        bx, by = camera.world_to_screen(b.x, b.y)
        d = math.hypot(bx - ax, by - ay) or 1.0
        ra = structure_half_px(a.spec, camera.zoom, False) * 0.8
        rb = structure_half_px(b.spec, camera.zoom, False) * 0.8
        if d <= ra + rb:
            continue
        ux, uy = (bx - ax) / d, (by - ay) / d
        p0, p1 = (ax + ux * ra, ay + uy * ra), (bx - ux * rb, by - uy * rb)
        pygame.draw.aaline(surface, _scale(D.COLOR_FLOW, 0.6), p0, p1)
        k = (now_s * D.FEED_DOT_SPEED) % 1.0
        pygame.draw.circle(surface, D.COLOR_FLOW, (int(p0[0] + (p1[0] - p0[0]) * k), int(p0[1] + (p1[1] - p0[1]) * k)), 1)
        n += 2
    return n


def draw_grid_links(surface, world, camera):
    to_screen = camera.world_to_screen
    for s in world.structures.values():
        if s.built and s.grid_parent is not None and s.grid_parent in world.structures and not s.is_line():
            p = world.structures[s.grid_parent]
            G.dotted(surface, D.COLOR_GRID_LINK, to_screen(s.x, s.y), to_screen(p.x, p.y), D.DOT_SPACING_PX)


def _draw_structure(surface, world, s, camera, now_s, selected):
    w, h = surface.get_size()
    sx, sy = camera.world_to_screen(s.x, s.y)
    if s is world.lander:
        sy -= lander_lift
    half = structure_half_px(s.spec, camera.zoom, s.kind == "lander")
    if not _on_screen(sx, sy, half * 2, w, h):
        return 0
    shape = structure_shape(s.kind)
    if not s.built:
        G.dotted_circle(surface, D.COLOR_SITE, sx, sy, s.spec["footprint_cells"] * camera.zoom, D.DOT_SPACING_PX)
        return G.draw_shape(surface, D.COLOR_SITE, shape, sx, sy, half, s.build_progress())
    color = D.COLOR_STRUCTURE
    if s.status in (P.STARVED, P.BLOCKED, P.BROKEN) and P.recipe(s):
        color = _scale(D.COLOR_STARVED, 0.6 + 0.4 * (int(now_s * 2) % 2))
    if not s.powered:
        color = _scale(color, _flicker(now_s, s.id))
    if s.deconstruct:
        color = _scale(D.COLOR_ALERT, 0.5 + 0.5 * (int(now_s * 2) % 2))
        segs = G.draw_shape(surface, color, shape, sx, sy, half, 1.0 - min(1.0, s.teardown_progress()))
    else:
        segs = G.draw_shape(surface, color, shape, sx, sy, half)
        if s.wear > D.WEAR_SHOW_FROM:
            # Worn: a faint, shaky second image, like a tired CRT trace.
            k = (s.wear - D.WEAR_SHOW_FROM) / (1.0 - D.WEAR_SHOW_FROM)
            off = D.WEAR_JITTER_PX * k * math.sin(now_s * 9.0 + s.id)
            segs += G.draw_shape(surface, _scale(color, 0.35 + 0.3 * k), shape, sx + off, sy - off * 0.6, half)
    r = P.recipe(s)
    if r and half >= D.GAUGE_MIN_HALF_PX:
        segs += _draw_gauges(surface, s, r, sx, sy, half)
    if s.kind == "lander" and int(now_s * D.BEACON_BLINK_HZ * 2) % 2 == 0:
        bx, by = G.LANDER_BEACON if style == "pictorial" else (0.0, 0.0)
        pygame.draw.circle(surface, D.COLOR_SELECT, (int(sx + bx * half), int(sy + by * half)), 1)
    return segs


def _rails(camera, p0, p1, width_cells=D.CONVEYOR_WIDTH_CELLS):
    """Screen points of two parallel rails from world p0 to p1, width_cells
    apart (or a few pixels at least), and the length between the ends."""
    a, b = camera.world_to_screen(*p0), camera.world_to_screen(*p1)
    d = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
    ux, uy = (b[0] - a[0]) / d, (b[1] - a[1]) / d
    half = max(width_cells * camera.zoom, D.CONVEYOR_WIDTH_MIN_PX) / 2
    nx, ny = -uy * half, ux * half
    left = ((a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny))
    right = ((a[0] - nx, a[1] - ny), (b[0] - nx, b[1] - ny))
    return a, b, d, left, right


def draw_road(surface, world, s, camera, now_s, selected=None):
    """A graded road: its two edges, faint; a site is dotted, solid as far as it is graded."""
    p0, p1 = ST.line_of(world, s)
    a, b, d, left, right = _rails(camera, p0, p1, S.ROAD_WIDTH_CELLS)
    w, h = surface.get_size()
    if max(a[0], b[0]) < 0 or min(a[0], b[0]) > w or max(a[1], b[1]) < 0 or min(a[1], b[1]) > h:
        return 0
    color = D.COLOR_SELECT if selected == ("structure", s.id) else D.COLOR_ROAD
    if s.deconstruct:
        color = _scale(D.COLOR_ALERT, 0.5 + 0.5 * (int(now_s * 2) % 2))
    if not s.built:
        k = s.build_progress()
        for p, q in (left, right):
            G.dotted(surface, color, p, q, D.DOT_SPACING_PX)
            pygame.draw.aaline(surface, color, p, (p[0] + (q[0] - p[0]) * k, p[1] + (q[1] - p[1]) * k))
        return 2
    for p, q in (left, right):
        pygame.draw.aaline(surface, color, p, q)
    return 2


def draw_conveyor(surface, world, c, camera, now_s, selected=None, color=None):
    """A belt: two cyan rails, with items running along it while it works.
    A site is dotted, solid as far as it is built."""
    line = ST.line_of(world, c)
    if line is None:
        return 0
    a, b, d, left, right = _rails(camera, *line)
    w, h = surface.get_size()
    if max(a[0], b[0]) < 0 or min(a[0], b[0]) > w or max(a[1], b[1]) < 0 or min(a[1], b[1]) > h:
        return 0
    if color is None:
        color = D.COLOR_FLOW
        if not c.built:
            color = D.COLOR_SITE
        elif c.deconstruct:
            color = _scale(D.COLOR_ALERT, 0.5 + 0.5 * (int(now_s * 2) % 2))
        elif not c.powered:
            color = _scale(color, 0.5 * _flicker(now_s, c.id))
        elif c.status != P.WORKING:
            color = _scale(color, 0.6)
        if selected == ("structure", c.id):
            color = D.COLOR_SELECT
    if not c.built:
        k = c.build_progress()
        for p, q in (left, right):
            G.dotted(surface, color, p, q, D.DOT_SPACING_PX)
            pygame.draw.aaline(surface, color, p, (p[0] + (q[0] - p[0]) * k, p[1] + (q[1] - p[1]) * k))
        return 2
    for p, q in (left, right):
        pygame.draw.aaline(surface, color, p, q)
    if c.status == P.WORKING:
        spacing = max(D.CONVEYOR_DOT_SPACING_CELLS * camera.zoom, 6.0)
        speed = S.CONVEYOR_ITEMS_PER_S * spacing   # one item arrives per second
        ux, uy = (b[0] - a[0]) / d, (b[1] - a[1]) / d
        pos = (now_s * speed) % spacing
        while pos < d:
            pygame.draw.circle(surface, D.COLOR_SELECT, (int(a[0] + ux * pos), int(a[1] + uy * pos)), 1)
            pos += spacing
    return 2


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
    """Supply pods coming down: a capsule falling out of the sky on a fading
    trail, a retro-rocket flare just before touchdown, then a dust ring."""
    now = world.time_s()
    n = 0
    for pod in world.orbit.falling:
        k = max(0.0, min(1.0, (pod.land_s - now) / CT.DROP_FALL_S))   # 1 at the top, 0 on the ground
        gx, gy = camera.world_to_screen(pod.x, pod.y)
        drop = k * k * D.POD_FALL_PX          # slows as the retros fire
        px, py = gx, gy - drop
        # Trail back up toward orbit, fading.
        for i in range(D.POD_TRAIL_STEPS):
            a, b = py - i * D.POD_TRAIL_STEP_PX, py - (i + 1) * D.POD_TRAIL_STEP_PX
            if b < 0:
                break
            pygame.draw.line(surface, _scale(D.COLOR_POWER, 0.5 * (1 - i / D.POD_TRAIL_STEPS)), (px, a), (px, b))
            n += 1
        # Landing marker on the ground.
        G.dotted_circle(surface, _scale(D.COLOR_POWER, 0.6), gx, gy, D.POD_SIZE_PX + 3, D.DOT_SPACING_PX)
        # Retro flare in the last moments.
        if k < D.POD_RETRO_FRACTION:
            flare = D.POD_FLARE_PX * (0.6 + 0.4 * math.sin(now * 40))
            for dx in (-0.35, 0.0, 0.35):
                pygame.draw.aaline(surface, D.COLOR_SELECT, (px + dx * 6, py + D.POD_SIZE_PX),
                                   (px + dx * 10, py + D.POD_SIZE_PX + flare))
            n += 3
        r = D.POD_SIZE_PX
        pygame.draw.aalines(surface, D.COLOR_POWER, True,
                            [(px - r * 0.6, py - r), (px + r * 0.6, py - r), (px + r, py + r * 0.6), (px - r, py + r * 0.6)])
        n += 4
    for x, y, t in world.orbit.landed:
        k = (now - t) / CT.DUST_S
        gx, gy = camera.world_to_screen(x, y)
        G.dotted_circle(surface, _scale(D.COLOR_DEBRIS, 1 - k), gx, gy, 4 + k * D.POD_DUST_RADIUS_PX, D.DOT_SPACING_PX)
        n += 6
    return n


def _draw_scan_beam(surface, s, camera):
    """Radar sweep: a faint beam with a short fading trail, long enough to
    cross the whole map (the scanner's detection range is separate)."""
    sx, sy = camera.world_to_screen(s.x, s.y)
    e = camera.extent
    r = max(math.hypot(cx - s.x, cy - s.y) for cx in (0, e) for cy in (0, e)) * camera.zoom
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

    for s in world.structures.values():
        if s.kind == "road":
            segments += draw_road(surface, world, s, camera, now_s, selected)
    segments += draw_tracks(surface, world, camera)
    draw_fields(surface, world, camera, now_s)
    draw_grid_links(surface, world, camera)
    segments += draw_feed_links(surface, world, camera, now_s)

    size = max(D.DEBRIS_SIZE_CELLS * z, D.DEBRIS_MIN_PX) / 2
    for piece in world.debris.values():
        if not piece.seen:
            continue
        sx, sy = to_screen(piece.x, piece.y)
        if _on_screen(sx, sy, size, w, h):
            segments += G.draw_shape(surface, D.COLOR_DEBRIS, G.DEBRIS_SHAPES[piece.kind], sx, sy, size)

    for s in world.structures.values():
        if s.kind == "conveyor":
            segments += draw_conveyor(surface, world, s, camera, now_s, selected)
    for s in world.structures.values():
        if s.is_line():
            continue
        if s.kind == "scanner" and s.built and s.powered:
            segments += _draw_scan_beam(surface, s, camera)
        segments += _draw_structure(surface, world, s, camera, now_s, selected)

    segments += draw_pods(surface, world, camera)
    if lander_lift > 0:
        return segments  # still landing: the rovers are aboard

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
        elif kind == "structure" and eid in world.structures and not world.structures[eid].is_line():
            s = world.structures[eid]
            sx, sy = to_screen(s.x, s.y)
            _brackets(surface, sx, sy, structure_half_px(s.spec, z, s.kind == "lander") * 1.15)
            reach = s.spec.get("grid_reach_cells", 0)
            if reach and s.built:
                G.dotted_circle(surface, D.COLOR_GRID_LINK, sx, sy, reach * z, D.DOT_SPACING_PX * 2)

    if ghost is not None:
        segments += draw_ghost(surface, world, camera, ghost)
    return segments


def draw_conveyor_ghost(surface, world, camera, ghost):
    """Conveyor placement: the source picked (or the one under the cursor), then
    the belt to the destination under the cursor, with its cost or why not."""
    _, src, hover, (mx, my) = ghost
    sx, sy = camera.world_to_screen(mx, my)
    a = world.structures.get(src) if src is not None else None
    b = world.structures.get(hover) if hover is not None else None
    if a is None:
        if b is None:
            draw_text(surface, "CONVEYOR: CLICK A BUILDING TO SEND FROM", (sx, sy + 14), 1, D.COLOR_TEXT, "center")
            return 0
        ok, reason = CONV.can_start(b)
        bx, by = camera.world_to_screen(b.x, b.y)
        _brackets(surface, bx, by, structure_half_px(b.spec, camera.zoom, b is world.lander) * 1.15)
        note = f"SEND FROM {b.spec['name'].upper()}" if ok else reason
        draw_text(surface, "CONVEYOR: " + note, (bx, by + 14), 1, D.COLOR_TEXT if ok else D.COLOR_ALERT, "center")
        return 0
    ax, ay = camera.world_to_screen(a.x, a.y)
    _brackets(surface, ax, ay, structure_half_px(a.spec, camera.zoom, a is world.lander) * 1.15)
    if b is None or b is a:
        G.dotted(surface, D.COLOR_GHOST_OK, (ax, ay), (sx, sy), D.DOT_SPACING_PX)
        draw_text(surface, f"FROM {a.spec['name'].upper()}: CLICK WHERE TO SEND", (sx, sy + 14), 1, D.COLOR_TEXT,
                  "center")
        return 0
    p = CONV.plan(world, a, b)
    p0, p1 = ST.link_ends(a, b)
    color = D.COLOR_GHOST_OK if p["ok"] else D.COLOR_ALERT
    _, _, _, left, right = _rails(camera, p0, p1)
    for q0, q1 in (left, right):
        G.dotted(surface, color, q0, q1, D.DOT_SPACING_PX)
    bx, by = camera.world_to_screen(b.x, b.y)
    if p["ok"]:
        cells = max(1, math.ceil(p["length"] - 1e-6))
        cost = ", ".join(f"{n * cells} {k.upper()}" for k, n in S.STRUCTURES["conveyor"]["cost_per_cell"].items())
        note = (f"TO {b.spec['name'].upper()}  {p['length']:.1f} CELLS  {cost}  CARRIES "
                + ", ".join(k.upper() for k in p["items"]))
        if p["credits"]:
            note += f"  GRADING {p['credits']} CR"
    else:
        note = p["reason"]
    draw_text(surface, note, (bx, by + 14), 1, D.COLOR_TEXT if p["ok"] else D.COLOR_ALERT, "center")
    return 2


def draw_road_ghost(surface, world, camera, ghost):
    """Road placement: the first end once clicked, then the strip to the cursor
    with its length and price, or why not."""
    _, start, (mx, my) = ghost
    sx, sy = camera.world_to_screen(mx, my)
    if start is None:
        pygame.draw.circle(surface, D.COLOR_GHOST_OK, (int(sx), int(sy)), 3, 1)
        draw_text(surface, "ROAD: CLICK WHERE IT STARTS", (sx, sy + 14), 1, D.COLOR_TEXT, "center")
        return 0
    p = ROADS.plan(world, start, (mx, my))
    color = D.COLOR_GHOST_OK if p["ok"] else D.COLOR_ALERT
    _, _, _, left, right = _rails(camera, start, (mx, my), S.ROAD_WIDTH_CELLS)
    for q0, q1 in (left, right):
        G.dotted(surface, color, q0, q1, D.DOT_SPACING_PX)
    if p["ok"]:
        note = f"ROAD {p['length']:.1f} CELLS  {p['credits']} CR"
        if p["grade_deg"] > 0:
            note += "  INCLUDING GRADING"
        note += f"  ROVERS {U.ROAD_SPEED_MULT:.0f}X FASTER"
    else:
        note = p["reason"]
    draw_text(surface, note, (sx, sy + 14), 1, D.COLOR_TEXT if p["ok"] else D.COLOR_ALERT, "center")
    return 2


def draw_ghost(surface, world, camera, ghost):
    """Placement preview: the structure where it would go, its grid reach, and why not."""
    if ghost[0] == "conveyor":
        return draw_conveyor_ghost(surface, world, camera, ghost)
    if ghost[0] == "road":
        return draw_road_ghost(surface, world, camera, ghost)
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
    if ok:
        grade = ST.grading_needed(world, kind, x, y)
        if grade > 0:
            note = f"GRADING {ST.grade_credits(spec, grade)} CR +{ST.grade_seconds(spec, grade):.0f} S  " + note
        feeds_to, fed_by = FEEDS.partners(world, kind, x, y)
        if feeds_to:
            note += "  FEEDS " + ", ".join(n.upper() for n in feeds_to)
        if fed_by:
            note += "  FED BY " + ", ".join(n.upper() for n in fed_by)
        if spec.get("snap"):
            n = sum(1 for o in world.structures.values() if o.kind == kind
                    and ((abs(abs(o.x - x) - spec["snap"]["cell"][0]) < 0.05 and abs(o.y - y) < 0.05)
                         or (abs(abs(o.y - y) - spec["snap"]["cell"][1]) < 0.05 and abs(o.x - x) < 0.05)))
            if n:
                note += f"  FARM +{n * spec['snap']['farm_bonus'] * 100:.0f}%"
    if ok and kind == "solar":
        note = f"+{spec['power_kw'] * world.illumination_at(x, y):.1f} KW  " + note
    if ok and "sun_speed" in spec:
        note = f"SUN {world.illumination_at(x, y) * 100:.0f}%  " + note
    if ok and "waste_heat" in spec:
        wh = spec["waste_heat"]
        warm = any(o.kind in wh["from"] and o.built and math.hypot(o.x - x, o.y - y)
                   <= spec["footprint_cells"] + o.spec["footprint_cells"] + wh["gap_cells"]
                   for o in world.structures.values())
        note = (f"WASTE HEAT {wh['speed']:.0f}X  " if warm else "") + note
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
        if s.is_line():
            continue
        sx, sy = camera.world_to_screen(s.x, s.y)
        r = max(structure_half_px(s.spec, camera.zoom, s.kind == "lander"), D.SELECT_PICK_RADIUS_PX)
        if math.hypot(sx - mx, sy - my) <= r:
            return ("structure", s.id)
    for s in world.structures.values():   # conveyors last: buildings sit on their ends
        line = ST.line_of(world, s) if s.is_line() else None
        if line and ST.distance_to_segment(mx, my, *(camera.world_to_screen(*p) for p in line)) <= D.CONVEYOR_PICK_PX:
            return ("structure", s.id)
    return None


def structure_at(world, x, y):
    """The building (not a conveyor) whose footprint is nearest the world point
    (x, y), within CONVEYOR_PICK_CELLS of its edge, or None."""
    best = None
    for s in world.structures.values():
        if s.is_line():
            continue
        d = math.hypot(s.x - x, s.y - y) - s.spec["footprint_cells"]
        if d <= S.CONVEYOR_PICK_CELLS and (best is None or d < best[0]):
            best = (d, s)
    return best[1] if best else None
