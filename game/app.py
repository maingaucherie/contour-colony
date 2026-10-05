"""Application shell: loading state, running state, one frame at a time."""

import random
import sys
import time

import pygame

from game.content import display as D
from game.content import terrain as T
from game.content import world as W
from game.content.research import RESEARCH
from game.content.structures import STRUCTURES
from game.content.units import BAY_MENU
from game.render import draw, entities
from game.render.contours import build_contours, tier_for_zoom
from game.render.glow import Glow
from game.render.surfaces import new_surface
from game.sim.terrain import generate_terrain
from game.sim.world import build_world
from game.sim import structures as ST
from game.ui import hud, menus, panels
from game.ui.input import Input

WEB = sys.platform == "emscripten"
_STAGES = ("GENERATING TERRAIN", "TRACING CONTOURS", "LANDING")
_TICK_S = 1.0 / W.TICK_RATE


class App:
    def __init__(self, seed=None, scaled=D.SCALED_WINDOW):
        pygame.init()
        flags = pygame.SCALED | pygame.RESIZABLE if scaled and not WEB else 0
        self.window = pygame.display.set_mode(D.SCREEN_SIZE, flags)
        pygame.display.set_caption(D.WINDOW_TITLE)
        if WEB:
            # pygbag sizes the page canvas from its last known aspect ratio, which
            # is the 1x1 placeholder until asked again: fit it to our 16:9 frame.
            import platform

            platform.window.window_resize()
        # Everything draws into this offscreen frame, copied to the window per frame.
        self.screen = new_surface(D.SCREEN_SIZE)
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
        if seed is None:
            # Seed from the clock: the browser build's default random source
            # gave every visitor the same site.
            seed = random.Random(time.time_ns()).randrange(T.SEED_MAX)
        self.seed = seed
        self.heightmap = None
        self.contours = None
        self.camera = None
        self.world = None
        self.selected = None
        self.menu = None          # None, "build" or "research"
        self.placing = None       # structure kind being placed
        self.confirm_new_until = 0.0
        self.paused = False
        self.speed_index = 0
        self.accumulator = 0.0
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
        self.stage = 3
        self.world = yield from build_world(self.seed, hm)
        self.camera = draw.Camera(D.SCREEN_SIZE, hm.size - 1)
        self.camera.x, self.camera.y = self.world.lander.x, self.world.lander.y
        self.camera.zoom = D.START_ZOOM
        self.camera.clamp()

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
            self.input.panning_enabled = self.menu != "research"
            self.input.apply_held(self.camera, dt)
            self._handle_pointer_and_keys()
            self._advance(dt)
            self._draw_site()
        hud.draw_frame(self.screen)
        if self.glow_on:
            self.glow.apply(self.screen)
        self.frame_ms = (time.perf_counter() - start) * 1000.0
        self.window.blit(self.screen, (0, 0))
        pygame.display.flip()

    def _do(self, action):
        if action == "quit":
            # Escape backs out of placement and menus first.
            if self.placing or self.menu:
                self.placing = self.menu = None
            elif not WEB:
                self.running = False
        elif action == "toggle_glow":
            self.glow_on = not self.glow_on
        elif action == "toggle_stats":
            self.show_stats = not self.show_stats
        elif action == "toggle_view":
            self.view = "survey" if self.view == "operations" else "operations"
        elif action == "new_site":
            now = time.perf_counter()
            if self.world is None or now < self.confirm_new_until:
                self.start_site()
            else:
                self.confirm_new_until = now + D.NEW_SITE_CONFIRM_S
                self.world.event("PRESS N AGAIN TO ABANDON THIS SITE AND START A NEW ONE", "alert")
        elif self.world is None:
            return
        elif action == "pause":
            self.paused = not self.paused
        elif action == "speed_up":
            self.speed_index = min(self.speed_index + 1, len(W.SIM_SPEEDS) - 1)
        elif action == "speed_down":
            self.speed_index = max(self.speed_index - 1, 0)
        elif action == "sell":
            self.world.sell_scrap(D.SELL_BATCH)
        elif action == "sell_all":
            self.world.sell_scrap(self.world.lander.storage.get("scrap", 0))
        elif action == "centre" and self.selected is not None:
            x, y = self._selected_xy()
            self.camera.x, self.camera.y = x, y
            self.camera.clamp()
        elif action == "build":
            self.menu = None if self.menu == "build" else "build"
            self.placing = None
        elif action == "research":
            self.menu = None if self.menu == "research" else "research"
            self.placing = None
        elif action == "priority":
            s = self._selected_structure()
            if s is not None and s.spec.get("draw_kw"):
                order = W.PRIORITIES
                self.world.set_priority(s.id, order[(order.index(s.priority) + 1) % len(order)])
        elif action == "cancel_site":
            s = self._selected_structure()
            if s is not None and not s.built:
                self.world.cancel(s.id)
                self.selected = None

    def _selected_structure(self):
        if self.selected and self.selected[0] == "structure":
            return self.world.structures.get(self.selected[1])
        return None

    def _mouse_world(self):
        return self.camera.screen_to_world(*self.input.mouse)

    def _handle_pointer_and_keys(self):
        world, inp = self.world, self.input
        # Typed keys: menus first, then the selected rover bay.
        for ch in inp.typed:
            if self.menu == "build":
                kind = menus.build_key(world, ch)
                if kind:
                    self.placing, self.menu = kind, None
            elif self.menu == "research":
                node = menus.research_key(ch)
                if node:
                    ok, reason = world.start_research(node)
                    if not ok:
                        world.event(f"{RESEARCH[node]['name'].upper()}: {reason}", "alert")
            else:
                s = self._selected_structure()
                if s is not None and s.kind == "rover_bay" and s.built and ch.isdigit():
                    i = int(ch) - 1
                    if 0 <= i < len(BAY_MENU):
                        ok, reason = world.order_unit(s.id, BAY_MENU[i])
                        if not ok:
                            world.event(reason, "alert")
        # Pointer.
        if self.placing:
            if inp.click is not None:
                x, y = self.camera.screen_to_world(*inp.click)
                site, reason = world.place(self.placing, x, y)
                if site is None:
                    world.event(f"CAN'T BUILD HERE: {reason}", "alert")
                elif not (pygame.key.get_mods() & pygame.KMOD_SHIFT):
                    self.placing = None  # hold shift to place several
            if inp.right_click is not None:
                self.placing = None
            return
        if inp.click is not None:
            self.selected = entities.pick(world, self.camera, self._alpha(), inp.click)
        if inp.right_click is not None and self.selected and self.selected[0] == "unit":
            x, y = self.camera.screen_to_world(*inp.right_click)
            unit = world.units.get(self.selected[1])
            if unit is not None:
                kind = "survey" if unit.kind == "survey_rover" else "move"
                ok, reason = world.command_unit(unit.id, kind, x, y)
                world.event(("ORDER: " + ("SURVEY THERE" if kind == "survey" else "GO THERE")) if ok
                            else f"ORDER REFUSED: {reason}", "info" if ok else "alert")

    # Simulation ---------------------------------------------------------------

    def _advance(self, dt):
        """Run fixed 10 Hz ticks for the real time that passed, times the sim speed."""
        if self.paused:
            return
        speed = W.SIM_SPEEDS[self.speed_index]
        self.accumulator += dt * speed
        ticks = 0
        while self.accumulator >= _TICK_S:
            if ticks >= W.MAX_TICKS_PER_FRAME * speed:
                self.accumulator = 0.0  # too far behind: drop time rather than spiral
                break
            self.world.tick()
            self.accumulator -= _TICK_S
            ticks += 1

    def _alpha(self):
        return min(self.accumulator / _TICK_S, 1.0)

    def _selected_xy(self):
        kind, eid = self.selected
        if kind == "unit" and eid in self.world.units:
            return entities.interp(self.world.units[eid], self._alpha())
        s = self.world.structures.get(eid)
        return (s.x, s.y) if s else (self.camera.x, self.camera.y)

    def _draw_site(self):
        cam, hm = self.camera, self.heightmap
        tier = tier_for_zoom(cam.zoom)
        world = self.world
        caps = [W.SURVEY_LEVEL_TO_TIER[level] for level in world.survey.chunk_levels()]
        self.segments = draw.draw_contours(self.screen, self.contours, cam, tier, self.colors[self.view], caps)
        draw.draw_site_border(self.screen, cam)
        ghost = None
        if self.placing and self.input.mouse_inside:
            x, y = self._mouse_world()
            ok, reason = ST.check_placement(world, self.placing, x, y)
            ghost = (self.placing, x, y, ok, reason, STRUCTURES[self.placing])
        self.segments += entities.draw_world(self.screen, world, cam, self._alpha(),
                                             time.perf_counter(), self.selected, ghost)

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
            "credits": world.credits, "scrap": world.stock("scrap"), "parts": world.stock("parts"),
            "power": self._power_summary(), "time_s": world.time_s(),
            "paused": self.paused, "speed": W.SIM_SPEEDS[self.speed_index],
            "research": (RESEARCH[world.research.current]["name"], world.research.progress())
            if world.research.current else None,
            "events": [((world.tick_count - t) / world.tick_rate, text, kind) for t, text, kind in world.events],
            "hint": self._hint(),
        })
        panels.draw_inspect(self.screen, world, self.selected, D.PANEL_TOP)
        if self.menu == "build":
            menus.draw_build_menu(self.screen, world, D.HUD_MARGIN + 6, D.MENU_TOP)
        elif self.menu == "research":
            menus.draw_research(self.screen, world)

    def _power_summary(self):
        grid = self.world.power_grids.get(self.world.lander.grid)
        return (grid["supply"], grid["demand"]) if grid else (0.0, 0.0)

    def _hint(self):
        if self.placing:
            return (f"PLACING {STRUCTURES[self.placing]['name'].upper()}:  CLICK TO PLACE  "
                    "SHIFT+CLICK PLACE MORE  RIGHT CLICK/ESC CANCEL")
        return None
