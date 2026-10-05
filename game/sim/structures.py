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

    @property
    def spec(self):
        return STRUCTURES[self.kind]

    def stored(self):
        return sum(self.storage.values())

    def charges(self):
        return self.built and self.spec.get("charge_slots", 0) > 0

    def stores(self):
        return self.built and self.spec.get("storage", 0) > 0

    def materials_needed(self):
        """Items still to bring: cost - delivered - incoming (never negative)."""
        cost = self.spec.get("build_cost", {})
        return {k: n - self.delivered.get(k, 0) - self.incoming.get(k, 0)
                for k, n in cost.items() if n - self.delivered.get(k, 0) - self.incoming.get(k, 0) > 0}

    def fully_delivered(self):
        cost = self.spec.get("build_cost", {})
        return all(self.delivered.get(k, 0) >= n for k, n in cost.items())

    def build_progress(self):
        """0..1 over the whole job: materials first (a third), then assembly."""
        if self.built:
            return 1.0
        cost = self.spec.get("build_cost", {})
        total = sum(cost.values()) or 1
        got = sum(min(self.delivered.get(k, 0), n) for k, n in cost.items())
        assembly = self.work_done_s / self.spec.get("build_time_s", 1.0)
        return min(1.0, got / total / 3 + assembly * 2 / 3)


def make_docks(s):
    spec = s.spec
    slots = spec.get("charge_slots", 0) or spec.get("dock_slots", 0)
    s.docks, s.dock_users = [], []
    r = spec.get("dock_radius_cells", 0.0)
    for k in range(slots):
        a = math.pi / 4 + k * 2 * math.pi / slots
        s.docks.append((s.x + r * math.cos(a), s.y + r * math.sin(a)))
        s.dock_users.append(None)


def check_placement(world, kind, x, y):
    """(ok, reason) for placing kind with its centre at (x, y)."""
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
    steepest = 0.0
    for cy in range(int(y - r), int(y + r) + 2):
        for cx in range(int(x - r), int(x + r) + 2):
            if 0 <= cx < size and 0 <= cy < size and math.hypot(cx - x, cy - y) <= r + 0.5:
                steepest = max(steepest, world.slopes[cy * size + cx])
    if steepest > spec["max_slope_deg"]:
        return False, f"TOO STEEP ({steepest:.1f} DEG, MAX {spec['max_slope_deg']:.0f})"
    for other in world.structures.values():
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
    world.structures[s.id] = s
    world.dirty_power = True
    return s, ""


def complete(world, s):
    s.built = True
    for k, n in s.delivered.items():
        world.consumed[k] = world.consumed.get(k, 0) + n
    s.delivered.clear()
    s.incoming.clear()
    if s.kind == "solar":
        s.output_kw = s.spec["power_kw"] * world.illumination_at(s.x, s.y)
    else:
        s.output_kw = s.spec.get("power_kw", 0.0)
    make_docks(s)
    world.structures_changed()
    world.event(f"{s.spec['name'].upper()} COMPLETE")


def cancel_site(world, s):
    """Remove an unfinished site; delivered materials go back to the lander."""
    for item, n in s.delivered.items():
        world.lander.storage[item] = world.lander.storage.get(item, 0) + n
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
