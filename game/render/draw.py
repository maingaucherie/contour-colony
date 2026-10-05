"""World to screen: camera transform and terrain line drawing."""

import pygame

from game.content import display as D
from game.content import terrain as T
from game.content import world as W
from game.render.contours import level_rank, tier_for_zoom


class Camera:
    """Centre (x, y) in cell units; zoom in screen pixels per cell."""

    def __init__(self, screen_size, world_extent):
        self.sw, self.sh = screen_size
        self.extent = world_extent
        self.min_zoom = min(self.sw, self.sh) / world_extent * D.ZOOM_FIT_MARGIN
        self.zoom = self.min_zoom
        self.x = self.y = world_extent / 2

    def clamp(self):
        self.zoom = min(max(self.zoom, self.min_zoom), D.ZOOM_MAX)
        self.x = min(max(self.x, 0.0), self.extent)
        self.y = min(max(self.y, 0.0), self.extent)

    def offset(self):
        return self.sw / 2 - self.x * self.zoom, self.sh / 2 - self.y * self.zoom

    def world_to_screen(self, x, y):
        ox, oy = self.offset()
        return x * self.zoom + ox, y * self.zoom + oy

    def screen_to_world(self, sx, sy):
        ox, oy = self.offset()
        return (sx - ox) / self.zoom, (sy - oy) / self.zoom

    def visible_rect(self):
        x0, y0 = self.screen_to_world(0, 0)
        x1, y1 = self.screen_to_world(self.sw, self.sh)
        return x0, y0, x1, y1

    def pan_pixels(self, dx, dy):
        self.x -= dx / self.zoom
        self.y -= dy / self.zoom
        self.clamp()

    def zoom_at(self, factor, sx, sy):
        """Zoom by factor, keeping the world point under (sx, sy) fixed."""
        wx, wy = self.screen_to_world(sx, sy)
        self.zoom = min(max(self.zoom * factor, self.min_zoom), D.ZOOM_MAX)
        self.x = wx - (sx - self.sw / 2) / self.zoom
        self.y = wy - (sy - self.sh / 2) / self.zoom
        self.clamp()


def _lerp_color(c0, c1, t):
    return tuple(int(a + (b - a) * t + 0.5) for a, b in zip(c0, c1))


def palette_color(stops, t):
    t = min(max(t, 0.0), 1.0)
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t <= t1:
            return _lerp_color(c0, c1, (t - t0) / (t1 - t0) if t1 > t0 else 0.0)
    return stops[-1][1]


def contour_colors(contours, min_h, max_h, view):
    """Colour per level k for the given view ('operations' or 'survey')."""
    colors = {}
    span = max(max_h - min_h, 1e-6)
    for k in range(contours.k_min, contours.k_max + 1):
        index = k % T.CONTOUR_INDEX_STEP == 0
        if view == "survey":
            base = palette_color(D.SURVEY_PALETTE, (k * contours.interval - min_h) / span)
            gain = D.SURVEY_INDEX_BRIGHTNESS if index else D.SURVEY_NORMAL_BRIGHTNESS
            full = tuple(int(c * gain) for c in base)
        else:
            full = D.COLOR_CONTOUR_OPS_INDEX if index else D.COLOR_CONTOUR_OPS
        # A ramp of faded versions, so fading lines need no per-frame colour maths.
        steps = D.CONTOUR_FADE_STEPS
        colors[k] = [tuple(int(c * q / steps) for c in full) for q in range(steps + 1)]
    return colors


def _smoothstep(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3.0 - 2.0 * t)


def zoom_alphas(zoom, tier_specs=T.CONTOUR_TIERS):
    """Visibility of each tier's levels at this zoom: tier 0 always, finer tiers
    fade in between min_zoom / FADE_RATIO and min_zoom."""
    out = []
    for spec in tier_specs:
        z1 = spec["min_zoom"]
        if z1 <= 0:
            out.append(1.0)
        else:
            z0 = z1 / T.CONTOUR_FADE_RATIO
            out.append(_smoothstep((zoom - z0) / (z1 - z0)))
    return out


class ContourShading:
    """Per-piece survey knowledge, cached. When the survey changes, only pieces
    near the changed areas are recomputed (a survey rover changes it every tick)."""

    def __init__(self, survey):
        self.survey = survey
        self.version = survey.version
        self.cache = {}   # id(piece) -> (piece, knowledge)
        r = T.CONTOUR_SURVEY_BLUR_CELLS
        self.reach = r
        steps = (-1.0, -0.5, 0.0, 0.5, 1.0)
        self.offsets = [(dx * r, dy * r) for dx in steps for dy in steps]

    def _invalidate(self):
        survey = self.survey
        rects = [c[1:] for c in survey.changes if c[0] > self.version]
        if survey.changes and survey.changes[0][0] > self.version + 1:
            self.cache.clear()  # missed some changes: start over
        else:
            r = self.reach
            stale = [key for key, (pl, _) in self.cache.items()
                     if any(x0 - r <= pl.mx <= x1 + r and y0 - r <= pl.my <= y1 + r for x0, y0, x1, y1 in rects)]
            for key in stale:
                del self.cache[key]
        self.version = survey.version

    def knowledge(self, pl):
        """Average survey level around a piece, 0..2."""
        if self.version != self.survey.version:
            self._invalidate()
        hit = self.cache.get(id(pl))
        if hit is None:
            level_at = self.survey.level_at
            k = sum(level_at(pl.mx + dx, pl.my + dy) for dx, dy in self.offsets) / len(self.offsets)
            self.cache[id(pl)] = (pl, k)
            return k
        return hit[1]


