"""Application shell: loading state, running state, one frame at a time."""

import json
import random
import sys
import time

import pygame

from game.content import display as D
from game.content import terrain as T
from game.content import world as W
from game.content.research import RESEARCH, RESEARCH_MENU
from game.content.items import ITEMS
from game.content import structures as STRUCTURE_RULES
from game.content.structures import BUILD_MENU, STRUCTURES
from game.content.units import BAY_MENU
from game.audio.player import Audio
from game.render import draw, entities
from game.render.contours import build_contours, tier_for_zoom
from game.render.glow import Glow
from game.render.scenery import build_scenery
from game.render.surfaces import new_surface
from game.sim.terrain import generate_terrain
from game.sim.world import build_world
from game.sim import jobs
from game.sim import structures as ST
from game.content import audio as AUDIO
from game.content import contracts as CT
from game.sim.orbit import Orbit
from game import storage
from game.sim import body, save
from game.ui import board, hud, menus, panels
from game.ui.intro import Intro
from game.ui.input import Input

WEB = sys.platform == "emscripten"
_STAGES = ("TUNING AUDIO", "GENERATING TERRAIN", "TRACING CONTOURS", "SURVEYING SURROUNDINGS", "LANDING")
_TICK_S = 1.0 / W.TICK_RATE


class App:
    def __init__(self, seed=None, scaled=D.SCALED_WINDOW):
        pygame.mixer.pre_init(22050, -16, 1, 512)
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
        self.show_stats = False   # F shows frame rate and drawing stats
        self.running = True
        self.audio = Audio()
        self.audio_built = False
        self.mode = CT.DEFAULT_MODE    # pace of the next site (switchable on the briefing)
        self.events_heard = 0
        self.segments = 0
        self.frame_ms = 0.0
        self.world = None
        self.last_outcome = None
        self.last_overhead = False
        self.last_save = 0.0
        self.saved_at = -99.0         # real time of the last save, for the HUD's "SAVED" blink
        self._load_settings()
        # A site left unfinished last time is offered first (unless a seed was asked for).
        self.continue_offer = None
        if seed is None:
            text = storage.load_text(D.SAVE_KEY)
            info = save.summary(text) if text else None
            if info and info["outcome"] != "lost":
                self.continue_offer = (info, text)
        if self.continue_offer:
            self.world = self.loader = self.camera = None
            self.intro = None
        else:
            self.start_site(seed)

    # Settings and saves -------------------------------------------------------

    def _load_settings(self):
        try:
            data = json.loads(storage.load_text(D.SETTINGS_KEY) or "{}")
        except ValueError:
            data = {}
        if data.get("sound") in AUDIO.MODES:
            while self.audio.mode != data["sound"]:
                self.audio.cycle_mode()
        self.glow_on = bool(data.get("glow", self.glow_on))
        self.show_stats = bool(data.get("stats", self.show_stats))
        if data.get("icons") in D.ICON_STYLES:
            entities.style = data["icons"]
        if data.get("pace") in CT.MODES:
            self.mode = data["pace"]

    def _save_settings(self):
        storage.save_text(D.SETTINGS_KEY, json.dumps({
            "sound": self.audio.mode, "glow": self.glow_on, "stats": self.show_stats,
            "icons": entities.style, "pace": self.mode}))

    def _autosave(self, force=False):
        """Save the site every AUTOSAVE_S of real time (and when asked)."""
        world = self.world
        if world is None or self.loader is not None or self.intro is not None:
            return
        now = time.perf_counter()
        if not force and now - self.last_save < D.AUTOSAVE_S:
            return
        self.last_save = now
        if world.outcome == "lost":
            storage.delete(D.SAVE_KEY)  # nothing to come back to
            return
        if storage.save_text(D.SAVE_KEY, save.dumps(world)):
            self.saved_at = now

    # Site loading -------------------------------------------------------

    def start_site(self, seed=None, resume=None):
        """Begin loading a site: a new one, or (resume = save text) a saved one."""
        self.continue_offer = None
        self.resume = save.read(resume) if resume else None
        if self.resume:
            seed = self.resume["seed"]
            self.mode = self.resume["mode"]
        elif self.world is not None or seed is None:
            storage.delete(D.SAVE_KEY)   # a new site replaces the saved one
        if seed is None:
            # Seed from the clock: the browser build's default random source
            # gave every visitor the same site.
            seed = random.Random(time.time_ns()).randrange(T.SEED_MAX)
        self.seed = seed
        self.heightmap = None
        self.contours = None
        self.scenery = None
        self.camera = None
        self.world = None
        self.selected = None
        self.shading = None
        self.menu = None          # None, "build", "research" or "orbit"
        self.targeting = False    # choosing where an orbital scan goes
        self.board_rects = []     # clickable offers on the contracts board
        self.end_rects = None     # clickable choices on the site complete / lost screen
        self.last_tick_sound = 0.0
        self.menu_cursor = 0
        self.menu_rects = None    # (panel rect, row rects) from the last draw
        self.placing = None       # structure kind being placed
        self.confirm_new_until = 0.0
        self.paused = False
        self.speed_index = 0
        self.accumulator = 0.0
        self.actual_speed = 1.0
        self.stage = 0
        self.progress = 0.0
        self.intro = None
        self.resuming = False
        self.loader = self._load()

    def _load(self):
        if not self.audio_built:
            self.stage = 1
            yield from self.audio.build()
            self.audio_built = True
        self.stage = 2
        self.heightmap = yield from generate_terrain(self.seed)
        self.stage = 3
        self.contours = yield from build_contours(self.heightmap)
        hm = self.heightmap
        self.colors = {view: draw.contour_colors(self.contours, hm.min_h, hm.max_h, view)
                       for view in ("operations", "survey")}
        self.stage = 4
        self.scenery = yield from build_scenery(hm, self.contours.interval, self.seed)
        self.stage = 5
        self.world = yield from build_world(self.seed, hm, self.mode)
        if self.resume:
            save.apply(self.world, self.resume)
            self.resume = None
            self.resuming = True
        self.events_heard = self.world.event_count
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
                self.last_save = time.perf_counter()
                if self.resuming:
                    self.resuming = False
                    self.world.event("SITE RESTORED - WELCOME BACK")
                else:
                    self.intro = Intro(time.perf_counter(), body.briefing_lines(self.seed, body.generate(self.seed)))
                return

    # Frame ----------------------------------------------------------------

    def frame(self):
        dt = self.clock.tick(D.FRAME_RATE_CAP) / 1000.0
        start = time.perf_counter()
        actions = self.input.process(pygame.event.get(), self.camera)
        if self.continue_offer is not None:
            self._continue_screen(actions)
            return
        if self.intro is not None and self.loader is None:
            actions = self._intro_input(actions)
        for action in actions:
            self._do(action)

        self.screen.fill(D.COLOR_BACKGROUND)
        if self.loader is not None:
            self._step_loader()
            hud.draw_loading(self.screen, self.seed, self.stage, len(_STAGES),
                             _STAGES[self.stage - 1], self.progress)
        else:
            self.input.panning_enabled = self.menu is None and self.intro is None
            self.input.apply_held(self.camera, dt)
            if self.intro is None:
                self._handle_pointer_and_keys()
                self._advance(dt)
            self._draw_site()
            overhead = self.world.orbit.was_overhead
            if self.world.outcome != self.last_outcome or (overhead and not self.last_overhead):
                self._autosave(force=True)   # on winning or losing, and as each orbital pass begins
            self.last_outcome, self.last_overhead = self.world.outcome, overhead
            self._autosave()
        if self.world is not None and self.loader is None:
            self._sounds_for_events()
            supply, demand = self._power_summary()
            self.audio.update(time.perf_counter(), demand / supply if supply else 0.0, self._ambient_levels())
        hud.draw_frame(self.screen)
        if self.glow_on:
            self.glow.apply(self.screen)
        self.frame_ms = (time.perf_counter() - start) * 1000.0
        self.window.blit(self.screen, (0, 0))
        pygame.display.flip()

    def _continue_screen(self, actions):
        """Start-up: offer the site left unfinished last time."""
        info, text = self.continue_offer
        self.screen.fill(D.COLOR_BACKGROUND)
        rects = hud.draw_continue(self.screen, info, self.input.mouse)
        inp = self.input
        go_on = any(k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_c) for k in inp.keys_down)
        fresh = "new_site" in actions
        if inp.click is not None:
            go_on = go_on or rects[0].collidepoint(inp.click)
            fresh = fresh or rects[1].collidepoint(inp.click)
        if "quit" in actions and not WEB:
            self.running = False
        if go_on:
            try:
                self.start_site(resume=text)
            except save.SaveError as exc:
                print("could not load:", exc)
                self.start_site()
        elif fresh:
            self.start_site()
        hud.draw_frame(self.screen)
        if self.glow_on:
            self.glow.apply(self.screen)
        self.window.blit(self.screen, (0, 0))
        pygame.display.flip()

    def _intro_input(self, actions):
        """During the landing briefing: P switches pace, a click, Enter or Space
        skips ahead, then begins. Other actions (sound, glow, quit) pass through."""
        now = time.perf_counter()
        intro, inp = self.intro, self.input
        if any(ch == "P" for ch in inp.typed):
            self.mode = "pressure" if self.mode == "calm" else "calm"
            self.world.contracts.set_mode(self.mode)
            self._save_settings()
            self.audio.play("menu")
        go = inp.click is not None or "pause" in actions or any(
            k in (pygame.K_RETURN, pygame.K_KP_ENTER) for k in inp.keys_down)
        if go:
            if intro.ready(now):
                self.intro = None
                self.audio.play("confirm")
            else:
                intro.skip()
        inp.click = None
        inp.right_click = None
        return [a for a in actions if a in ("quit", "sound", "toggle_glow", "toggle_stats", "new_site")]

    def _do(self, action):
        if self.menu and action == "pause":
            return  # Space selects in menus
        if action == "quit":
            # Escape backs out of placement and menus first.
            if self.placing or self.menu or self.targeting:
                self.placing = self.menu = None
                self.targeting = False
            elif not WEB:
                self.running = False
        elif action == "toggle_glow":
            self.glow_on = not self.glow_on
            self._save_settings()
        elif action == "toggle_stats":
            self.show_stats = not self.show_stats
            self._save_settings()
        elif action == "toggle_view":
            self.view = "survey" if self.view == "operations" else "operations"
        elif action == "new_site":
            now = time.perf_counter()
            if self.world is None or self.world.outcome is not None or now < self.confirm_new_until:
                self.start_site()
            else:
                self.confirm_new_until = now + D.NEW_SITE_CONFIRM_S
                self.world.event("PRESS N AGAIN TO ABANDON THIS SITE AND START A NEW ONE", "alert")
        elif self.world is None:
            return
        elif action == "contracts" and self.world.outcome == "won" and not self.world.endless:
            self._keep_playing()
        elif action == "pause":
            self.paused = not self.paused
        elif action == "speed_up":
            self.speed_index = min(self.speed_index + 1, len(W.SIM_SPEEDS) - 1)
        elif action == "speed_down":
            self.speed_index = max(self.speed_index - 1, 0)
        elif action in ("sell", "sell_all"):
            amount = D.SELL_BATCH if action == "sell" else self.world.lander.storage.get("scrap", 0)
            self.audio.play("sell" if self.world.sell_scrap(amount) else "error")
        elif action == "centre" and self.selected is not None:
            x, y = self._selected_xy()
            self.camera.x, self.camera.y = x, y
            self.camera.clamp()
        elif action == "sound":
            mode = self.audio.cycle_mode()
            self._save_settings()
            if self.world is not None:
                self.world.event({"all": "SOUND ON", "sfx": "MUSIC OFF, EFFECTS ON", "off": "SOUND OFF"}[mode])
        elif action == "icons":
            styles = D.ICON_STYLES
            entities.style = styles[(styles.index(entities.style) + 1) % len(styles)]
            self._save_settings()
        elif action in ("build", "research", "orbit", "contracts"):
            self.menu = None if self.menu == action else action
            self.menu_cursor = 0
            self.placing = None
            self.targeting = False
        elif action == "clock":
            s = self._selected_structure()
            if s is not None and s.built and s.spec.get("recipe"):
                self.world.set_clock(s.id, ST.next_clock(self.world, s))
                self.audio.play("menu")
        elif action == "priority":
            s = self._selected_structure()
            if s is not None and s.spec.get("draw_kw"):
                order = W.PRIORITIES
                self.world.set_priority(s.id, order[(order.index(s.priority) + 1) % len(order)])
        elif action == "cancel_site":
            s = self._selected_structure()
            if s is not None:
                built = s.built
                ok, reason = self.world.toggle_deconstruct(s.id)
                if not ok:
                    self.world.event(reason, "alert")
                elif not built:
                    self.selected = None

    def _selected_structure(self):
        if self.selected and self.selected[0] == "structure":
            return self.world.structures.get(self.selected[1])
        return None

    def _menu_entries(self):
        if self.menu == "contracts":
            return [c.id for c in self.world.contracts.offers]
        if self.menu == "orbit":
            return board.orbit_entries(self.world)
        return BUILD_MENU if self.menu == "build" else RESEARCH_MENU

    def _menu_choose(self, i):
        world = self.world
        entries = self._menu_entries()
        if not 0 <= i < len(entries):
            return
        if self.menu == "contracts":
            ok, reason = world.accept_contract(entries[i])
            self.audio.play("confirm" if ok else "error")
            if not ok:
                world.event(reason, "alert")
            self.menu_cursor = max(0, min(self.menu_cursor, len(self._menu_entries()) - 1))
        elif self.menu == "orbit":
            kind, index = entries[i]
            if kind == "sell":
                n = world.sell(index, D.MARKET_BATCH)
                self.audio.play("sell" if n else "error")
                if n:
                    world.event(f"SOLD {n} {ITEMS[index]['name'].upper()} FOR {n * world.price(index)} CR")
                self.menu_cursor = min(self.menu_cursor, len(self._menu_entries()) - 1)
            elif kind == "supply":
                ok, reason = world.order_supply(index)
                self.audio.play("confirm" if ok else "error")
                if not ok:
                    world.event(f"{CT.SUPPLY[index]['name'].upper()}: {reason}", "alert")
            elif not Orbit.overhead(world.time_s()):
                self.audio.play("error")
                world.event("ORBITAL SCAN: SHIP NOT OVERHEAD", "alert")
            elif world.orbit.scan_used:
                self.audio.play("error")
                world.event("ORBITAL SCAN: ALREADY USED THIS PASS", "alert")
            else:
                self.targeting, self.menu = True, None
                self.audio.play("confirm")
        elif self.menu == "build":
            kind = entries[i]
            if world.unlocked(kind):
                self.placing, self.menu = kind, None
                self.audio.play("confirm")
            else:
                need = RESEARCH[STRUCTURES[kind]["unlocked_by"]]["name"].upper()
                world.event(f"{STRUCTURES[kind]['name'].upper()} NEEDS RESEARCH: {need}", "alert")
        else:
            node = entries[i]
            ok, reason = world.start_research(node)
            if ok:
                self.audio.play("confirm")
            else:
                world.event(f"{RESEARCH[node]['name'].upper()}: {reason}", "alert")

    def _menu_input(self):
        """Cursor (up/down, W/S), Enter/Space to choose, mouse hover and click,
        and number shortcuts in the build menu."""
        inp = self.input
        n = max(1, len(self._menu_entries()))
        for key in inp.keys_down:
            if key in (pygame.K_UP, pygame.K_w):
                self.menu_cursor = (self.menu_cursor - 1) % n
                self.audio.play("menu")
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.menu_cursor = (self.menu_cursor + 1) % n
                self.audio.play("menu")
            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self._menu_choose(self.menu_cursor)
                return
        if self.menu == "build":
            for ch in inp.typed:
                if ch in menus.BUILD_KEYS:
                    self.menu_cursor = menus.BUILD_KEYS.index(ch)
                    self._menu_choose(self.menu_cursor)
                    return
        if self.menu_rects is None:
            return
        panel, rows = self.menu_rects
        if inp.mouse_moved:  # hover only takes over when the mouse moves
            for i, row in enumerate(rows):
                if row.collidepoint(inp.mouse) and self.menu_cursor != i:
                    self.menu_cursor = i
                    self.audio.play("menu")
        if inp.click is not None:
            if panel.collidepoint(inp.click):
                for i, row in enumerate(rows):
                    if row.collidepoint(inp.click):
                        self._menu_choose(i)
            else:
                self.menu = None  # clicking the map closes the menu

    def _mouse_world(self):
        return self.camera.screen_to_world(*self.input.mouse)

    def _handle_pointer_and_keys(self):
        world, inp = self.world, self.input
        if self.menu:
            self._menu_input()
            return
        # Typed keys: the selected rover bay.
        bay = self._selected_structure()
        if bay is not None and bay.kind == "rover_bay" and bay.built:
            for ch in inp.typed:
                if ch.isdigit() and 0 < int(ch) <= len(BAY_MENU):
                    ok, reason = world.order_unit(bay.id, BAY_MENU[int(ch) - 1])
                    if not ok:
                        world.event(reason, "alert")
        # Pointer.
        if self.targeting:
            if inp.click is not None:
                x, y = self.camera.screen_to_world(*inp.click)
                ok, reason = world.orbital_scan(x, y)
                self.audio.play("order" if ok else "error")
                if not ok:
                    world.event(f"ORBITAL SCAN: {reason}", "alert")
                self.targeting = False
            if inp.right_click is not None:
                self.targeting = False
            return
        if self.placing:
            if inp.click is not None:
                x, y = ST.snap_position(world, self.placing, *self.camera.screen_to_world(*inp.click))
                site, reason = world.place(self.placing, x, y)
                self.audio.play("place" if site is not None else "error")
                if site is None:
                    world.event(f"CAN'T BUILD HERE: {reason}", "info")
                elif not (pygame.key.get_mods() & pygame.KMOD_SHIFT):
                    self.placing = None  # hold shift to place several
            if inp.right_click is not None:
                self.placing = None
            return
        if inp.click is not None and self.end_rects:
            for rect, choice in self.end_rects:
                if rect.collidepoint(inp.click):
                    if choice == "keep":
                        self._keep_playing()
                    else:
                        self.start_site()
                    return
        if inp.click is not None:
            for rect, offer_id in self.board_rects:
                if rect.collidepoint(inp.click):
                    ok, reason = world.accept_contract(offer_id)
                    self.audio.play("confirm" if ok else "error")
                    if not ok:
                        world.event(reason, "alert")
                    return
            picked = entities.pick(world, self.camera, self._alpha(), inp.click)
            if picked is not None and picked != self.selected:
                self.audio.play("select")
            self.selected = picked
        if inp.right_click is not None and self.selected and self.selected[0] == "unit":
            x, y = self.camera.screen_to_world(*inp.right_click)
            unit = world.units.get(self.selected[1])
            if unit is not None:
                kind = "survey" if unit.kind == "survey_rover" else "move"
                ok, reason = world.command_unit(unit.id, kind, x, y)
                self.audio.play("order" if ok else "error")
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
        deadline = time.perf_counter() + W.SIM_BUDGET_MS / 1000.0
        while self.accumulator >= _TICK_S:
            if ticks >= W.MAX_TICKS_PER_FRAME * speed or time.perf_counter() > deadline:
                self.accumulator = 0.0  # too far behind: drop time rather than spiral
                break
            self.world.tick()
            self.accumulator -= _TICK_S
            ticks += 1
        # Achieved speed (sim seconds per real second), smoothed, for the HUD.
        if dt > 0:
            achieved = ticks * _TICK_S / dt
            self.actual_speed += (achieved - self.actual_speed) * 0.05

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
        if self.shading is None or self.shading.survey is not world.survey:
            self.shading = draw.ContourShading(world.survey)
        self.segments = draw.draw_scenery(self.screen, self.scenery, cam, self.colors[self.view])
        self.segments += draw.draw_contours(self.screen, self.contours, cam, self.colors[self.view], self.shading)
        draw.draw_site_border(self.screen, cam)
        if self.view == "survey" and not self.placing:
            draw.draw_slope_marks(self.screen, world, cam, W.SLOPE_BUILDABLE_DEG, impassable_only=True)
        ghost = None
        if self.placing and self.input.mouse_inside:
            draw.draw_slope_marks(self.screen, world, cam, STRUCTURES[self.placing]["max_slope_deg"],
                                  self._mouse_world(), D.SLOPE_MARK_RADIUS_CELLS, gradable=STRUCTURE_RULES.GRADE_MAX_DEG)
            x, y = ST.snap_position(world, self.placing, *self._mouse_world())
            ok, reason = ST.check_placement(world, self.placing, x, y)
            ghost = (self.placing, x, y, ok, reason, STRUCTURES[self.placing])
        now = time.perf_counter()
        entities.lander_lift = self.intro.lift_px(now) if self.intro else 0.0
        self.segments += entities.draw_world(self.screen, world, cam, self._alpha(),
                                             now, self.selected, ghost)
        if self.intro is not None:
            if self.intro.descent(now) >= 1.0 and not self.intro.touched_down:
                self.intro.touched_down = True
                self.audio.play("thump")
            self.intro.draw(self.screen, cam, world.lander, now, self.mode)
            return
        if self.targeting and self.input.mouse_inside:
            mx, my = self.input.mouse
            r = CT.SCAN_RADIUS_CELLS * cam.zoom
            entities.G.dotted_circle(self.screen, D.COLOR_POWER, mx, my, r, D.DOT_SPACING_PX * 2)
            board.draw_text(self.screen, "ORBITAL SCAN: SURVEYS AND FLAGS FIELDS IN THIS CIRCLE", (mx, my + 10), 1,
                            D.COLOR_POWER, "center")

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
            "sinter": world.stock("sinter"), "reputation": world.contracts.reputation,
            "storage": (world.stored_total(), world.capacity()), "haulers": self._hauler_summary(),
            "power": self._power_summary(), "time_s": world.time_s(),
            "paused": self.paused, "speed": W.SIM_SPEEDS[self.speed_index], "actual_speed": self.actual_speed,
            "research": (RESEARCH[world.research.current]["name"], world.research.progress())
            if world.research.current else None,
            "events": [((world.tick_count - t) / world.tick_rate, text, kind) for t, text, kind in world.events],
            "hint": self._hint(),
            "saved": time.perf_counter() - self.saved_at < D.SAVED_BLINK_S,
            "complete": world.score() if world.endless else None,
        })
        now = time.perf_counter()
        board_bottom, self.board_rects = board.draw_board(self.screen, world, now,
                                                          self.input.mouse if self.input.mouse_inside else None)
        panels.draw_inspect(self.screen, world, self.selected, board_bottom + D.PANEL_GAP)
        self.menu_rects = None
        if self.menu == "build":
            self.menu_rects = menus.draw_build_menu(self.screen, world, D.HUD_MARGIN + 6, D.MENU_TOP, self.menu_cursor)
        elif self.menu == "research":
            self.menu_rects = menus.draw_research(self.screen, world, self.menu_cursor)
        elif self.menu == "orbit":
            self.menu_rects = board.draw_orbit_menu(self.screen, world, self.menu_cursor)
        elif self.menu == "contracts":
            self.menu_rects = board.draw_contracts_menu(self.screen, world, self.menu_cursor)
        self.end_rects = None
        if world.outcome is not None and not world.endless:
            self.end_rects = board.draw_end(self.screen, world, self.input.mouse)
        # A ticking clock while a contract is close to its deadline.
        if (not self.paused and world.outcome is None and now - self.last_tick_sound >= 1.0
                and any(board.contract_urgent(world, c) for c in world.contracts.open)):
            self.last_tick_sound = now
            self.audio.play("tick")

    def _sounds_for_events(self):
        """Chimes for new world events (the most important one per frame)."""
        world = self.world
        new = world.event_count - self.events_heard
        if new <= 0:
            return
        self.events_heard = world.event_count
        recent = list(world.events)[-min(new, len(world.events)):]
        rank = ("won", "lost", "alert", "contract", "field", "static", "thump", "research", "complete", "offer",
                "rolled")
        best = None
        for _, text, kind in recent:
            if kind == "won":
                name = "won"
            elif kind == "alert":
                name = "lost" if text.startswith("REPUTATION GONE") else "alert"
            elif kind == "contract":
                name = "contract" if text.startswith("CONTRACT FILLED") else "offer"
            elif kind == "orbit":
                name = "static" if text.startswith("ORBITAL PASS") else "thump"
            elif kind == "field":
                name = "field"
            elif text.startswith("RESEARCH COMPLETE"):
                name = "research"
            elif text.endswith("COMPLETE") or "DISMANTLED" in text:
                name = "complete"
            elif "ROLLED OUT" in text:
                name = "rolled"
            else:
                continue
            if best is None or rank.index(name) < rank.index(best):
                best = name
        if best:
            self.audio.play(best)

    def _hauler_summary(self):
        """(haulers, idle ones, production loads waiting for one)."""
        haulers = [u for u in self.world.units.values() if u.kind == "hauler"]
        idle = sum(1 for u in haulers if u.haul is None and not u.cargo_total())
        waiting = sum(1 for o in jobs.offers(self.world) if o[3] == "production")
        return len(haulers), idle, waiting

    def _ambient_levels(self):
        """Close-up sounds: how loud each category should be, from working
        machines and moving rovers near the middle of the screen."""
        cam = self.camera
        lo, hi = AUDIO.AMBIENT_ZOOM
        zoom_k = (cam.zoom - lo) / (hi - lo) if cam is not None else 0.0
        if zoom_k <= 0.0 or self.intro is not None or self.paused:
            return {}
        zoom_k = min(1.0, zoom_k)
        cx, cy = cam.sw / 2, cam.sh / 2
        levels = {}

        def add(kind, x, y):
            for cat, sources in AUDIO.AMBIENT_SOURCES.items():
                if kind in sources:
                    sx, sy = cam.world_to_screen(x, y)
                    k = 1.0 - ((sx - cx) ** 2 + (sy - cy) ** 2) ** 0.5 / AUDIO.AMBIENT_RANGE_PX
                    if k > 0:
                        levels[cat] = min(1.0, levels.get(cat, 0.0) + k)

        for s in self.world.structures.values():
            if s.built and s.status == "working" and s.powered:
                add(s.kind, s.x, s.y)
        for u in self.world.units.values():
            if u.state == "moving":
                add(u.kind, u.x, u.y)
        return {cat: v * zoom_k for cat, v in levels.items()}

    def _power_summary(self):
        grid = self.world.power_grids.get(self.world.lander.grid)
        return (grid["supply"], grid["demand"]) if grid else (0.0, 0.0)

    def _keep_playing(self):
        """After the win: the site runs on as a sandbox; the score stays as it was."""
        self.world.endless = True
        self.world.event("SITE HANDED OFF - YOU STAY ON AS CARETAKER. BUILD AS YOU LIKE", "won")
        self.audio.play("confirm")
        self._autosave(force=True)

    def _hint(self):
        if self.targeting:
            return "ORBITAL SCAN:  CLICK THE MAP TO SCAN THERE  RIGHT CLICK/ESC CANCEL"
        if self.placing:
            return (f"PLACING {STRUCTURES[self.placing]['name'].upper()}:  CLICK TO PLACE  "
                    "SHIFT+CLICK PLACE MORE  RIGHT CLICK/ESC CANCEL")
        return None
