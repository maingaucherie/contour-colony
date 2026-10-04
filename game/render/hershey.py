"""Hershey stroke-font text, rendered once per (text, size, colour) and cached.

Text surfaces have a black background, which doubles as a legibility backing
for HUD text drawn over terrain.
"""

import pygame

from game.content import display as D
from game.render.hershey_data import GLYPHS

_FALLBACK = GLYPHS["\x7f"]
_TOP = min(y for _, _, strokes in GLYPHS.values() for s in strokes for _, y in s)
_BOTTOM = max(y for _, _, strokes in GLYPHS.values() for s in strokes for _, y in s)
_cache = {}


def _glyph(ch):
    return GLYPHS.get(ch, _FALLBACK)


def text_width(text, size=1):
    scale = D.TEXT_SCALES[size]
    units = sum(r - l + D.TEXT_LETTER_SPACING_UNITS for l, r, _ in map(_glyph, text))
    return int(units * scale + 0.5)


def line_height(size=1):
    return int((_BOTTOM - _TOP) * D.TEXT_SCALES[size] + 0.5)


def render(text, size=1, color=D.COLOR_TEXT):
    key = (text, size, color)
    surf = _cache.get(key)
    if surf is not None:
        return surf
    scale = D.TEXT_SCALES[size]
    surf = pygame.Surface((max(1, text_width(text, size) + 2), line_height(size) + 2))
    surf.fill(D.COLOR_BACKGROUND)
    pen = 1.0
    for left, right, strokes in map(_glyph, text):
        ox = pen - left * scale
        for stroke in strokes:
            pts = [(ox + x * scale, 1 + (y - _TOP) * scale) for x, y in stroke]
            if len(pts) > 1:
                pygame.draw.aalines(surf, color, False, pts)
        pen += (right - left + D.TEXT_LETTER_SPACING_UNITS) * scale
    if len(_cache) >= D.TEXT_CACHE_MAX:
        _cache.clear()
    _cache[key] = surf
    return surf


def draw_text(dest, text, pos, size=1, color=D.COLOR_TEXT, align="left", additive=False):
    """Blit cached text. pos is the top-left (or top-right/top-centre).

    By default the text's black background is kept, blanking what is under it
    so HUD text stays legible over terrain; additive=True adds light instead.
    """
    surf = render(text, size, color)
    x, y = pos
    if align == "right":
        x -= surf.get_width()
    elif align == "center":
        x -= surf.get_width() // 2
    return dest.blit(surf, (x, y), special_flags=pygame.BLEND_ADD if additive else 0)
