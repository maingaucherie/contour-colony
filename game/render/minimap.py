"""Minimap: the whole site in a corner, with the colony on it and the view's outline.

The relief image is made once per site (it's slow to build); the colony and
the view outline are drawn on top every frame. Clicking the minimap moves the
camera there (the app does that, using to_world).
"""

import math

import pygame

from game.content import display as D
from game.render import draw
from game.sim import structures as ST


def relief(world, size_px):
    """A size_px square image of the site: brighter is higher, darker is steeper."""
    hm = world.heightmap
    n = hm.size
    span = max(hm.max_h - hm.min_h, 1e-6)
    step = n / size_px
    pixels = bytearray()
    for py in range(size_px):
        y = min(n - 1, int((py + 0.5) * step))
        for px in range(size_px):
            x = min(n - 1, int((px + 0.5) * step))
            i = y * n + x
            t = (hm.heights[i] - hm.min_h) / span
            shade = max(0.25, 1.0 - world.slopes[i] / D.MINIMAP_SLOPE_DARK_DEG)
            c = draw.palette_color(D.MINIMAP_PALETTE, t)
            pixels += bytes(int(v * shade) for v in c)
    return pygame.image.frombuffer(bytes(pixels), (size_px, size_px), "RGB").convert()


class Minimap:
    def __init__(self, world, screen_size):
        s = D.MINIMAP_SIZE_PX
        w, h = screen_size
        self.rect = pygame.Rect(w - D.HUD_MARGIN - 6 - s, h - D.MINIMAP_BOTTOM_PX - s, s, s)
        self.world = world
        self.image = relief(world, s)
        self.scale = s / world.heightmap.size   # pixels per cell

    def to_screen(self, x, y):
        return self.rect.x + x * self.scale, self.rect.y + y * self.scale

    def to_world(self, sx, sy):
        return (sx - self.rect.x) / self.scale, (sy - self.rect.y) / self.scale

    def contains(self, pos):
        return pos is not None and self.rect.collidepoint(pos)

    def draw(self, surface, camera):
        world = self.world
        surface.blit(self.image, self.rect)
        pygame.draw.rect(surface, D.COLOR_FRAME, self.rect.inflate(2, 2), 1)
        for f in world.fields:
            if f.hinted:
                cx, cy = self.to_screen(f.cx, f.cy)
                r = max(2, int(f.radius * self.scale))
                color = D.COLOR_FIELD_ICE if f.kind == "ice" else D.COLOR_FIELD
                pygame.draw.circle(surface, color, (int(cx), int(cy)), r, 1)
        for s in world.structures.values():
            if s.is_line():
                ends = ST.line_of(world, s)
                if ends:
                    a, b = ends
                    color = D.COLOR_FLOW if s.spec.get("carries") else D.COLOR_TEXT_DIM
                    pygame.draw.line(surface, color, self.to_screen(*a), self.to_screen(*b))
                continue
            x, y = self.to_screen(s.x, s.y)
            r = max(1, int(s.spec["footprint_cells"] * self.scale + 0.5))
            if not s.built:
                color = D.COLOR_TEXT_DIM
            elif s.powered or s.draw_kw() <= 0:
                color = D.COLOR_TEXT
            else:
                color = D.COLOR_ALERT   # built but unpowered
            pygame.draw.rect(surface, color, (int(x) - r // 2, int(y) - r // 2, max(r, 2), max(r, 2)))
        for u in world.units.values():
            x, y = self.to_screen(u.x, u.y)
            surface.set_at((int(x), int(y)), D.COLOR_FLOW)
        x0, y0, x1, y1 = camera.visible_rect()
        e = camera.extent
        x0, y0, x1, y1 = max(0.0, x0), max(0.0, y0), min(e, x1), min(e, y1)
        if x1 - x0 < e or y1 - y0 < e:
            (sx0, sy0), (sx1, sy1) = self.to_screen(x0, y0), self.to_screen(x1, y1)
            pygame.draw.rect(surface, D.COLOR_POWER,
                             (math.floor(sx0), math.floor(sy0), max(2, sx1 - sx0), max(2, sy1 - sy0)), 1)
