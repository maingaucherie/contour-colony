"""World to screen: camera transform and terrain line drawing."""

import pygame

from game.content import display as D
from game.content import terrain as T
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
    """Per-piece survey knowledge, cached until the survey changes."""

    def __init__(self, survey):
        self.survey = survey
        self.version = -1
        self.cache = {}
        r = T.CONTOUR_SURVEY_BLUR_CELLS
        steps = (-1.0, -0.5, 0.0, 0.5, 1.0)
        self.offsets = [(dx * r, dy * r) for dx in steps for dy in steps]

    def knowledge(self, pl):
        """Average survey level around a piece, 0..2."""
        if self.version != self.survey.version:
            self.version = self.survey.version
            self.cache.clear()
        key = id(pl)
        k = self.cache.get(key)
        if k is None:
            level_at = self.survey.level_at
            k = sum(level_at(pl.mx + dx, pl.my + dy) for dx, dy in self.offsets) / len(self.offsets)
            self.cache[key] = k
        return k


def draw_contours(surface, contours, camera, colors, shading=None):
    """Draw visible contour pieces. Finer levels fade in with zoom and with the
    survey knowledge around each piece. Returns the number of segments drawn."""
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
                if shading is not None and rank > 0:
                    a *= min(1.0, max(0.0, shading.knowledge(pl) - rank + 1))
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
