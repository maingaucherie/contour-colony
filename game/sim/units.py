"""Shared unit machinery: movement, wandering, battery, docking, orders.

Each unit kind has a brain module (scavenger, constructor, surveyor, hauler) with:
  think(world, unit)        choose the next activity
  arrived(world, unit)      a MOVING unit reached the end of its path
  work_done(world, unit)    a WORKING unit's timer ran out
  work_tick(world, unit)    optional, every tick while WORKING
  on_move(world, unit)      optional, every tick while MOVING
  drop_job(world, unit)     release claims (low battery, new orders)
Never imports pygame.
"""

import math
from collections import deque
from dataclasses import dataclass, field

from game.content import units as U
from game.content import world as W
from game.content.structures import STRUCTURES

# Core states. What a unit is doing within a state is its `activity`.
IDLE = "idle"
MOVING = "moving"
WORKING = "working"
CHARGING = "charging"
STRANDED = "stranded"


@dataclass(slots=True)
class Unit:
    id: int
    kind: str
    x: float                         # position on the planned path
    y: float
    battery: float
    state: str = IDLE
    activity: str = "idle"
    cargo: dict = field(default_factory=dict)
    target: int | None = None        # debris, structure or site id the activity is about
    job: int | None = None           # constructor: the site it is supplying
    haul: tuple | None = None        # hauler: (source id, dest id, item, amount)
    survey_at: tuple | None = None   # survey rover: the field spot it's going to survey
    order: tuple | None = None       # direct order: ("move" | "survey", x, y)
    zone: tuple | None = None        # scraper: centre of the area it sweeps
    lane: int = 0                    # scraper: next pass to sweep
    scraped: float = 0.0             # scraper: cells scraped toward the next load
    pass_end: tuple | None = None    # scraper: where the current pass ends
    blade_odo: float = 0.0           # scraper: odometer when last counted
    blade_cell: int = -1             # scraper: cell last scraped
    zone_check: int = -10 ** 9       # scraper: tick it last looked for new ground
    zone_ordered: bool = False       # scraper: the player chose its zone (it stays, however crowded)
    path: list = field(default_factory=list)
    path_left: float = 0.0           # cells of path still to drive
    odometer: float = 0.0            # cells driven on the current path
    timer: int = 0
    dock: int | None = None          # structure id when holding a dock slot
    slot: int = -1
    docked: bool = False
    heading: float = 0.0             # radians, along the planned path
    # Visual position: the planned position plus a sideways wander.
    vx: float = 0.0
    vy: float = 0.0
    prev_vx: float = 0.0
    prev_vy: float = 0.0
    side_x: float = 0.0
    side_y: float = 1.0
    vis_heading: float = 0.0
    wobble_amp: float = 0.3
    wobble_len: float = 3.0
    wobble_phase: float = 0.0
    collected: int = 0
    trail: deque = field(default_factory=lambda: deque(maxlen=U.TRAIL_POINTS))

    @property
    def spec(self):
        return U.UNITS[self.kind]

    def cargo_total(self):
        return sum(self.cargo.values())


def ticks(seconds):
    return max(1, round(seconds * W.TICK_RATE))


def make_unit(world, uid, kind, x, y):
    rng = world.rng
    u = Unit(uid, kind, x, y, world.battery_capacity(kind), vx=x, vy=y, prev_vx=x, prev_vy=y,
             wobble_amp=rng.uniform(*U.WOBBLE_AMPLITUDE_CELLS),
             wobble_len=rng.uniform(*U.WOBBLE_WAVELENGTH_CELLS),
             wobble_phase=rng.uniform(0.0, 2 * math.pi))
    return u


def brain(unit):
    from game.sim import constructor, drone, hauler, scavenger, scraper, surveyor
    return {"scavenger": scavenger, "constructor": constructor, "survey_rover": surveyor,
            "hauler": hauler, "maintenance_drone": drone, "scraper": scraper,
            "construction_drone": constructor, "harvester": scraper}[unit.kind]


def flies(unit):
    return unit.spec.get("flies", False)


def fly_cost(unit, x, y):
    """Cost-cells for a flyer: straight distance."""
    return math.hypot(x - unit.x, y - unit.y)


# Battery and planning ---------------------------------------------------------

def capacity(world, unit):
    return world.battery_capacity(unit.kind)


def reserve(world, unit):
    return U.LOW_BATTERY_FRACTION * capacity(world, unit)


