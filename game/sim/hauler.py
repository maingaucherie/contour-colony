"""Hauler brain: work the job board. Never imports pygame.

Take the best job (see jobs.py), drive to the source, load, drive to the
destination, unload. Items are reserved at both ends for the whole trip.
"""

import math

from game.sim import jobs as J
from game.sim import production as P
from game.sim import units as UN


def _approach(s, unit):
    """A spot just outside a structure, on the side the unit comes from."""
    dx, dy = unit.x - s.x, unit.y - s.y
    d = math.hypot(dx, dy) or 1.0
    r = s.spec["footprint_cells"] + 0.8
    return s.x + dx / d * r, s.y + dy / d * r


def _haul(world, unit):
    """(source, dest, item, amount) of the current job, structures resolved."""
    if unit.haul is None:
        return None, None, None, 0
    src_id, dst_id, item, amount = unit.haul
    return world.structures.get(src_id), world.structures.get(dst_id), item, amount


def _go(world, unit, s, activity, f=None):
    goal = _approach(s, unit)
    UN.set_path(unit, UN.path_to(world, unit, goal, f) or [goal], activity, s.id)


def _toward(world, unit, s, activity, f=None):
    """Drive to s if the battery allows getting there and on to a charger;
    otherwise top up at a charger on the way first."""
    f = f or UN.here_field(world, unit)
    d = f.dist[world.grid.node_at(s.x, s.y)]
    rest = UN.back_cost(world, s.x, s.y)
    if not UN.can_afford(world, unit, d + rest):
        r = UN.relay(world, unit, s.x, s.y, rest)
        if r is not None and UN.stage(world, unit, r):
            return
    UN.release_dock(world, unit)
    _go(world, unit, s, activity, f)


def think(world, unit):
    if UN.try_charge(world, unit):
        return
    roles = UN.dock_roles(world, unit)
    if unit.battery < UN.reserve(world, unit) and "charge" not in roles:
        if UN.go_dock(world, unit, "charge"):
            return
    f = UN.here_field(world, unit)
    if unit.cargo_total():
        item = next(iter(unit.cargo))
        src, dst, _, _ = _haul(world, unit)
        if dst is None:
            job = J.best_job(world, unit, f, only_item=item)
            if job is None:
                UN.idle(unit, "holding cargo - nowhere to take it")
                return
            _, _, dst, item, amount = job
            J.reserve(None, dst, item, amount)
            unit.haul = (None, dst.id, item, amount)
        _toward(world, unit, dst, "to_dropoff", f)
        return
    if unit.haul is not None:
        # A reserved job, picked up again after topping up on the way.
        src, dst, item, amount = _haul(world, unit)
        if src is not None and dst is not None:
            _toward(world, unit, src, "to_pickup", f)
            return
        drop_job(world, unit)
    job = J.best_job(world, unit, f)
    if job is not None:
        _, src, dst, item, amount = job
        J.reserve(src, dst, item, amount)
        unit.haul = (src.id, dst.id, item, amount)
        _toward(world, unit, src, "to_pickup", f)
        return
    UN.head_home(world, unit)


def arrived(world, unit):
    src, dst, item, amount = _haul(world, unit)
    if unit.activity == "to_pickup":
        if src is None:
            drop_job(world, unit)
            think(world, unit)
        else:
            UN.work(unit, "load", unit.spec["load_s"])
    elif unit.activity == "to_dropoff":
        if dst is None:
            drop_job(world, unit)
            think(world, unit)
        else:
            UN.work(unit, "unload", unit.spec["load_s"])
    else:
        think(world, unit)


def work_done(world, unit):
    src, dst, item, amount = _haul(world, unit)
    if unit.activity == "load":
        J.release_out(src, item, amount)
        take = 0
        if src is not None:
            held = src.outputs if P.recipe(src) and item in src.outputs else src.storage
            take = min(amount, held.get(item, 0))
        if take:
            held[item] -= take
            if not held[item]:
                del held[item]
            unit.cargo[item] = unit.cargo.get(item, 0) + take
        if take < amount:
            J.release_in(dst, item, amount - take)
        if not take:
            unit.haul = None
            think(world, unit)
            return
        unit.haul = (None, dst.id if dst else None, item, take)
        if dst is None:
            think(world, unit)
        else:
            _toward(world, unit, dst, "to_dropoff")
    elif unit.activity == "unload":
        n = unit.cargo.get(item, 0)
        J.release_in(dst, item, amount)
        if dst is not None and n:
            put = world.deliver(dst, item, n)
            unit.cargo[item] = n - put
            if not unit.cargo[item]:
                del unit.cargo[item]
        unit.haul = None
        think(world, unit)


def drop_job(world, unit):
    src, dst, item, amount = _haul(world, unit)
    if unit.haul is not None:
        if unit.cargo_total():
            J.release_in(dst, item, amount)  # picked up already: only the destination was reserved
        else:
            J.release_out(src, item, amount)
            J.release_in(dst, item, amount)
    unit.haul = None
    unit.target = None
    unit.path = []
