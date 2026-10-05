"""World: terrain, structures, units, debris, fields, survey, research, credits,
and the fixed-step tick.

Tick order follows the design: power -> production -> job board -> units ->
wear -> contracts. Production covers research, rover bays, scanners and
recipes; the job board is consulted by haulers as they think; orbital passes
run after production. Wear arrives with a later milestone.
Commands (methods called by the UI between ticks) are the only way the
player changes the world, so a replay of commands reproduces a run.
"""

import math
import random
from collections import deque

from game.content import items as I
from game.content import units as U
from game.content import world as W
from game.content.research import RESEARCH
from game.content.structures import STRUCTURES
from game.content.terrain import CONTOUR_CHUNK_CELLS
from game.content import contracts as CT
from game.sim import debris, feeds, fields, power, production, structures, units
from game.sim.contracts import Contracts
from game.sim.orbit import Orbit
from game.sim.pathing import PathGrid
from game.sim.research import Research
from game.sim.survey import SurveyMap
from game.sim.tracks import Tracks
from game.sim.terrain import illumination


class World:
    def __init__(self, seed, heightmap, slopes, grid, light, mode=CT.DEFAULT_MODE):
        self.seed = seed
        self.rng = random.Random(f"{seed}/world")
        self.heightmap = heightmap
        self.slopes = slopes
        self.grid = grid
        self.illumination = light
        self.tick_rate = W.TICK_RATE
        self.tick_count = 0
        self.next_id = 1
        self.structures = {}
        self.units = {}
        self.debris = {}
        self.fields = []
        self.credits = W.START_CREDITS
        self.scrap_spawned = 0
        self.scrap_sold = 0
        self.consumed = {}            # items used up: construction, rover bays, recipes, contracts
        self.produced = {}            # items made: recipes, supply drops
        self.contracts = Contracts(seed, mode)
        self.orbit = Orbit()
        self.outcome = None           # None, "won" or "lost"
        self.storage_full = False
        self._feeds = None
        self.autosold = 0             # scrap sold on arrival since the last report
        self.outcome_text = ""
        self.end_s = None
        self.debris_timer = round(W.DEBRIS_SPAWN_INTERVAL_S * W.TICK_RATE)
        self.lander = None
        self.home_field = None
        self.charge_field = None
        self.charger_key = None
        self.spawn_map = None
        self.survey = SurveyMap(heightmap.size, CONTOUR_CHUNK_CELLS)
        self.tracks = Tracks(heightmap.size)
        self.research = Research()
        self.power_grids = {}
        self.dirty_power = True
        self.events = deque(maxlen=W.EVENT_LOG_LENGTH)
        self.event_count = 0          # total events ever, so listeners can spot new ones

    def new_id(self):
        uid = self.next_id
        self.next_id += 1
        return uid

    def event(self, text, kind="info"):
        self.events.append((self.tick_count, text, kind))
        self.event_count += 1

    def time_s(self):
        return self.tick_count / W.TICK_RATE

    # Queries ----------------------------------------------------------------------

    def illumination_at(self, x, y):
        n = self.heightmap.size
        return self.illumination[min(max(int(y), 0), n - 1) * n + min(max(int(x), 0), n - 1)]

    def battery_capacity(self, kind):
        return U.UNITS[kind]["battery"] * self.research.effect("battery_mult", 1.0)

    def storages(self):
        return [s for s in self.structures.values() if s.stores()]

    def stock(self, item):
        return sum(s.storage.get(item, 0) for s in self.storages())

    def chargers(self):
        return [s for s in self.structures.values() if s.charges() and (s.powered or s is self.lander)]

    def unlocked(self, kind):
        spec = STRUCTURES.get(kind) or U.UNITS.get(kind)
        return self.research.unlocked(spec.get("unlocked_by"))

    # Storage --------------------------------------------------------------------------

    def store(self, s, item, amount):
        """Move up to amount items into structure s. Returns how many fit."""
        n = max(0, min(amount, s.spec["storage"] - s.stored()))
        if n:
            s.storage[item] = s.storage.get(item, 0) + n
        return n

    def deliver(self, s, item, amount):
        """A hauler unloading at s: into a recipe's input buffer, straight to the
        contracts at an export bay (capacity doesn't apply to goods that ship),
        or into storage. Returns how many were accepted."""
        r = s.spec.get("recipe")
        if r and item in r["in"]:
            put = max(0, min(amount, production.input_cap(s, item) - s.inputs.get(item, 0)))
            if put:
                s.inputs[item] = s.inputs.get(item, 0) + put
            return put
        put = self.contracts.receive(self, item, amount) if s.spec.get("export_bay") else 0
        if s.stores():
            put += self.store(s, item, amount - put)
        return put

    # Colony storage ----------------------------------------------------------------------

    def capacity(self):
        return sum(s.spec["storage"] for s in self.storages())

    def stored_total(self):
        return sum(s.stored() for s in self.storages())

    def item_cap(self, item):
        share = I.ITEMS[item].get("cap_fraction", W.ITEM_CAP_FRACTION)
        return max(W.ITEM_CAP_MIN, int(share * self.capacity()))

    def storage_room(self, item):
        """How many more of item storage will take (cap minus stock and what's on its way)."""
        coming = sum(s.reserved_in.get(item, 0) for s in self.storages() if not s.spec.get("export_bay")
                     or item not in self.contracts.needs())
        return max(0, self.item_cap(item) - self.stock(item) - coming)

    @staticmethod
    def price(item):
        spec = I.ITEMS[item]
        return spec.get("sell_price", max(1, int(spec["value"] * W.SPOT_PRICE_FRACTION)))

    def sell(self, item, amount):
        """Sell up to amount of item from colony storage (lander first, never
        items a hauler has reserved). Returns how many were sold."""
        sold = 0
        for s in [self.lander] + [s for s in self.storages() if s is not self.lander]:
            free = s.storage.get(item, 0) - s.reserved_out.get(item, 0)
            n = max(0, min(amount - sold, free))
            if n:
                s.storage[item] -= n
                if not s.storage[item]:
                    del s.storage[item]
                sold += n
        if sold:
            self._sold(item, sold)
        return sold

    def _sold(self, item, n):
        self.credits += n * self.price(item)
        if item == "scrap":
            self.scrap_sold += n
        else:
            self.consumed[item] = self.consumed.get(item, 0) + n

    def unload_scrap(self, s, amount):
        """A scavenger unloading at s: store what fits under the cap, sell the rest."""
        keep = min(amount, max(0, self.item_cap("scrap") - self.stock("scrap")))
        stored = self.store(s, "scrap", keep)
        extra = amount - stored
        if extra:
            self._sold("scrap", extra)
            self.autosold += extra
        return amount

    def take_items(self, cost):
        """Take a whole cost {item: n} from storage (lander first), or nothing."""
        order = [self.lander] + [s for s in self.storages() if s is not self.lander]

        def free(s, k):  # never what a hauler has reserved
            return max(0, s.storage.get(k, 0) - s.reserved_out.get(k, 0))

        if any(sum(free(s, k) for s in order) < n for k, n in cost.items()):
            return False
        for k, n in cost.items():
            for s in order:
                take = min(n, free(s, k))
                if take:
                    s.storage[k] -= take
                    if not s.storage[k]:
                        del s.storage[k]
                    n -= take
            self.consumed[k] = self.consumed.get(k, 0) + cost[k]
        return True

    def scrap_accounted(self):
        """Every scrap ever spawned, wherever it is now (for conservation checks)."""
        on_sites = sum(s.delivered.get("scrap", 0) for s in self.structures.values() if not s.built)
        return (sum(d.value for d in self.debris.values())
                + sum(u.cargo.get("scrap", 0) for u in self.units.values())
                + self.stock("scrap") + on_sites + self.scrap_sold
                + self.consumed.get("scrap", 0) - W.START_STORAGE.get("scrap", 0))

    # Commands (applied between ticks) ------------------------------------------------

    def sell_scrap(self, amount):
        """Sell up to amount scrap from colony storage. Returns how many were sold."""
        return self.sell("scrap", amount)

    def place(self, kind, x, y):
        return structures.place_site(self, kind, x, y)

    def cancel(self, structure_id):
        s = self.structures.get(structure_id)
        if s is not None and not s.built:
            # Constructors carrying for it put their cargo back into storage later.
            for u in self.units.values():
                if u.job == structure_id:
                    units.brain(u).drop_job(self, u)
                    units.idle(u)
            # Materials already delivered are refunded; count them as stock again.
            structures.cancel_site(self, s)
            return True
        return False

    def toggle_deconstruct(self, structure_id):
        """Mark a built structure for dismantling (or unmark it). Returns (ok, reason)."""
        s = self.structures.get(structure_id)
        if s is None or s is self.lander:
            return False, "THE LANDER STAYS"
        if not s.built:
            return self.cancel(structure_id), ""
        s.deconstruct = not s.deconstruct
        s.teardown_s = 0.0
        if not s.deconstruct:
            for u in self.units.values():
                if u.job == s.id:
                    units.brain(u).drop_job(self, u)
                    units.idle(u)
        self.event(f"{s.spec['name'].upper()} " + ("MARKED FOR DECONSTRUCTION" if s.deconstruct else "KEPT"))
        return True, ""

    def set_priority(self, structure_id, priority):
        s = self.structures.get(structure_id)
        if s is not None and priority in W.PRIORITIES:
            s.priority = priority
            self.dirty_power = True

    def start_research(self, node):
        ok, reason = self.research.can_start(node, self.credits)
        if ok:
            self.credits -= RESEARCH[node]["cost"]
            self.research.start(node)
            self.event(f"RESEARCH STARTED: {RESEARCH[node]['name'].upper()}")
        return ok, reason

    def order_unit(self, bay_id, kind):
        s = self.structures.get(bay_id)
        if s is None or s.kind != "rover_bay" or not s.built:
            return False, "NO ROVER BAY"
        if not self.unlocked(kind):
            return False, "NOT RESEARCHED"
        if len(s.queue) >= 5:
            return False, "QUEUE FULL"
        s.queue.append(kind)
        return True, ""

    def command_unit(self, unit_id, kind, x, y):
        u = self.units.get(unit_id)
        if u is None or u.state == units.STRANDED:
            return False, "UNAVAILABLE"
        if kind == "survey" and u.kind != "survey_rover":
            kind = "move"
        return units.give_order(self, u, kind, x, y)

    # Systems -----------------------------------------------------------------------

    def reveal_debris(self, x, y, radius):
        """Mark debris within radius as seen. Returns how many were new."""
        n = 0
        r2 = radius * radius
        for d in self.debris.values():
            if not d.seen and (d.x - x) ** 2 + (d.y - y) ** 2 <= r2:
                d.seen = True
                n += 1
        return n

    def hint_field(self, f):
        if not f.hinted:
            f.hinted = True
            self.event(f"FIELD SIGNAL: POSSIBLE {f.kind.upper()} DEPOSIT", "field")
            # Ground already surveyed in detail confirms it straight away.
            if any(self.survey.level_at(x, y) >= 2 for x, y in f.sample_points(1.0)):
                f.confirmed = True
                self.event(f"{f.kind.upper()} FIELD CONFIRMED - RICHNESS {f.richness:.1f}X", "field")

    def survey_area(self, x, y, radius, level):
        """Raise survey levels. Ground surveys never discover fields: only the
        scanner (or an orbital scan) flags them. A detailed (level 2) survey
        over a flagged field confirms it."""
        changed = self.survey.raise_area(x, y, radius, level)
        if not changed or level < 2:
            return
        res = self.survey.res
        for f in self.fields:
            if f.confirmed or not f.hinted:
                continue
            for i in changed:
                sy, sx = divmod(i, self.survey.n)
                if f.contains((sx + 0.5) * res, (sy + 0.5) * res):
                    f.confirmed = True
                    self.event(f"{f.kind.upper()} FIELD CONFIRMED - RICHNESS {f.richness:.1f}X", "field")
                    break

    def spawn_unit(self, kind, x, y):
        uid = self.new_id()
        u = units.make_unit(self, uid, kind, x, y)
        self.units[uid] = u
        return u

    def structures_changed(self):
        self.dirty_power = True
        self._feeds = None
        structures.refresh_output(self)

    def feed_links(self):
        """Direct-feed links between touching buildings, cached until structures change."""
        if self._feeds is None:
            self._feeds = feeds.links(self)
        return self._feeds

    def _refresh_chargers(self):
        """Recompute the nearest-charger field and debris spawn area when chargers change."""
        chargers = self.chargers()
        key = tuple(sorted(s.id for s in chargers))
        if key == self.charger_key:
            return
        self.charger_key = key
        nodes = tuple(sorted({self.grid.node_at(s.x, s.y) for s in chargers}))
        self.charge_field = self.grid.field(nodes)
        scav = U.UNITS["scavenger"]
        usable = (1.0 - U.LOW_BATTERY_FRACTION) * self.battery_capacity("scavenger") - scav["pickup_energy"]
        max_round_trip = usable / (scav["drain_per_cost_cell"] * U.TRIP_SAFETY_FACTOR)
        self.spawn_map.update(self.charge_field, [(s.x, s.y) for s in chargers], max_round_trip)

    def _check_storage(self):
        if self.autosold >= W.SELL_EVENT_EVERY:
            self.event(f"SURPLUS SCRAP SOLD: {self.autosold} FOR {self.autosold * self.price('scrap')} CR")
            self.autosold = 0
        full = self.stored_total() >= W.STORAGE_FULL_FRACTION * self.capacity()
        if full and not self.storage_full:
            self.event("STORAGE FULL - BUILD A DEPOT", "alert")
        self.storage_full = full

    def finish(self, outcome, text):
        if self.outcome is None:
            self.outcome, self.outcome_text, self.end_s = outcome, text, self.time_s()
            self.event(text, "won" if outcome == "won" else "alert")

    def score(self):
        c = self.contracts
        minutes = (self.end_s if self.end_s is not None else self.time_s()) / 60.0
        bonus = max(0.0, CT.SCORE_TIME_TARGET_MIN - minutes) * CT.SCORE_TIME_BONUS_PER_MIN if self.outcome == "won" else 0.0
        return int(c.credits_earned + c.reputation * CT.SCORE_REPUTATION + bonus)

    def item_total(self, item):
        """Every unit of an item that physically exists on site (for ledger checks)."""
        n = 0
        for s in self.structures.values():
            n += s.storage.get(item, 0) + s.inputs.get(item, 0) + s.outputs.get(item, 0)
            if not s.built:
                n += s.delivered.get(item, 0)
        n += sum(u.cargo.get(item, 0) for u in self.units.values())
        if item == "scrap":
            n += sum(d.value for d in self.debris.values())
        return n

    def accept_contract(self, contract_id):
        return self.contracts.accept(self, contract_id)

    def order_supply(self, index):
        return self.orbit.order(self, index)

    def orbital_scan(self, x, y):
        return self.orbit.scan(self, x, y)

    def tick(self):
        if self.outcome is not None:
            return
        self.tick_count += 1
        # Power.
        if self.dirty_power:
            self.power_grids = power.compute(list(self.structures.values()))
            self.dirty_power = False
        self._refresh_chargers()
        # Production.
        done = self.research.tick()
        if done:
            self.event(f"RESEARCH COMPLETE: {RESEARCH[done]['name'].upper()}")
            self.charger_key = None  # battery upgrades change debris range
        for s in list(self.structures.values()):
            if s.built and s.kind == "rover_bay":
                structures.update_bay(self, s)
            elif s.built and s.kind == "scanner":
                structures.update_scanner(self, s)
            elif s.built:
                production.update(self, s)
        feeds.update(self)
        self.orbit.update(self)
        # Environment and units.
        debris.update(self)
        for unit in list(self.units.values()):
            units.update(self, unit)
        if self.tick_count % (W.TRACK_FADE_EVERY_S * W.TICK_RATE) == 0:
            self.tracks.fade()
        # Contracts last, as in the design's tick order.
        self.contracts.update(self)
        if self.tick_count % (W.STORAGE_CHECK_S * W.TICK_RATE) == 0:
            self._check_storage()

    def digest(self):
        """Compact full-state snapshot for determinism checks."""
        return (
            self.tick_count, self.credits, self.scrap_spawned, self.scrap_sold, self.next_id,
            tuple(sorted(self.consumed.items())),
            tuple((s.id, s.kind, s.x, s.y, s.built, s.work_done_s, s.powered, s.deconstruct, s.teardown_s,
                   tuple(sorted(s.storage.items())))
                  for s in self.structures.values()),
            tuple((d.id, d.x, d.y, d.kind, d.claimed_by, d.seen) for d in self.debris.values()),
            tuple((u.id, u.kind, u.x, u.y, u.battery, u.state, u.activity, tuple(sorted(u.cargo.items())), u.target)
                  for u in self.units.values()),
            bytes(self.survey.levels), tuple(sorted(self.research.done)), self.rng.getstate(),
            tuple((s.id, tuple(sorted(s.inputs.items())), tuple(sorted(s.outputs.items())), s.cycle_left_s)
                  for s in self.structures.values()),
            tuple((c.id, c.good, c.qty, c.delivered) for c in self.contracts.open),
            tuple((c.id, c.good, c.qty) for c in self.contracts.offers),
            round(self.contracts.reputation, 6), self.outcome,
        )