def trip_energy(unit, cost_cells, work_energy=0.0):
    return cost_cells * unit.spec["drain_per_cost_cell"] * U.TRIP_SAFETY_FACTOR + work_energy


def can_afford(world, unit, cost_cells, work_energy=0.0):
    """Enough battery for a trip of cost_cells (that already includes getting back to a charger)."""
    return unit.battery - trip_energy(unit, cost_cells, work_energy) >= reserve(world, unit)


def range_limit(world, unit):
    """Cost-cells a full battery covers, with a margin: as far as a rover's own field needs to search."""
    return round(capacity(world, unit) / unit.spec["drain_per_cost_cell"] * U.FIELD_RANGE_MARGIN)


class FlightField:
    """Distances for a flyer: straight lines from (x, y), over everything.
    Looks like a route field (dist[node], reachable), so brains written for
    rovers work for flyers too."""

    class _Straight:
        def __init__(self, grid, x, y):
            self.grid, self.x, self.y = grid, x, y

        def __getitem__(self, node):
            cx, cy = self.grid.node_centre(node)
            return math.hypot(cx - self.x, cy - self.y)

    def __init__(self, grid, x, y):
        self.source = grid.node_at(x, y)
        self.dist = FlightField._Straight(grid, x, y)

    def reachable(self, node):
        return True


def field_from(world, unit, x, y):
    """Distances from (x, y) as this unit travels: by ground, or flying."""
    grid = world.grid
    if flies(unit):
        return FlightField(grid, x, y)
    return grid.field(grid.nearest_reachable(grid.node_at(x, y), world.home_field), range_limit(world, unit))


def back_cost_for(world, unit, x, y):
    """Cost-cells from (x, y) back to a charger this unit can use."""
    if flies(unit):
        homes = [s for s in world.chargers() if s.kind in unit.spec["docks_at"]]
        return min((math.hypot(s.x - x, s.y - y) for s in homes), default=math.inf)
    return back_cost(world, x, y)


def here_field(world, unit):
    grid = world.grid
    if flies(unit):
        return FlightField(grid, unit.x, unit.y)
    start = grid.nearest_reachable(grid.node_at(unit.x, unit.y), world.home_field)
    return grid.field(start, range_limit(world, unit))


def back_cost(world, x, y):
    """Cost-cells from (x, y) to the nearest working charger. A spot on a
    blocked node (beside a cliff) counts from the drivable node next to it."""
    grid, cf = world.grid, world.charge_field
    node = grid.node_at(x, y)
    if cf.reachable(node):
        return cf.dist[node]
    near = grid.nearest_reachable(node, cf)
    return cf.dist[near] + grid.node_cells if near != cf.source or cf.reachable(near) else math.inf


def path_to(world, unit, goal, from_field=None):
    """Waypoints from the unit to goal, or None if unreachable. The path bends
    around structures, except any whose footprint the start or goal is near
    (the one being visited, or the one the unit is leaving)."""
    if flies(unit):
        return [goal]  # straight over everything
    grid = world.grid
    f = from_field or here_field(world, unit)
    node = grid.node_at(*goal)
    if not f.reachable(node):
        # A goal just off drivable ground (a dock beside a cliff): route to the
        # drivable node next to it, then the short last step.
        near = grid.nearest_reachable(node, f)
        if near == node or not f.reachable(near) or near == f.source and node not in dict(grid.neighbours(near)):
            return None
        node = near
    points = grid.waypoints((unit.x, unit.y), f.nodes_from_source(node), goal)
    return avoid_structures(world, (unit.x, unit.y), points)


def _seg_point_dist(ax, ay, bx, by, px, py):
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    t = 0.0 if l2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / l2))
    cx, cy = ax + t * dx, ay + t * dy
    return math.hypot(px - cx, py - cy), t


