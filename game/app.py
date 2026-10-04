"""Application shell: loading state, running state, one frame at a time."""

import random
import sys
import time

import pygame

from game.content import display as D
from game.content import terrain as T
from game.render import draw
from game.render.contours import build_contours, tier_for_zoom
from game.render.glow import Glow
from game.sim.terrain import generate_terrain
from game.ui import hud
from game.ui.input import Input

WEB = sys.platform == "emscripten"
_STAGES = ("GENERATING TERRAIN", "TRACING CONTOURS")


class App:
    def __init__(self, seed=None):
        pygame.init()
        flags = 0 if WEB else pygame.SCALED | pygame.RESIZABLE
        self.screen = pygame.display.set_mode(D.SCREEN_SIZE, flags)
        pygame.display.set_caption(D.WINDOW_TITLE)
        self.clock = pygame.time.Clock()
        self.glow = Glow(self.screen)
        self.glow_on = D.GLOW_ENABLED
        self.input = Input()
        self.view = "operations"
        self.show_stats = True
        self.running = True
        self.segments = 0
        self.frame_ms = 0.0
        self.start_site(seed)

    # Site loading -------------------------------------------------------

    def start_site(self, seed=None):
        self.seed = random.randrange(T.SEED_MAX) if seed is None else seed
        self.heightmap = None
        self.contours = None
        self.camera = None
        self.stage = 0
        self.progress = 0.0
        self.loader = self._load()

    def _load(self):
        self.stage = 1
        self.heightmap = yield from generate_terrain(self.seed)
        self.stage = 2
        self.contours = yield from build_contours(self.heightmap)
        hm = self.heightmap
        self.colors = {view: draw.contour_colors(self.contours, hm.min_h, hm.max_h, view)
                       for view in ("operations", "survey")}
        self.camera = draw.Camera(D.SCREEN_SIZE, hm.size - 1)

    def _step_loader(self):
        deadline = time.perf_counter() + D.LOAD_BUDGET_MS / 1000.0
        while time.perf_counter() < deadline:
            try:
                self.progress = next(self.loader)
            except StopIteration:
                self.loader = None
                return

    # Frame ----------------------------------------------------------------

    def frame(self):
        dt = self.clock.tick(D.FRAME_RATE_CAP) / 1000.0
        start = time.perf_counter()
        for action in self.input.process(pygame.event.get(), self.camera):
            self._do(action)

        self.screen.fill(D.COLOR_BACKGROUND)
        if self.loader is not None:
            self._step_loader()
            hud.draw_loading(self.screen, self.seed, self.stage, len(_STAGES),
                             _STAGES[self.stage - 1], self.progress)
        else:
            self.input.apply_held(self.camera, dt)
            self._draw_site()
        hud.draw_frame(self.screen)
        if self.glow_on:
            self.glow.apply(self.screen)
        self.frame_ms = (time.perf_counter() - start) * 1000.0
        pygame.display.flip()

    def _do(self, action):
        if action == "quit" and not WEB:
            self.running = False
        elif action == "toggle_glow":
            self.glow_on = not self.glow_on
        elif action == "toggle_stats":
            self.show_stats = not self.show_stats
        elif action == "toggle_view":
            self.view = "survey" if self.view == "operations" else "operations"
        elif action == "new_site":
            self.start_site()

    def _draw_site(self):
        cam, hm = self.camera, self.heightmap
        tier = tier_for_zoom(cam.zoom)
        self.segments = draw.draw_contours(self.screen, self.contours, cam, tier, self.colors[self.view])
        draw.draw_site_border(self.screen, cam)

        cursor = None
        if self.input.mouse_inside:
            wx, wy = cam.screen_to_world(*self.input.mouse)
            if 0 <= wx <= cam.extent and 0 <= wy <= cam.extent:
                km = hm.cell_m / 1000.0
                cursor = (wx * km, wy * km, hm.sample(wx, wy), hm.slope_deg(wx, wy))
        hud.draw_running(self.screen, {
            "seed": self.seed, "view": self.view, "interval": self.contours.interval,
            "cursor": cursor, "cell_m": hm.cell_m, "zoom": cam.zoom, "tier": tier,
            "show_stats": self.show_stats, "fps": self.clock.get_fps(),
            "frame_ms": self.frame_ms, "segments": self.segments, "glow": self.glow_on,
        })