def _place_lander(grid):
    """Cheapest open node near the centre whose reachable area is large enough."""
    n = grid.n
    centre = (n - 1) / 2
    radius = W.LANDER_SEARCH_RADIUS_FRACTION * n
    candidates = []
    for node, is_open in enumerate(grid.open):
        if not is_open:
            continue
        ny, nx = divmod(node, n)
        d = math.hypot(nx - centre, ny - centre)
        if d <= radius:
            candidates.append((grid.cost[node] + W.LANDER_CENTRE_PENALTY * d, node))
    candidates.sort()
    open_count = sum(grid.open)
    for _, node in candidates:
        field_ = grid.field(node)
        reached = sum(1 for d in field_.dist if d < math.inf)
        if reached >= W.LANDER_MIN_REACH_FRACTION * open_count:
            return node, field_
    node = candidates[0][1]
    return node, grid.field(node)


def build_world(seed, heightmap, mode=CT.DEFAULT_MODE):
    """Generator: yields progress in [0, 1], returns a ready World."""
    slopes = heightmap.cell_slopes()
    yield 0.15
    grid = PathGrid(heightmap.size, slopes)
    yield 0.3
    light = illumination(heightmap, W)
    yield 0.45
    world = World(seed, heightmap, slopes, grid, light, mode)

    node, home = _place_lander(grid)
    lx, ly = grid.node_centre(node)
    lander = structures.Structure(world.new_id(), "lander", lx, ly)
    lander.output_kw = STRUCTURES["lander"]["power_kw"]
    lander.storage = dict(W.START_STORAGE)
    world.structures[lander.id] = lander
    world.lander = lander
    world.home_field = home
    structures.make_docks(lander, world)
    yield 0.55

    world.fields = fields.generate(world, world.rng)
    yield 0.65
    world.spawn_map = debris.SpawnMap(heightmap, slopes, grid)
    yield 0.85
    world.power_grids = power.compute(list(world.structures.values()))
    world.dirty_power = False
    world._refresh_chargers()
    lvl1, lvl2 = W.LANDING_SURVEY_RADIUS_CELLS
    world.survey_area(lx, ly, lvl1, 1)
    world.survey_area(lx, ly, lvl2, 2)
    world.events.clear()
    for _ in range(W.DEBRIS_INITIAL):
        debris.try_spawn(world)

    slot = 0
    for kind in ("scavenger", "constructor"):
        spec = U.UNITS[kind]
        for i in range(spec["start_count"]):
            x, y = lander.docks[slot]
            u = world.spawn_unit(kind, x, y)
            u.dock, u.slot, u.docked = lander.id, slot, True
            lander.dock_users[slot] = u.id
            u.timer = round((i + 1) * spec["launch_stagger_s"] * W.TICK_RATE) + slot
            slot += 1
    world.event("TOUCHDOWN. SCAVENGERS DEPLOYED")
    yield 1.0
    return world