def avoid_structures(world, start, points):
    """Insert detour waypoints so path segments clear structure footprints."""
    obstacles = []
    gx, gy = points[-1] if points else start
    for s in world.structures.values():
        if s.is_line():
            continue  # rovers drive over conveyors
        r = s.spec["footprint_cells"] + U.STRUCTURE_CLEARANCE_CELLS
        reach = r + s.spec.get("dock_radius_cells", 0.0)
        if math.hypot(gx - s.x, gy - s.y) <= reach or math.hypot(start[0] - s.x, start[1] - s.y) <= reach:
            continue  # visiting or leaving it
        obstacles.append((s.x, s.y, r))
    if not obstacles:
        return points
    out = []
    ax, ay = start
    for bx, by in points:
        for _ in range(3):  # a segment may need more than one detour
            hit = None
            for ox, oy, r in obstacles:
                d, t = _seg_point_dist(ax, ay, bx, by, ox, oy)
                if d < r and 0.0 < t < 1.0 and (hit is None or t < hit[3]):
                    hit = (ox, oy, r, t)
            if hit is None:
                break
            ox, oy, r, t = hit
            cx, cy = ax + (bx - ax) * t, ay + (by - ay) * t
            nx, ny = cx - ox, cy - oy
            n = math.hypot(nx, ny)
            if n < 1e-6:  # dead centre: go around on the left
                nx, ny, n = -(by - ay), bx - ax, math.hypot(bx - ax, by - ay) or 1.0
            wx, wy = ox + nx / n * (r + 0.3), oy + ny / n * (r + 0.3)
            if not world.grid.open[world.grid.node_at(wx, wy)]:
                wx, wy = ox - nx / n * (r + 0.3), oy - ny / n * (r + 0.3)  # other side
            out.append((wx, wy))
            ax, ay = wx, wy
        out.append((bx, by))
        ax, ay = bx, by
    return out


def set_path(unit, path, activity, target=None):
    unit.path = path
    unit.path_left = 0.0
    px, py = unit.x, unit.y
    for x, y in path:
        unit.path_left += math.hypot(x - px, y - py)
        px, py = x, y
    unit.odometer = 0.0
    unit.state, unit.activity, unit.target = MOVING, activity, target


def work(unit, activity, seconds):
    unit.state, unit.activity, unit.timer = WORKING, activity, ticks(seconds)


def idle(unit, activity="idle"):
    unit.state, unit.activity, unit.timer = IDLE, activity, ticks(U.IDLE_RETHINK_S)


# Docking ----------------------------------------------------------------------

def release_dock(world, unit):
    if unit.dock is not None and unit.dock in world.structures:
        s = world.structures[unit.dock]
        if unit.slot < len(s.dock_users) and s.dock_users[unit.slot] == unit.id:
            s.dock_users[unit.slot] = None
    unit.dock, unit.slot, unit.docked = None, -1, False


def dock_roles(world, unit):
    if not unit.docked or unit.dock not in world.structures:
        return set()
    s = world.structures[unit.dock]
    roles = set()
    if s.charges():
        roles.add("charge")
    if s.stores():
        roles.add("store")
    return roles


def go_dock(world, unit, role, only=None):
    """Head for the nearest structure that can charge / store (or for `only`),
    reserving a dock slot if one is free (otherwise drive to it and wait).
    Never a charger the battery can't reach while one it can is around; a
    busy one counts as a little further away, since waiting in line beats a
    long drive. False if none reachable."""
    flyer = flies(unit)
    f = None if flyer else here_field(world, unit)
    grid = world.grid
    best = None
    for s in ([only] if only is not None else world.structures.values()):
        if flyer and only is None and s.kind not in unit.spec.get("docks_at", ()):
            continue
        if role == "charge" and not (s.charges() and (s.powered or s is world.lander)):
            continue
        # Scrap can always be unloaded: what doesn't fit is sold.
        only_scrap = set(unit.cargo) <= {"scrap"}
        if role == "store" and not (s.stores() and (s.stored() < s.spec["storage"] or only_scrap)
                                    and all(s.accepts(k) for k in unit.cargo)):
            continue
        d = fly_cost(unit, s.x, s.y) if flyer else f.dist[grid.node_at(s.x, s.y)]
        if d == math.inf:
            continue
        free = None in s.dock_users or (unit.dock == s.id)
        reachable = trip_energy(unit, d) <= unit.battery
        cost = d
        if role == "charge" and s.stores() and not unit.cargo_total():
            cost += U.PARK_AWAY_FROM_STORAGE_COST  # leave storage docks to units with cargo
        if not free:
            cost += U.BUSY_DOCK_COST
        key = (not reachable, cost)
        if best is None or key < best[0]:
            best = (key, s)
    if best is None:
        return False
    s = best[1]
    if unit.dock != s.id:
        release_dock(world, unit)
        if None in s.dock_users:
            slot = s.dock_users.index(None)
            s.dock_users[slot] = unit.id
            unit.dock, unit.slot = s.id, slot
    goal = s.docks[unit.slot] if unit.dock == s.id else (s.x, s.y)
    path = path_to(world, unit, goal, f) or [goal]
    set_path(unit, path, "to_charge" if role == "charge" else "to_store", s.id)
    unit.docked = False
    return True


