"""CRT bloom: blur the finished frame and add it back on top.

Everything is drawn as light on black, so adding the blurred copy over the
sharp lines looks the same as drawing it underneath, and needs one pass.
"""

import pygame

from game.content import display as D
from game.render.surfaces import new_surface


class Glow:
    def __init__(self, frame):
        # smoothscale needs matching formats: the frame must come from new_surface too.
        self.size = frame.get_size()
        self.small_size = (self.size[0] // D.GLOW_DOWNSCALE, self.size[1] // D.GLOW_DOWNSCALE)
        self.small = new_surface(self.small_size)
        self.big = new_surface(self.size)

    def apply(self, frame):
        pygame.transform.smoothscale(frame, self.small_size, self.small)
        pygame.transform.smoothscale(self.small, self.size, self.big)
        for _ in range(D.GLOW_GAIN):
            frame.blit(self.big, (0, 0), special_flags=pygame.BLEND_ADD)
