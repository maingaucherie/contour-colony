"""Offscreen surfaces with an explicit pixel format.

pygame.Surface(size), and Surface(size, 0, other), copy their pixel format
from the window's surface (or from other). That ties every internal surface
to the display, whose backing surface differs by platform, video driver and
renderer, and reading it crashed at startup on at least one Linux desktop.
An explicit depth uses pygame's standard masks and never touches the display.
The game draws into one of these and copies it to the window once per frame.
"""

import pygame

from game.content import display as D


def new_surface(size):
    return pygame.Surface(size, 0, D.SURFACE_DEPTH)