def draw_contours(surface, contours, camera, colors, shading=None):
    """Draw visible contour pieces. Finer levels fade in with zoom; survey
    knowledge around a piece brightens it. Returns the number of segments drawn."""
    z = camera.zoom
    ox, oy = camera.offset()
    vx0, vy0, vx1, vy1 = camera.visible_rect()
    aalines = pygame.draw.aalines
    alphas = zoom_alphas(z, contours.tier_specs)
    geometry = tier_for_zoom(z * T.CONTOUR_FADE_RATIO, contours.tier_specs)
    steps = D.CONTOUR_FADE_STEPS
    count = 0
    for chunk in contours.chunks:
        if chunk.x1 < vx0 or chunk.x0 > vx1 or chunk.y1 < vy0 or chunk.y0 > vy1:
            continue
        for k, lines in chunk.tiers[geometry]:
            rank = level_rank(k, contours.tier_specs)
            za = alphas[rank]
            if za <= 0.02:
                continue
            ramp = colors[k]
            for pl in lines:
                if pl.max_x < vx0 or pl.min_x > vx1 or pl.max_y < vy0 or pl.min_y > vy1:
                    continue
                a = za
                if shading is not None:
                    known = min(1.0, shading.knowledge(pl) / 2.0)  # survey levels 0..2
                    dim = T.CONTOUR_UNSURVEYED_BRIGHTNESS
                    a *= dim + (1.0 - dim) * known
                q = int(a * steps + 0.5)
                if q <= 0:
                    continue
                pts = [(x * z + ox, y * z + oy) for x, y in pl.points]
                aalines(surface, ramp[q], False, pts)
                count += len(pts) - 1
    return count


def draw_site_border(surface, camera):
    e = camera.extent
    corners = [camera.world_to_screen(x, y) for x, y in ((0, 0), (e, 0), (e, e), (0, e))]
    pygame.draw.lines(surface, D.COLOR_SITE_BORDER, True, corners)


def draw_slope_marks(surface, world, camera, max_slope, centre=None, radius=None, impassable_only=False):
    """Mark ground by slope: a green dot where something with max_slope can be
    built, a red cross where it's too steep. Around centre within radius (cells),
    or across the whole view at a spacing that keeps the count bounded. With
    impassable_only, crosses mark only ground rovers can't cross at all."""
    hm = world.heightmap
    n = hm.size
    slopes = world.slopes
    z = camera.zoom
    if centre is not None:
        cx, cy = centre
        x0, x1 = int(cx - radius), int(cx + radius) + 1
        y0, y1 = int(cy - radius), int(cy + radius) + 1
        step = 1
    else:
        vx0, vy0, vx1, vy1 = camera.visible_rect()
        x0, y0, x1, y1 = int(vx0), int(vy0), int(vx1) + 1, int(vy1) + 1
        area = max(1, (x1 - x0) * (y1 - y0))
        step = max(1, int((area / D.SLOPE_MARK_MAX) ** 0.5 + 0.999))
    x0, y0 = max(0, x0 - x0 % step), max(0, y0 - y0 % step)
    x1, y1 = min(n - 1, x1), min(n - 1, y1)
    ox, oy = camera.offset()
    arm = max(1.5, min(3.0, z * 0.12))
    blocked = W.SLOPE_IMPASSABLE_DEG if impassable_only else max_slope
    for y in range(y0, y1 + 1, step):
        row = y * n
        for x in range(x0, x1 + 1, step):
            if centre is not None:
                d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
                if d > radius:
                    continue
                k = 1.0 - d / radius
            else:
                k = 1.0
            sx, sy = x * z + ox, y * z + oy
            s = slopes[row + x]
            if s <= max_slope:
                c = tuple(int(v * (0.35 + 0.65 * k)) for v in D.COLOR_BUILDABLE)
                surface.set_at((int(sx), int(sy)), c)
            elif s > blocked:
                c = tuple(int(v * (0.35 + 0.65 * k)) for v in D.COLOR_TOO_STEEP)
                pygame.draw.line(surface, c, (sx - arm, sy - arm), (sx + arm, sy + arm))
                pygame.draw.line(surface, c, (sx - arm, sy + arm), (sx + arm, sy - arm))
