"""World: terrain, structures, units, debris, credits, and the fixed-step tick.

Tick order follows the design: power -> production -> job board -> units ->
wear -> contracts. Milestone 2 has debris spawning (environment) and units.
"""

import math
import random
from dataclasses import dataclass, field

from game.content import items as I
from game.content import units as U
from game.content import world as W
from game.content.structures import STRUCTURES
from game.sim import debris, units
from game.sim.pathing import PathGrid


@dataclass(slots=True)
class Structure:
    id: int
    kind: str
    x: float
    y: float
    storage: dict = field(default_factory=dict)  # item -> count
    docks: list = field(default_factory=list)     # dock points (x, y)
    dock_users: list = field(default_factory=list)  # unit id or None per dock

    @property
    def spec(self):
        return STRUCTURES[self.kind]

    def stored(self):
        return sum(self.storage.values())


class World:
    def __init__(self, seed, heightmap, slopes, grid):
        self.seed = seed
        self.rng = random.Random(f"{seed}/world")
        self.heightmap = heightmap
        self.slopes = slopes
        self.grid = grid
        self.tick_count = 0
        self.next_id = 1
        self.structures = {}
        self.units = {}
        self.debris = {}
        self.credits = 0
        self.scrap_spawned = 0
        self.scrap_sold = 0
        self.debris_timer = round(W.DEBRIS_SPAWN_INTERVAL_S * W.TICK_RATE)
        self.lander = None
        self.home_field = None
        self.debris_weights = None

    def new_id(self):
        uid = self.next_id
        self.next_id += 1
        return uid

    # Commands (applied between ticks) ----------------------------------------

    def sell_scrap(self, amount):
        """Sell up to amount scrap from the lander. Returns how many were sold."""
        n = min(amount, self.lander.storage.get("scrap", 0))
        if n > 0:
            self.lander.storage["scrap"] -= n
            self.credits += n * I.ITEMS["scrap"]["sell_price"]
            self.scrap_sold += n
        return n

    # Helpers -------------------------------------------------------------------

    def lander_store(self, item, amount):
        """Move up to amount items into lander storage. Returns how many fit."""
        n = max(0, min(amount, self.lander.spec["storage"] - self.lander.stored()))
        if n:
            self.lander.storage[item] = self.lander.storage.get(item, 0) + n
        return n

    def scrap_accounted(self):
        """Every scrap ever spawned, wherever it is now (for conservation checks)."""
        return (sum(d.value for d in self.debris.values())
                + sum(u.cargo for u in self.units.values())
                + self.lander.storage.get("scrap", 0)
                + self.scrap_sold)

    def time_s(self):
        return self.tick_count / W.TICK_RATE

    # Tick ------------------------------------------------------------------------

    def tick(self):
        self.tick_count += 1
        debris.update(self)
        for unit in self.units.values():
            units.update(self, unit)

    def digest(self):
        """Compact full-state snapshot for determinism checks."""
        return (
            self.tick_count, self.credits, self.scrap_spawned, self.scrap_sold, self.next_id,
            tuple(sorted(self.lander.storage.items())),
            tuple((d.id, d.x, d.y, d.kind, d.claimed_by) for d in self.debris.values()),
            tuple((u.id, u.x, u.y, u.battery, u.state, u.cargo, u.target, u.slot)
                  for u in self.units.values()),
            self.rng.getstate(),
        )


def _place_lander(grid, size):
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


def build_world(seed, heightmap):
    """Generator: yields progress in [0, 1], returns a ready World."""
    slopes = heightmap.cell_slopes()
    yield 0.25
    grid = PathGrid(heightmap.size, slopes)
    yield 0.5
    world = World(seed, heightmap, slopes, grid)

    node, home = _place_lander(grid, heightmap.size)
    lx, ly = grid.node_centre(node)
    spec = STRUCTURES["lander"]
    lander = Structure(world.new_id(), "lander", lx, ly)
    for k in range(spec["charge_slots"]):
        a = math.pi / 4 + k * 2 * math.pi / spec["charge_slots"]
        r = spec["dock_radius_cells"]
        lander.docks.append((lx + r * math.cos(a), ly + r * math.sin(a)))
        lander.dock_users.append(None)
    world.structures[lander.id] = lander
    world.lander = lander
    world.home_field = home
    yield 0.6

    scav = U.UNITS["scavenger"]
    usable = (1.0 - U.LOW_BATTERY_FRACTION) * scav["battery"] - scav["pickup_energy"]
    max_round_trip = usable / (scav["drain_per_cost_cell"] * U.TRIP_SAFETY_FACTOR)
    world.debris_weights = debris.spawn_weights(heightmap, slopes, grid, home, (lx, ly), max_round_trip)
    yield 0.9
    for _ in range(W.DEBRIS_INITIAL):
        debris.try_spawn(world)

    for i in range(scav["start_count"]):
        uid = world.new_id()
        stagger = round((i + 1) * scav["launch_stagger_s"] * W.TICK_RATE)
        world.units[uid] = units.make_scavenger(world, uid, lander, i, stagger)
    yield 1.0
    return world
