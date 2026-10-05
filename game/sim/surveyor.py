"""Survey rover brain: scout for scrap and confirm flagged fields. Never imports pygame.

While driving it raises everything within sweep_radius to survey level 1 and
spots debris within its sight. Standing still for linger_s raises the spot to
level 2. It can't discover fields itself: once the scanner flags one, the
rover goes and surveys it in detail until the whole outline is confirmed.
Otherwise it pushes the surveyed frontier outward, finding scrap for the
scavengers. A player order ("survey here") overrides that.
"""

import math

from game.sim import units as UN


def _linger_s(world, unit):
    return unit.spec["linger_s"] * world.research.effect("linger_mult", 1.0)


def on_move(world, unit):
    world.survey_area(unit.x, unit.y, unit.spec["sweep_radius_cells"], 1)


def start_linger(world, unit):
    UN.work(unit, "surveying", _linger_s(world, unit))


def _targets(world, unit, f):
    """Best spot to drive to: an unconfirmed part of a hinted field, else the
    nearest unsurveyed ground, as long as it's within battery range."""
    grid = world.grid
    linger_energy = _linger_s(world, unit) * unit.spec["linger_drain_per_s"]
    best = None
    for fld in world.fields:
        if not fld.hinted:
            continue
        # Interior points and the boundary itself: a field is fully confirmed only
        # once every piece of its outline has been surveyed in detail.
        edge = [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b in zip(fld.boundary, fld.boundary[1:])]
        for x, y in fld.sample_points(unit.spec["linger_radius_cells"]) + edge:
            if world.survey.level_at(x, y) >= 2:
                continue
            node = grid.node_at(x, y)
            d = f.dist[node]
            if d == math.inf or not UN.can_afford(world, unit, d + world.charge_field.dist[node], linger_energy):
                continue
            if best is None or d < best[0]:
                best = (d, (x, y), True)
    if best is not None:
        return best
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
            best = (d, (x, y), False)
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
    if choice is not None:
        _, (x, y), linger = choice
        UN.release_dock(world, unit)
        UN.set_path(unit, UN.path_to(world, unit, (x, y), f), "to_survey_spot" if linger else "to_frontier")
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
    unit.order = None
    think(world, unit)


def drop_job(world, unit):
    unit.target = None
    unit.path = []
