"""Survey rover brain: scout for scrap and confirm flagged fields. Never imports pygame.

While driving it raises everything within sweep_radius to survey level 1 and
spots debris within its sight. Standing still for linger_s raises the spot to
level 2. It can't discover fields itself: once the scanner flags one, the
rover goes and surveys it in detail until the whole outline is confirmed.
Otherwise it pushes the surveyed frontier outward, finding scrap for the
scavengers. A player order ("survey here") overrides that.
"""

import math

from game.content import world as W
from game.sim import units as UN


def _linger_s(world, unit):
    return unit.spec["linger_s"] * world.research.effect("linger_mult", 1.0)


def on_move(world, unit):
    world.survey_area(unit.x, unit.y, unit.spec["sweep_radius_cells"], 1)


def start_linger(world, unit):
    UN.work(unit, "surveying", _linger_s(world, unit))


def stand_point(world, x, y, reach):
    """Where a rover should stand to survey (x, y) in detail: of the point
    itself and spots within reach around it, the one closest to a charger by
    road (so a field across a cliff is surveyed from the near side). None when
    every spot is walled in."""
    grid, home, cf = world.grid, world.home_field, world.charge_field
    size = world.heightmap.size
    best = None
    candidates = [(x, y)] + [(x + reach * k / 4 * math.cos(math.radians(a)), y + reach * k / 4 * math.sin(math.radians(a)))
                             for k in range(1, 5) for a in range(0, 360, 30)]
    for px, py in candidates:
        if not (0 <= px < size and 0 <= py < size):
            continue
        node = grid.node_at(px, py)
        if not (grid.open[node] and home.reachable(node)):
            continue
        cost = cf.dist[node] if cf is not None else 0.0
        if best is None or cost < best[0] - 1e-9:
            best = (cost, (px, py))
    return best[1] if best else None


def _targets(world, unit, f):
    """Best spot to drive to: an unconfirmed part of a hinted field, else the
    nearest unsurveyed ground, as long as it's within battery range.
    Returns (cost, stand point, field target point or None)."""
    grid = world.grid
    linger_energy = _linger_s(world, unit) * unit.spec["linger_drain_per_s"]
    reach = unit.spec["linger_radius_cells"] + W.SURVEY_CELLS * 0.75
    best = None
    unit_far = None   # nearest field spot out of range from here, for a top-up on the way
    for fld in world.fields:
        if not fld.hinted or fld.survey_done:
            continue
        # Interior points and the boundary itself: a field is fully surveyed once
        # every piece of its outline that can be reached has been done in detail.
        edge = [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b in zip(fld.boundary, fld.boundary[1:])]
        remaining = 0
        for x, y in fld.sample_points(unit.spec["linger_radius_cells"]) + edge:
            if world.survey.level_at(x, y) >= 2:
                continue
            stand = stand_point(world, x, y, reach)
            if stand is None:
                continue  # behind cliffs: nobody can survey it from the ground
            remaining += 1
            node = grid.node_at(*stand)
            d = f.dist[node]
            if d == math.inf:
                continue
            if not UN.can_afford(world, unit, d + world.charge_field.dist[node], linger_energy):
                if unit_far is None or d < unit_far[0]:
                    unit_far = (d, stand, linger_energy)
                continue
            if best is None or d < best[0]:
                best = (d, stand, (x, y))
        if not remaining:
            fld.survey_done = True
            world.event(f"{fld.kind.upper()} FIELD SURVEY COMPLETE", "field")
    if best is not None:
        return best
    if unit_far is not None:
        _, (x, y), energy = unit_far
        r = UN.relay(world, unit, x, y, world.charge_field.dist[grid.node_at(x, y)], energy)
        if r is not None:
            return ("relay", r)
    for node in range(grid.n * grid.n):
        d = f.dist[node]
        if d == math.inf or d < grid.node_cells:
            continue
        x, y = grid.node_centre(node)
        if world.survey.level_at(x, y) >= 1:
            continue
        if not UN.can_afford(world, unit, d + world.charge_field.dist[node]):
            continue
        if best is None or d < best[0]:
            best = (d, (x, y), None)
    return best


def think(world, unit):
    if UN.try_charge(world, unit):
        return
    roles = UN.dock_roles(world, unit)
    if unit.battery < UN.reserve(world, unit) and "charge" not in roles:
        if UN.go_dock(world, unit, "charge"):
            return
    f = UN.here_field(world, unit)
    choice = _targets(world, unit, f)
    if choice is not None and choice[0] == "relay":
        if UN.stage(world, unit, choice[1]):
            return
        choice = None
    if choice is not None:
        _, (x, y), spot = choice
        unit.survey_at = spot
        UN.release_dock(world, unit)
        UN.set_path(unit, UN.path_to(world, unit, (x, y), f), "to_survey_spot" if spot else "to_frontier")
        return
    UN.head_home(world, unit)


def arrived(world, unit):
    if unit.activity == "to_survey_spot":
        start_linger(world, unit)
    else:
        think(world, unit)


def work_tick(world, unit):
    unit.battery = max(0.0, unit.battery - unit.spec["linger_drain_per_s"] / world.tick_rate)


def work_done(world, unit):
    world.survey_area(unit.x, unit.y, unit.spec["linger_radius_cells"], 2)
    if unit.survey_at is not None:
        # Surveyed from beside it: make sure the spot it came for is covered.
        world.survey_area(*unit.survey_at, W.SURVEY_CELLS * 0.75, 2)
        unit.survey_at = None
    unit.order = None
    think(world, unit)


def drop_job(world, unit):
    unit.target = None
    unit.survey_at = None
    unit.path = []