def try_charge(world, unit, below_fraction=U.TOP_UP_BELOW_FRACTION):
    """If docked at a charger and below the threshold, start charging."""
    if "charge" in dock_roles(world, unit) and unit.battery < below_fraction * capacity(world, unit):
        unit.state, unit.activity = CHARGING, "charging"
        return True
    return False


def relay(world, unit, x, y, rest_cost=0.0, work_energy=0.0, start=None, battery=None):
    """The next charger to top up at, for a trip to (x, y) (then rest_cost more
    cost-cells and work_energy) that is out of range from here but in range
    on a full battery from the charger nearest the destination. Hops from
    charger to charger when that one is out of reach too. None if there's no
    way. start/battery plan from somewhere else (e.g. after loading cargo).
    Flyers don't relay: they go straight, or not at all."""
    if flies(unit):
        return None
    grid = world.grid
    cf = world.charge_field
    node = grid.node_at(x, y)
    if cf.dist[node] == math.inf:
        return None
    usable = U.RELAY_PLANNING_FRACTION * capacity(world, unit) - reserve(world, unit)
    if trip_energy(unit, cf.dist[node] + rest_cost, work_energy) > usable:
        return None
    goal_node = cf.nodes_from_source(node)[0]
    chargers = sorted(world.chargers(), key=lambda s: s.id)
    if not any(grid.node_at(s.x, s.y) == goal_node for s in chargers):
        return None
    sx, sy = start if start is not None else (unit.x, unit.y)
    battery = unit.battery if battery is None else battery
    here = grid.field(grid.nearest_reachable(grid.node_at(sx, sy), world.home_field), range_limit(world, unit))

    def reachable_now(s):
        if start is None and unit.docked and unit.dock == s.id:
            return True
        return battery - trip_energy(unit, here.dist[grid.node_at(s.x, s.y)]) >= reserve(world, unit)

    # Breadth-first over chargers a full battery can get between.
    first = {s.id: s for s in chargers if reachable_now(s)}
    frontier = sorted(first.values(), key=lambda s: here.dist[grid.node_at(s.x, s.y)])
    seen = set(first)
    while frontier:
        nxt = []
        for s in frontier:
            if grid.node_at(s.x, s.y) == goal_node:
                return first[s.id]
            hop = grid.field(grid.node_at(s.x, s.y))
            for t in chargers:
                if t.id not in seen and trip_energy(unit, hop.dist[grid.node_at(t.x, t.y)]) <= usable:
                    seen.add(t.id)
                    first[t.id] = first[s.id]
                    nxt.append(t)
        frontier = nxt
    return None


def in_charger_range(world, unit, x, y):
    """Can a unit on a full battery get from the nearest charger to (x, y) and back?"""
    d = world.charge_field.dist[world.grid.node_at(x, y)]
    usable = U.RELAY_PLANNING_FRACTION * capacity(world, unit) - reserve(world, unit)
    return d < math.inf and trip_energy(unit, 2 * d) <= usable


def stage(world, unit, s):
    """Go and charge to full at charger s (already there: start charging).
    False if that can't help: already there on a full battery."""
    if unit.docked and unit.dock == s.id:
        if unit.battery >= capacity(world, unit) - 1e-6:
            return False
        unit.state, unit.activity = CHARGING, "charging"
        return True
    return go_dock(world, unit, "charge", only=s)


def head_home(world, unit):
    """Nothing to do: charge up if needed, otherwise park.

    Being docked somewhere that can't charge (a depot) doesn't count as home."""
    if try_charge(world, unit, 1.0):
        return
    roles = dock_roles(world, unit)
    at_charger = "charge" in roles
    if unit.battery < U.TOP_UP_IDLE_FRACTION * capacity(world, unit) and not at_charger \
            and go_dock(world, unit, "charge"):
        return
    # Parked empty at a storage dock (the lander): move to a free charging pad
    # nearby if there is one, so units bringing cargo can unload.
    if "store" in roles and not unit.cargo_total() and not flies(unit) and _free_pad_near(world, unit):
        go_dock(world, unit, "charge")
        return
    # Charged and nothing to do: give the dock slot back and wait beside it.
    if unit.docked and unit.dock in world.structures and not unit.cargo_total() \
            and unit.battery >= capacity(world, unit) - 1e-6:
        s = world.structures[unit.dock]
        dx, dy = unit.x - s.x, unit.y - s.y
        d = math.hypot(dx, dy) or 1.0
        r = d + U.PARK_OFFSET_CELLS
        goal = (s.x + dx / d * r, s.y + dy / d * r)
        release_dock(world, unit)
        set_path(unit, [goal], "to_park")
        return
    idle(unit)


