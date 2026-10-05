"""Structures: placement rules, construction sites, docks, rover bays.

Placing a structure creates a construction site. Constructors bring its
build_cost (tracked as delivered and incoming) and then assemble it for
build_time_s. Never imports pygame.
"""

import math
from dataclasses import dataclass, field

from game.content import structures as S
from game.content import units as U
from game.content import world as W
from game.content.structures import STRUCTURES
from game.sim import fields as F


@dataclass(slots=True)
class Structure:
    id: int
    kind: str
    x: float
    y: float
    built: bool = True
    delivered: dict = field(default_factory=dict)   # construction materials on site
    incoming: dict = field(default_factory=dict)    # materials constructors are carrying here
    work_done_s: float = 0.0                        # assembly seconds done
    priority: str = "normal"
    powered: bool = False
    grid: int = -1
    grid_parent: int | None = None
    output_kw: float = 0.0
    storage: dict = field(default_factory=dict)
    docks: list = field(default_factory=list)       # dock points (x, y)
    dock_users: list = field(default_factory=list)  # unit id or None per dock
    queue: list = field(default_factory=list)       # rover bay: unit kinds ordered
    building_unit: str | None = None
    bay_ticks_left: int = 0
    created_tick: int = 0
    sweep_angle: float = 0.0                        # scanner beam direction, radians
    # Production (see production.py) and the job board (see jobs.py).
    inputs: dict = field(default_factory=dict)
    outputs: dict = field(default_factory=dict)
    reserved_in: dict = field(default_factory=dict)   # items haulers are bringing
    reserved_out: dict = field(default_factory=dict)  # items haulers will collect
    cycle_left_s: float = 0.0
    cycles: int = 0
    vented: int = 0
    fed: int = 0                                    # items received by direct feed
    status: str = "idle"
    richness: float = 1.0
    field_id: int | None = None                     # mines: the field they work
    heat: float = 0.0                               # 0..1, structures with a "heat" spec
    clock: float = 1.0                              # recipe speed setting (see CLOCKS)
    wear: float = 0.0                               # 0..1 (see wear.py)
    repairer: int | None = None                     # unit repairing it
    grade_deg: float = 0.0                          # degrees of grading the site needs
    grade_cr: int = 0                               # credits paid for grading (refunded on cancel)
    warm: bool = False                              # getting waste heat from a neighbour
    deconstruct: bool = False                       # marked for a constructor to dismantle
    teardown_s: float = 0.0                         # dismantling seconds done

    @property
    def spec(self):
        return STRUCTURES[self.kind]

    def stored(self):
        return sum(self.storage.values())

    def charges(self):
        return self.built and self.spec.get("charge_slots", 0) > 0

    def stores(self):
        return self.built and self.spec.get("storage", 0) > 0

    def accepts(self, item):
        """Storage that keeps only some items (a hangar keeps parts) says so."""
        allowed = self.spec.get("accepts")
        return allowed is None or item in allowed

    def materials_needed(self):
        """Items still to bring: cost - delivered - incoming (never negative)."""
        cost = self.spec.get("build_cost", {})
        return {k: n - self.delivered.get(k, 0) - self.incoming.get(k, 0)
                for k, n in cost.items() if n - self.delivered.get(k, 0) - self.incoming.get(k, 0) > 0}

    def fully_delivered(self):
        cost = self.spec.get("build_cost", {})
        return all(self.delivered.get(k, 0) >= n for k, n in cost.items())

    def draw_kw(self):
        """Power drawn while working, at this clock speed."""
        return self.spec.get("draw_kw", 0.0) * clock_spec(self.clock)["power"]

    def build_time(self):
        """Assembly seconds, plus grading if the ground needs it."""
        return self.spec.get("build_time_s", 1.0) + grade_seconds(self.spec, self.grade_deg)

    def teardown_progress(self):
        return self.teardown_s / (self.spec.get("build_time_s", 1.0) * S.DECONSTRUCT_TIME_FRACTION)

    def build_progress(self):
        """0..1 over the whole job: materials first (a third), then assembly."""
        if self.built:
            return 1.0
        cost = self.spec.get("build_cost", {})
        total = sum(cost.values()) or 1
        got = sum(min(self.delivered.get(k, 0), n) for k, n in cost.items())
        assembly = self.work_done_s / self.build_time()
        return min(1.0, got / total / 3 + assembly * 2 / 3)


