"""Landing intro: the lander comes down with its engine lit while the
briefing about the body types out. Times are real seconds since the intro
began; drawing only, the simulation waits."""

import math

import pygame

from game.content import contracts as C
from game.content import display as D
from game.render import glyphs as G
from game.render.hershey import draw_text, line_height


class Intro:
    def __init__(self, now, lines):
        self.start = now
        self.lines = lines
        self.total_chars = sum(len(t) for t in lines)
        self.skipped = False
        self.touched_down = False

    def elapsed(self, now):
        return D.INTRO_DESCENT_S + 99.0 if self.skipped else now - self.start

    def descent(self, now):
        """0 at the top of the descent .. 1 at touchdown."""
        return min(1.0, self.elapsed(now) / D.INTRO_DESCENT_S)

    def lift_px(self, now):
        p = self.descent(now)
        ease = 1 - (1 - p) ** 3          # fast at first, gentle at the end
        return (1 - ease) * D.INTRO_LANDER_START_PX

    def typing_done(self, now):
        return (self.elapsed(now) - D.INTRO_TEXT_DELAY_S) * D.INTRO_CHARS_PER_S >= self.total_chars

    def ready(self, now):
        return self.descent(now) >= 1.0 and self.typing_done(now)

    def skip(self):
        self.skipped = True

    def draw(self, surface, camera, lander, now, mode):
        t = self.elapsed(now)
        sx, sy = camera.world_to_screen(lander.x, lander.y)
        p = self.descent(now)
        if p < 1.0:
            # Engine plume under the descending lander.
            lift = self.lift_px(now)
            for k in range(5):
                a = math.pi / 2 + (k - 2) * 0.18
                n = D.INTRO_PLUME_PX * (0.6 + 0.4 * math.sin(now * 37 + k * 1.7))
                pygame.draw.aaline(surface, D.COLOR_POWER, (sx, sy - lift + 10),
                                   (sx + math.cos(a) * n, sy - lift + 10 + math.sin(a) * n))
        else:
            # Dust ring spreading out from touchdown.
            since = t - D.INTRO_DESCENT_S
            if since < D.INTRO_DUST_S:
                k = since / D.INTRO_DUST_S
                r = 12 + k * D.INTRO_DUST_RADIUS_PX
                color = tuple(int(c * (1 - k)) for c in D.COLOR_DEBRIS)
                G.dotted_circle(surface, color, sx, sy, r, D.DOT_SPACING_PX)
        # The briefing, typed out.
        shown = max(0, int((t - D.INTRO_TEXT_DELAY_S) * D.INTRO_CHARS_PER_S))
        lh = D.HUD_LINE_HEIGHT + 2
        bw = D.INTRO_PANEL_WIDTH
        rows = len(self.lines) + 4
        x = D.HUD_MARGIN + 20
        y = surface.get_height() - D.HUD_MARGIN - 20 - rows * lh - line_height(1)   # lower left, clear of the lander
        rect = pygame.Rect(x - 12, y - 12, bw, rows * lh + line_height(1) + 12)
        surface.fill(D.COLOR_BACKGROUND, rect)
        pygame.draw.rect(surface, D.COLOR_FRAME, rect, 1)
        for i, text in enumerate(self.lines):
            part = text[:max(0, shown)]
            shown -= len(text)
            if part:
                draw_text(surface, part, (x, y + i * lh), 1, D.COLOR_TEXT if i == 0 else D.COLOR_TEXT_DIM)
        if self.typing_done(now):
            yy = y + (len(self.lines) + 1) * lh
            pace = C.MODES[mode]
            note = "CONTRACTS ARE OFFERS YOU ACCEPT, NO DRAIN" if pace["accept_offers"] else "CONTRACTS ASSIGNED, REPUTATION DRAINS"
            draw_text(surface, f"PACE      {mode.upper()} - {note}", (x, yy), 1, D.COLOR_FLOW)
            draw_text(surface, "          P: SWITCH PACE", (x, yy + lh), 1, D.COLOR_TEXT_DIM)
            if self.ready(now) and int(now * 2) % 2 == 0:
                draw_text(surface, "CLICK OR PRESS ENTER TO BEGIN", (x, yy + 2 * lh + 4), 1, D.COLOR_TEXT)
