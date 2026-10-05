"""Wear and repairs. Never imports pygame.

Production buildings wear a little with every cycle. Past WEAR["slow_from"]
they slow down (to worn_speed at 100%); in pressure mode they stop at 100%.
From repair_at they need a repair: a constructor or maintenance drone fetches
one machine part per `step` of wear and works it off. One repairer per
structure at a time (Structure.repairer).
"""

import math

from game.content import structures as S

W_ = S.WEAR


def add_wear(world, s):
    """After a finished cycle."""
    per = s.spec.get("wear_per_cycle", 0.0)
    if not per:
        return
    from game.sim.structures import clock_spec
    per *= clock_spec(s.clock)["wear"] * world.research.effect("wear_mult", 1.0)
    s.wear = min(1.0, s.wear + per)


def speed_factor(s):
    lo = W_["slow_from"]
    if s.wear <= lo:
        return 1.0
    return 1.0 - (s.wear - lo) / (1.0 - lo) * (1.0 - W_["worn_speed"])


def broken(world, s):
    return s.wear >= 1.0 and world.contracts.mode.get("wear_breaks", False)


def needs_repair(s):
    return s.built and s.wear >= W_["repair_at"]


def parts_needed(s):
    return max(1, math.ceil(s.wear / W_["step"] - 1e-9))


def jobs(world, unit):
    """Worn structures nobody is repairing, most worn first."""
    out = [s for s in world.structures.values() if needs_repair(s) and s.repairer in (None, unit.id)
           and not s.deconstruct]
    out.sort(key=lambda s: (-s.wear, s.id))
    return out


def parts_store(world, unit, near_xy, flies=False):
    """(storage, free parts) nearest to near_xy that has machine parts to spare."""
    best = None
    for s in world.storages():
        free = s.storage.get("parts", 0) - s.reserved_out.get("parts", 0)
        if free <= 0:
            continue
        d = math.hypot(s.x - near_xy[0], s.y - near_xy[1])
        if s.kind == "maintenance_hangar":
            d *= 0.5  # drones and builders prefer the hangar's own stock
        if best is None or d < best[0]:
            best = (d, s, free)
    return (best[1], best[2]) if best else (None, 0)


def take_parts(world, store, n):
    """Load up to n parts from a storage. Returns how many were taken."""
    take = max(0, min(n, store.storage.get("parts", 0) - store.reserved_out.get("parts", 0)))
    if take:
        store.storage["parts"] -= take
        if not store.storage["parts"]:
            del store.storage["parts"]
    return take


def finish_repair(world, unit, s):
    """Work off as much wear as the carried parts cover; parts are used up."""
    parts = unit.cargo.get("parts", 0)
    steps = min(parts, parts_needed(s))
    if steps:
        s.wear = max(0.0, s.wear - steps * W_["step"])
        unit.cargo["parts"] = parts - steps
        if not unit.cargo["parts"]:
            del unit.cargo["parts"]
        world.consumed["parts"] = world.consumed.get("parts", 0) + steps
        world.event(f"{s.spec['name'].upper()} REPAIRED ({steps} PARTS)")
    s.repairer = None
    return steps


def repair_seconds(unit, s):
    return min(unit.cargo.get("parts", 0), parts_needed(s)) * W_["seconds_per_step"] / unit.spec["repair_rate"]


def release(world, unit):
    for s in world.structures.values():
        if s.repairer == unit.id:
            s.repairer = None