def make_docks(s, world=None):
    """Dock points in a ring around the structure. With the world, each one
    is turned (or pulled in) until it sits on ground rovers can drive to,
    never on a cliff beside the structure."""
    spec = s.spec
    slots = spec.get("charge_slots", 0) or spec.get("dock_slots", 0)
    s.docks, s.dock_users = [], []
    r = spec.get("dock_radius_cells", 0.0)

    def drivable(x, y):
        if world is None:
            return True
        node = world.grid.node_at(x, y)
        return world.grid.open[node] and world.home_field.reachable(node)

    for k in range(slots):
        a0 = math.pi / 4 + k * 2 * math.pi / slots
        spot = (s.x, s.y)  # fallback: the structure's own (always drivable) centre
        for radius in (r, r * 0.6):
            for turn in (0, 1, -1, 2, -2, 3, -3, 4, -4, 5, -5, 6):
                a = a0 + turn * math.pi / 12
                x, y = s.x + radius * math.cos(a), s.y + radius * math.sin(a)
                if drivable(x, y):
                    spot = (x, y)
                    break
            else:
                continue
            break
        s.docks.append(spot)
        s.dock_users.append(None)


def clock_spec(clock):
    for value, spec in S.CLOCKS:
        if abs(value - clock) < 1e-6:
            return spec
    return S.CLOCKS[0][1]


def next_clock(world, s):
    """The clock speed after s's current one that the colony may use."""
    values = [v for v, spec in S.CLOCKS if not spec.get("research") or world.research.effect(spec["research"], False)]
    current = [v for v, _ in S.CLOCKS]
    i = current.index(s.clock) if s.clock in current else 0
    for step in range(1, len(current) + 1):
        v = current[(i + step) % len(current)]
        if v in values:
            return v
    return 1.0


def grade_credits(spec, deg):
    return int(round(S.GRADE_CREDITS_PER_DEG * deg * spec["footprint_cells"] ** 2))


def grade_seconds(spec, deg):
    return S.GRADE_SECONDS_PER_DEG * deg * spec["footprint_cells"] ** 2


def steepest_under(world, x, y, r):
    size = world.heightmap.size
    steepest = 0.0
    for cy in range(int(y - r), int(y + r) + 2):
        for cx in range(int(x - r), int(x + r) + 2):
            if 0 <= cx < size and 0 <= cy < size and math.hypot(cx - x, cy - y) <= r + 0.5:
                steepest = max(steepest, world.slopes[cy * size + cx])
    return steepest


def grading_needed(world, kind, x, y):
    """Degrees of grading the ground under kind at (x, y) would need (0 if none)."""
    spec = STRUCTURES[kind]
    return max(0.0, steepest_under(world, x, y, spec["footprint_cells"]) - spec["max_slope_deg"])


def _snaps(a_kind, ax, ay, b_kind, bx, by):
    """True if two snapping structures sit edge to edge on their lattice (no gap needed)."""
    snap = STRUCTURES[a_kind].get("snap")
    if not snap or a_kind != b_kind:
        return False
    cw, ch = snap["cell"]
    return abs(ax - bx) >= cw - 1e-3 or abs(ay - by) >= ch - 1e-3


def snap_position(world, kind, x, y):
    """Where a snapping structure placed near (x, y) clicks into place: the
    nearest free lattice slot beside one of its kind, else (x, y) unchanged."""
    snap = STRUCTURES[kind].get("snap")
    if not snap:
        return x, y
    cw, ch = snap["cell"]
    best = None
    for o in world.structures.values():
        if o.kind != kind or math.hypot(o.x - x, o.y - y) > S.SNAP_RADIUS_CELLS:
            continue
        for dx, dy in ((cw, 0), (-cw, 0), (0, ch), (0, -ch)):
            px, py = o.x + dx, o.y + dy
            d = math.hypot(px - x, py - y)
            if (best is None or d < best[0]) and check_placement(world, kind, px, py)[0]:
                best = (d, px, py)
    return (best[1], best[2]) if best else (x, y)


