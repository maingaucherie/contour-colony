"""World to screen: camera transform and terrain line drawing."""

import pygame

from game.content import display as D
from game.content import terrain as T


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
            colors[k] = tuple(int(c * gain) for c in base)
        else:
            colors[k] = D.COLOR_CONTOUR_OPS_INDEX if index else D.COLOR_CONTOUR_OPS
    return colors


def draw_contours(surface, contours, camera, tier, colors, chunk_tier_caps=None):
    """Draw visible polylines at the given detail tier, capped per chunk by
    chunk_tier_caps (survey knowledge). Returns the number of segments drawn."""
    z = camera.zoom
    ox, oy = camera.offset()
    vx0, vy0, vx1, vy1 = camera.visible_rect()
    aalines = pygame.draw.aalines
    count = 0
    for ci, chunk in enumerate(contours.chunks):
        if chunk.x1 < vx0 or chunk.x0 > vx1 or chunk.y1 < vy0 or chunk.y0 > vy1:
            continue
        t = tier if chunk_tier_caps is None else min(tier, chunk_tier_caps[ci])
        for k, lines in chunk.tiers[t]:
            color = colors[k]
            for pl in lines:
                if pl.max_x < vx0 or pl.min_x > vx1 or pl.max_y < vy0 or pl.min_y > vy1:
                    continue
                pts = [(x * z + ox, y * z + oy) for x, y in pl.points]
                aalines(surface, color, False, pts)
                count += len(pts) - 1
    return count


def draw_site_border(surface, camera):
    e = camera.extent
    corners = [camera.world_to_screen(x, y) for x, y in ((0, 0), (e, 0), (e, e), (0, e))]
    pygame.draw.lines(surface, D.COLOR_SITE_BORDER, True, corners)