def _free_pad_near(world, unit):
    f = here_field(world, unit)
    for s in world.structures.values():
        if (s.charges() and not s.stores() and s.powered and None in s.dock_users
                and f.dist[world.grid.node_at(s.x, s.y)] <= U.PARK_AWAY_FROM_STORAGE_COST):
            return True
    return False


# Orders -----------------------------------------------------------------------

def give_order(world, unit, kind, x, y):
    """Direct order from the player. Returns (ok, reason)."""
    f = here_field(world, unit)
    node = world.grid.node_at(x, y)
    if not f.reachable(node):
        return False, "OUT OF BATTERY RANGE" if world.home_field.reachable(node) else "UNREACHABLE"
    linger = unit.spec.get("linger_drain_per_s", 0.0) * unit.spec.get("linger_s", 0.0) if kind == "survey" else 0.0
    if not can_afford(world, unit, f.dist[node] + back_cost(world, x, y), linger):
        full = unit.battery >= capacity(world, unit)
        return False, "OUT OF BATTERY RANGE" + ("" if full else " - CHARGE FIRST")
    brain(unit).drop_job(world, unit)
    release_dock(world, unit)
    unit.order = (kind, x, y)
    path = path_to(world, unit, (x, y), f)
    set_path(unit, path, "to_order")
    return True, ""


# Movement -----------------------------------------------------------------------

def _move(world, unit):
    """Advance along the path. Returns True when the path is finished."""
    spec = unit.spec
    dt = 1.0 / W.TICK_RATE
    factor = 1.0 if flies(unit) else world.grid.cell_factor(unit.x, unit.y)
    remaining = spec["base_speed_cells_per_s"] * dt / factor
    if unit.activity == "scraping":
        remaining *= spec["scrape_speed_fraction"]
    moved = 0.0
    while remaining > 0.0 and unit.path:
        tx, ty = unit.path[0]
        dx, dy = tx - unit.x, ty - unit.y
        dist = math.hypot(dx, dy)
        if dist > 0.0:
            unit.heading = math.atan2(dy, dx)
        if dist <= remaining:
            unit.x, unit.y = tx, ty
            unit.path.pop(0)
            remaining -= dist
            moved += dist
        else:
            unit.x += dx / dist * remaining
            unit.y += dy / dist * remaining
            moved += remaining
            remaining = 0.0
    # Battery drain is per cost-cell travelled, which is constant per tick of driving.
    used = spec["base_speed_cells_per_s"] * dt - remaining * factor
    unit.battery = max(0.0, unit.battery - used * spec["drain_per_cost_cell"])
    unit.odometer += moved
    unit.path_left = max(0.0, unit.path_left - moved)
    return not unit.path


def _wander(unit):
    """Drawn position: steer toward the planned position plus a slow, shallow
    weave. The lag rounds corners; at rest it settles onto the planned spot."""
    target_x, target_y = unit.x, unit.y
    if unit.state == MOVING:
        k = U.WOBBLE_TURN_SMOOTHING
        tx, ty = -math.sin(unit.heading), math.cos(unit.heading)
        sx, sy = unit.side_x + (tx - unit.side_x) * k, unit.side_y + (ty - unit.side_y) * k
        n = math.hypot(sx, sy) or 1.0
        unit.side_x, unit.side_y = sx / n, sy / n
        ramp = U.WOBBLE_RAMP_CELLS
        envelope = max(0.0, min(1.0, unit.odometer / ramp, unit.path_left / ramp))
        t = 2 * math.pi * unit.odometer / unit.wobble_len
        sway = math.sin(t + unit.wobble_phase) + U.WOBBLE_SECOND_HARMONIC * math.sin(2.7 * t + 2.1 * unit.wobble_phase)
        off = unit.wobble_amp * sway * envelope
        target_x += unit.side_x * off
        target_y += unit.side_y * off
    f = U.STEER_FOLLOW
    unit.vx += (target_x - unit.vx) * f
    unit.vy += (target_y - unit.vy) * f