def farm_neighbours(world, s):
    snap = s.spec.get("snap")
    if not snap:
        return 0
    cw, ch = snap["cell"]
    n = 0
    for o in world.structures.values():
        if o is not s and o.kind == s.kind and o.built:
            dx, dy = abs(o.x - s.x), abs(o.y - s.y)
            if (abs(dx - cw) < 0.05 and dy < 0.05) or (abs(dy - ch) < 0.05 and dx < 0.05):
                n += 1
    return n


def refresh_output(world):
    """Power output of every generator (solar: sunlight, plus the farm bonus)."""
    for s in world.structures.values():
        if not s.built:
            continue
        if s.kind == "solar":
            bonus = 1.0 + s.spec["snap"]["farm_bonus"] * farm_neighbours(world, s)
            s.output_kw = s.spec["power_kw"] * world.illumination_at(s.x, s.y) * bonus
        else:
            s.output_kw = s.spec.get("power_kw", 0.0)


def check_placement(world, kind, x, y):
    """(ok, reason) for placing kind with its centre at (x, y). Ground a little
    too steep is fine if the colony can pay for grading it."""
    spec = STRUCTURES[kind]
    if not world.research.unlocked(spec.get("unlocked_by")):
        return False, "NOT RESEARCHED"
    size = world.heightmap.size
    r = spec["footprint_cells"]
    if not (r <= x <= size - 1 - r and r <= y <= size - 1 - r):
        return False, "OUTSIDE THE SITE"
    node = world.grid.node_at(x, y)
    if not world.grid.open[node] or not world.home_field.reachable(node):
        return False, "UNREACHABLE FOR ROVERS"
    steepest = steepest_under(world, x, y, r)
    if steepest > S.GRADE_MAX_DEG:
        return False, f"TOO STEEP ({steepest:.1f} DEG, GRADING MAX {S.GRADE_MAX_DEG:.0f})"
    if steepest > spec["max_slope_deg"]:
        cost = grade_credits(spec, steepest - spec["max_slope_deg"])
        if world.credits < cost:
            return False, f"GRADING NEEDS {cost} CR"
    for other in world.structures.values():
        if _snaps(kind, x, y, other.kind, other.x, other.y):
            continue
        if math.hypot(other.x - x, other.y - y) < r + other.spec["footprint_cells"] + S.PLACEMENT_GAP_CELLS:
            return False, "OVERLAPS " + other.spec["name"].upper()
    need = spec.get("requires_field")
    if need:
        f = F.field_at(world.fields, x, y, need)
        if f is None or world.survey.level_at(x, y) < 2:
            return False, f"NEEDS A CONFIRMED {need.upper()} FIELD"
    return True, ""


def place_site(world, kind, x, y):
    ok, reason = check_placement(world, kind, x, y)
    if not ok:
        return None, reason
    s = Structure(world.new_id(), kind, x, y, built=False, created_tick=world.tick_count)
    s.grade_deg = grading_needed(world, kind, x, y)
    if s.grade_deg > 0:
        s.grade_cr = grade_credits(s.spec, s.grade_deg)
        world.credits -= s.grade_cr
    world.structures[s.id] = s
    world.dirty_power = True
    return s, ""


def complete(world, s):
    s.built = True
    for k, n in s.delivered.items():
        world.consumed[k] = world.consumed.get(k, 0) + n
    s.delivered.clear()
    s.incoming.clear()
    need = s.spec.get("requires_field")
    if need:
        f = F.field_at(world.fields, s.x, s.y, need)
        s.richness = f.richness if f else 1.0
        s.field_id = f.id if f else None
    if s.grade_deg > 0:  # grading turned up regolith
        n = int(S.GRADE_REGOLITH_PER_DEG * s.grade_deg * s.spec["footprint_cells"] ** 2)
        if n:
            refund_items(world, {"regolith": n})
            world.produced["regolith"] = world.produced.get("regolith", 0) + n
    make_docks(s, world)
    world.structures_changed()
    world.event(f"{s.spec['name'].upper()} COMPLETE")


