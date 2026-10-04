"""Unit state machines, battery and movement. Never imports pygame.

Scavenger loop: pick the nearest unclaimed debris it can reach and still get
home from with battery to spare, drive there, pick it up, repeat until the
cargo is full or nothing is in range, then dock at the lander to unload and
charge. Below the low-battery threshold it drops its job and heads to dock.
"""

import math
from collections import deque
from dataclasses import dataclass, field

from game.content import units as U
from game.content import world as W
from game.content.structures import STRUCTURES

# States.
IDLE = "idle"
TO_DEBRIS = "to_debris"
PICKUP = "pickup"
TO_DOCK = "to_dock"
UNLOAD = "unload"
CHARGING = "charging"
STRANDED = "stranded"


@dataclass(slots=True)
class Unit:
    id: int
    kind: str
    x: float
    y: float
    battery: float
    state: str = IDLE
    cargo: int = 0
    target: int | None = None        # debris id
    path: list = field(default_factory=list)
    timer: int = 0                   # ticks left in the current timed state
    dock: int | None = None          # structure id when holding a dock slot
    slot: int = -1
    docked: bool = False             # at the dock point
    prev_x: float = 0.0
    prev_y: float = 0.0
    heading: float = 0.0             # radians, last direction of travel
    collected: int = 0
    trail: deque = field(default_factory=lambda: deque(maxlen=U.TRAIL_POINTS))

    @property
    def spec(self):
        return U.UNITS[self.kind]


def _ticks(seconds):
    return max(1, round(seconds * W.TICK_RATE))


def make_scavenger(world, uid, lander, slot, stagger_ticks):
    spec = U.UNITS["scavenger"]
    x, y = lander.docks[slot]
    unit = Unit(uid, "scavenger", x, y, spec["battery"], prev_x=x, prev_y=y,
                dock=lander.id, slot=slot, docked=True, timer=stagger_ticks)
    lander.dock_users[slot] = uid
    return unit


# Docking --------------------------------------------------------------------

def _release_dock(world, unit):
    if unit.dock is not None:
        world.structures[unit.dock].dock_users[unit.slot] = None
    unit.dock, unit.slot, unit.docked = None, -1, False


def _go_dock(world, unit):
    """Reserve a dock slot at the lander and path to it (or to its centre if all are busy)."""
    lander = world.lander
    if unit.dock is None:
        for slot, user in enumerate(lander.dock_users):
            if user is None:
                lander.dock_users[slot] = unit.id
                unit.dock, unit.slot = lander.id, slot
                break
    goal = lander.docks[unit.slot] if unit.dock is not None else (lander.x, lander.y)
    home = world.home_field
    node = world.grid.nearest_reachable(world.grid.node_at(unit.x, unit.y), home)
    chain = home.nodes_from_source(node)[::-1]
    unit.path = world.grid.waypoints((unit.x, unit.y), chain, goal)
    unit.docked = False
    unit.state = TO_DOCK


# Decisions -------------------------------------------------------------------

def _choose_debris(world, unit):
    """Nearest unclaimed debris (by travel cost) that leaves enough battery to get home."""
    spec = unit.spec
    grid = world.grid
    here = grid.nearest_reachable(grid.node_at(unit.x, unit.y), world.home_field)
    out = grid.field(here)
    home = world.home_field
    reserve = U.LOW_BATTERY_FRACTION * spec["battery"]
    best, best_cost = None, None
    for piece in world.debris.values():
        if piece.claimed_by is not None:
            continue
        node = grid.node_at(piece.x, piece.y)
        travel = out.dist[node]
        back = home.dist[node]
        need = (travel + back) * spec["drain_per_cost_cell"] * U.TRIP_SAFETY_FACTOR + spec["pickup_energy"]
        if unit.battery - need < reserve:
            continue
        if best is None or travel < best_cost:
            best, best_cost = piece, travel
    if best is None:
        return None
    chain = out.nodes_from_source(grid.node_at(best.x, best.y))
    return best, grid.waypoints((unit.x, unit.y), chain, (best.x, best.y))