def _trickle(world, unit, cap):
    """A stranded unit unfolds its panels and trickle-charges (faster in
    sunlight) until it has enough to crawl back to a charger, then goes."""
    light = world.illumination_at(unit.x, unit.y)
    unit.battery = min(cap, unit.battery + U.STRANDED_TRICKLE_PER_S * light / W.TICK_RATE)
    back = back_cost(world, unit.x, unit.y)
    need = cap if back == math.inf else min(cap, trip_energy(unit, back) + reserve(world, unit))
    if unit.battery >= max(need, U.STRANDED_RESUME_FRACTION * cap):
        unit.state = IDLE
        world.event(f"{unit.spec['name'].upper()} RECHARGED BY SUNLIGHT - HEADING HOME")
        if not go_dock(world, unit, "charge"):
            idle(unit)


def update(world, unit):
    b = brain(unit)
    unit.prev_vx, unit.prev_vy = unit.vx, unit.vy
    state = unit.state
    cap = capacity(world, unit)

    if state == STRANDED:
        _trickle(world, unit, cap)
    elif state == MOVING:
        arrived = _move(world, unit)
        if not flies(unit):
            world.tracks.drive(unit.x, unit.y, unit.heading)
        spotted = world.reveal_debris(unit.x, unit.y, unit.spec.get("sight_cells", 0.0))
        if hasattr(b, "on_move"):
            b.on_move(world, unit)
        if spotted and unit.activity == "searching":
            b.think(world, unit)  # found something: go straight for it
            arrived = False
        if unit.battery <= 0.0:
            b.drop_job(world, unit)
            unit.state, unit.activity, unit.path = STRANDED, "stranded", []
            world.event(f"{unit.spec['name'].upper()} STRANDED - RECHARGING SLOWLY BY SUNLIGHT", "alert")
        elif unit.activity != "to_charge" and unit.battery < U.LOW_BATTERY_FRACTION * cap:
            b.drop_job(world, unit)
            unit.order = None
            if not go_dock(world, unit, "charge"):
                idle(unit)
        elif arrived:
            if unit.activity in ("to_charge", "to_store"):
                s = world.structures.get(unit.target)
                if s is None:
                    b.think(world, unit)
                elif unit.dock != s.id:
                    # Arrived while every slot was taken: try again, else wait.
                    if None in s.dock_users:
                        go_dock(world, unit, "charge" if unit.activity == "to_charge" else "store")
                    else:
                        idle(unit, "waiting for a dock")
                else:
                    unit.docked = True
                    b.think(world, unit)
            elif unit.activity == "to_park":
                idle(unit)
            elif unit.activity == "to_order":
                kind = unit.order[0] if unit.order else "move"
                if kind == "survey" and hasattr(b, "start_linger"):
                    b.start_linger(world, unit)
                else:
                    unit.order = None
                    b.think(world, unit)
            else:
                b.arrived(world, unit)
    elif state == WORKING:
        unit.timer -= 1
        if hasattr(b, "work_tick"):
            b.work_tick(world, unit)
        if unit.state == WORKING and unit.timer <= 0:
            b.work_done(world, unit)
    elif state == CHARGING:
        s = world.structures.get(unit.dock)
        if s is None:  # dismantled under it
            unit.dock, unit.slot, unit.docked = None, -1, False
            b.think(world, unit)
        elif s.powered or s is world.lander:
            unit.battery = min(cap, unit.battery + s.spec["charge_per_s"] / W.TICK_RATE)
        if unit.state == CHARGING and unit.battery >= cap:
            b.think(world, unit)
    elif state == IDLE:
        unit.timer -= 1
        if unit.timer <= 0:
            b.think(world, unit)

    _wander(unit)
    if unit.state == MOVING or unit.trail:
        unit.trail.append((unit.vx, unit.vy))

    dx, dy = unit.vx - unit.prev_vx, unit.vy - unit.prev_vy
    if dx * dx + dy * dy > 1e-6:
        target = math.atan2(dy, dx)
        turn = (target - unit.vis_heading + math.pi) % (2 * math.pi) - math.pi
        unit.vis_heading += turn * U.HEADING_SMOOTHING
