"""Maintenance drone brain: fly out and repair worn structures. Never imports pygame.

Drones fly in straight lines over any terrain at a steady speed, so distances
are straight distances and slope doesn't matter. A drone picks the most worn
structure nobody is repairing, collects machine parts (its hangar's first),
flies over, repairs, and flies home to its hangar to charge.
"""

import math

from game.content import units as U
from game.sim import units as UN
from game.sim import wear


def _energy(unit, cells, work_s=0.0):
    return cells * unit.spec["drain_per_cost_cell"] * U.TRIP_SAFETY_FACTOR + work_s * unit.spec["repair_drain_per_s"]


def _home_distance(world, unit, x, y):
    homes = [s for s in world.chargers() if s.kind in unit.spec["docks_at"]]
    return min((math.hypot(s.x - x, s.y - y) for s in homes), default=math.inf)


def _affordable(world, unit, cells, work_s=0.0):
    return unit.battery - _energy(unit, cells, work_s) >= UN.reserve(world, unit)


def think(world, unit):
    if UN.try_charge(world, unit):
        return
    roles = UN.dock_roles(world, unit)
    if unit.battery < UN.reserve(world, unit) and "charge" not in roles:
        if UN.go_dock(world, unit, "charge"):
            return
    if unit.cargo.get("parts"):
        s = world.structures.get(unit.job)
        if s is not None and wear.needs_repair(s):
            UN.release_dock(world, unit)
            UN.set_path(unit, [(s.x, s.y)], "to_repair", s.id)
            return
        if "store" in roles:
            UN.work(unit, "unload", unit.spec["load_s"])
            return
        if UN.go_dock(world, unit, "charge"):   # hangars take parts back
            return
    for s in wear.jobs(world, unit):
        store, free = wear.parts_store(world, unit, (unit.x, unit.y), flies=True)
        if store is None:
            break
        n = min(wear.parts_needed(s), unit.spec["cargo"], free)
        trip = (math.hypot(store.x - unit.x, store.y - unit.y) + math.hypot(s.x - store.x, s.y - store.y)
                + _home_distance(world, unit, s.x, s.y))
        if not _affordable(world, unit, trip, n * wear.W_["seconds_per_step"] / unit.spec["repair_rate"]):
            continue
        s.repairer = unit.id
        unit.job = s.id
        UN.release_dock(world, unit)
        UN.set_path(unit, [(store.x, store.y)], "fetch_parts", store.id)
        return
    unit.job = None
    _home(world, unit)


def _home(world, unit):
    """Nothing to repair: wait docked at home, topping up."""
    if unit.docked and unit.dock in world.structures:
        if not UN.try_charge(world, unit, 1.0):
            UN.idle(unit)
        return
    if not UN.go_dock(world, unit, "charge"):
        UN.idle(unit)


def arrived(world, unit):
    if unit.activity == "fetch_parts":
        UN.work(unit, "load_parts", unit.spec["load_s"])
    elif unit.activity == "to_repair":
        s = world.structures.get(unit.job)
        if s is None or not s.built:
            wear.release(world, unit)
            unit.job = None
            think(world, unit)
        else:
            UN.work(unit, "repairing", wear.repair_seconds(unit, s))
    else:
        think(world, unit)


def work_tick(world, unit):
    if unit.activity == "repairing":
        unit.battery = max(0.0, unit.battery - unit.spec["repair_drain_per_s"] / world.tick_rate)


def work_done(world, unit):
    if unit.activity == "load_parts":
        s = world.structures.get(unit.job)
        store = world.structures.get(unit.target)
        take = 0
        if s is not None and store is not None and wear.needs_repair(s):
            take = wear.take_parts(world, store, min(wear.parts_needed(s), unit.spec["cargo"] - unit.cargo_total()))
        if not take:
            wear.release(world, unit)
            unit.job = None
            think(world, unit)
            return
        unit.cargo["parts"] = unit.cargo.get("parts", 0) + take
        UN.set_path(unit, [(s.x, s.y)], "to_repair", s.id)
    elif unit.activity == "repairing":
        s = world.structures.get(unit.job)
        if s is not None:
            wear.finish_repair(world, unit, s)
        unit.job = unit.target = None
        think(world, unit)
    elif unit.activity == "unload":
        s = world.structures.get(unit.dock)
        if s is not None:
            for k in list(unit.cargo):
                put = world.store(s, k, unit.cargo[k])
                unit.cargo[k] -= put
                if not unit.cargo[k]:
                    del unit.cargo[k]
        if unit.cargo_total():
            world.lander.storage["parts"] = world.lander.storage.get("parts", 0) + unit.cargo.pop("parts", 0)
        think(world, unit)
    else:
        think(world, unit)


def drop_job(world, unit):
    wear.release(world, unit)
    unit.target = None
    unit.path = []