def cancel_site(world, s):
    """Remove an unfinished site; delivered materials go back to the lander."""
    for item, n in s.delivered.items():
        world.lander.storage[item] = world.lander.storage.get(item, 0) + n
    world.credits += s.grade_cr
    for unit in world.units.values():
        if unit.target == s.id:
            unit.target = None
    del world.structures[s.id]
    world.dirty_power = True
    world.event(f"{s.spec['name'].upper()} SITE CANCELLED")


def update_bay(world, s):
    """Rover bay: take the next order's cost from storage, then build while powered."""
    if s.building_unit is None:
        if not s.queue:
            return
        cost = U.UNITS[s.queue[0]]["bay_cost"]
        if not world.take_items(cost):
            return
        s.building_unit = s.queue.pop(0)
        s.bay_ticks_left = round(U.UNITS[s.building_unit]["bay_time_s"] * W.TICK_RATE)
    if not s.powered:
        return
    s.bay_ticks_left -= 1
    if s.bay_ticks_left <= 0:
        kind, s.building_unit = s.building_unit, None
        r = s.spec["footprint_cells"] + 0.8
        world.spawn_unit(kind, s.x + r, s.y + r * 0.3)
        world.event(f"{U.UNITS[kind]['name'].upper()} ROLLED OUT")


def refund_items(world, items):
    """Put items into the lander (over capacity if need be: nothing is lost)."""
    for k, n in items.items():
        if n > 0:
            world.lander.storage[k] = world.lander.storage.get(k, 0) + n


def dismantle(world, s):
    """Remove a built structure: part of its cost and all its contents go back to storage."""
    cost = s.spec.get("build_cost", {})
    refund = {k: int(n * S.DECONSTRUCT_REFUND) for k, n in cost.items()}
    for k, n in refund.items():
        world.consumed[k] = world.consumed.get(k, 0) - n
    refund_items(world, refund)
    refund_items(world, s.storage)
    refund_items(world, s.inputs)
    refund_items(world, s.outputs)
    s.storage, s.inputs, s.outputs = {}, {}, {}
    if s.building_unit:  # a rover bay mid-build gives its materials back
        refund_items(world, U.UNITS[s.building_unit]["bay_cost"])
        for k, n in U.UNITS[s.building_unit]["bay_cost"].items():
            world.consumed[k] = world.consumed.get(k, 0) - n
    for unit in world.units.values():
        if unit.dock == s.id:
            unit.dock, unit.slot, unit.docked = None, -1, False
    del world.structures[s.id]
    world.structures_changed()
    world.event(f"{s.spec['name'].upper()} DISMANTLED - " + ", ".join(f"{n} {k.upper()}" for k, n in refund.items())
                + " RETURNED")


def update_scanner(world, s):
    """Advance the radar beam; reveal debris and count passes over fields it crosses."""
    if not s.powered:
        return
    spec = s.spec
    step = 2 * math.pi / (spec["sweep_period_s"] * W.TICK_RATE)
    start = s.sweep_angle
    s.sweep_angle = (start + step) % (2 * math.pi)
    radius = spec["scan_radius_cells"]

    def crossed(x, y):
        return (math.atan2(y - s.y, x - s.x) - start) % (2 * math.pi) < step

    for d in world.debris.values():
        if not d.seen and math.hypot(d.x - s.x, d.y - s.y) <= radius and crossed(d.x, d.y):
            d.seen = True
    for f in world.fields:
        if f.hinted or math.hypot(f.cx - s.x, f.cy - s.y) > radius + f.radius:
            continue
        if crossed(f.cx, f.cy):
            f.signal_passes += 1
            if f.signal_passes >= W.FIELD_SIGNAL_PASSES:
                world.hint_field(f)