def think(world, unit):
    """Pick the next activity. Called whenever a unit finishes what it was doing."""
    spec = unit.spec
    if unit.docked:
        if unit.cargo:
            unit.state, unit.timer = UNLOAD, _ticks(spec["unload_s"])
            return
        if unit.battery < U.TOP_UP_BELOW_FRACTION * spec["battery"]:
            unit.state = CHARGING
            return
    if unit.cargo < spec["cargo"]:
        choice = _choose_debris(world, unit)
        if choice is not None:
            piece, path = choice
            piece.claimed_by = unit.id
            unit.target, unit.path = piece.id, path
            _release_dock(world, unit)
            unit.state = TO_DEBRIS
            return
    if not unit.docked:
        _go_dock(world, unit)
    elif unit.battery < spec["battery"]:
        unit.state = CHARGING
    else:
        unit.state, unit.timer = IDLE, _ticks(U.IDLE_RETHINK_S)


# Per-tick update ---------------------------------------------------------------

def _move(world, unit):
    """Advance along the path. Returns True when the path is finished."""
    spec = unit.spec
    dt = 1.0 / W.TICK_RATE
    size = world.heightmap.size
    cx = min(max(int(unit.x + 0.5), 0), size - 1)
    cy = min(max(int(unit.y + 0.5), 0), size - 1)
    slope = world.slopes[cy * size + cx]
    factor = 1.0 + slope / U.SLOPE_DIVISOR_DEG
    remaining = spec["base_speed_cells_per_s"] * dt / factor
    while remaining > 0.0 and unit.path:
        tx, ty = unit.path[0]
        dx, dy = tx - unit.x, ty - unit.y
        dist = (dx * dx + dy * dy) ** 0.5
        if dist > 0.0:
            unit.heading = math.atan2(dy, dx)
        if dist <= remaining:
            unit.x, unit.y = tx, ty
            unit.path.pop(0)
            remaining -= dist
        else:
            unit.x += dx / dist * remaining
            unit.y += dy / dist * remaining
            remaining = 0.0
    # Battery drain is per cost-cell travelled, which is constant per tick of driving.
    used = spec["base_speed_cells_per_s"] * dt - remaining * factor
    unit.battery = max(0.0, unit.battery - used * spec["drain_per_cost_cell"])
    return not unit.path


def update(world, unit):
    unit.prev_x, unit.prev_y = unit.x, unit.y
    spec = unit.spec
    state = unit.state

    if state == STRANDED:
        pass
    elif state in (TO_DEBRIS, TO_DOCK):
        arrived = _move(world, unit)
        if unit.battery <= 0.0:
            _drop_job(world, unit)
            unit.state = STRANDED
        elif state == TO_DEBRIS and unit.battery < U.LOW_BATTERY_FRACTION * spec["battery"]:
            _drop_job(world, unit)
            _go_dock(world, unit)
        elif arrived and state == TO_DEBRIS:
            unit.state, unit.timer = PICKUP, _ticks(spec["pickup_s"])
        elif arrived:
            if unit.dock is None:
                _go_dock(world, unit)  # was waiting for a free slot
                if unit.dock is None:
                    unit.state, unit.timer = IDLE, _ticks(U.IDLE_RETHINK_S)
            else:
                unit.docked = True
                think(world, unit)
    elif state == PICKUP:
        unit.timer -= 1
        if unit.timer <= 0:
            piece = world.debris.pop(unit.target, None)
            unit.target = None
            if piece is not None:
                unit.cargo += piece.value
                unit.collected += piece.value
                unit.battery = max(0.0, unit.battery - spec["pickup_energy"])
            think(world, unit)
    elif state == UNLOAD:
        unit.timer -= 1
        if unit.timer <= 0:
            moved = world.lander_store("scrap", unit.cargo)
            unit.cargo -= moved
            if unit.cargo:
                unit.timer = _ticks(spec["unload_s"])  # storage full: wait and retry
            else:
                think(world, unit)
    elif state == CHARGING:
        dock = world.structures[unit.dock]
        rate = STRUCTURES[dock.kind]["charge_per_s"] / W.TICK_RATE
        unit.battery = min(spec["battery"], unit.battery + rate)
        if unit.battery >= spec["battery"]:
            think(world, unit)
    elif state == IDLE:
        unit.timer -= 1
        if unit.timer <= 0:
            think(world, unit)

    unit.trail.append((unit.x, unit.y))


def _drop_job(world, unit):
    """Return the claimed debris to the pool."""
    if unit.target is not None:
        piece = world.debris.get(unit.target)
        if piece is not None and piece.claimed_by == unit.id:
            piece.claimed_by = None
        unit.target = None
    unit.path = []
