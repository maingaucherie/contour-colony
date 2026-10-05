"""Job board: offers, requests, scoring and reservations. Never imports pygame.

Offers: production outputs (once JOB_OFFER_MIN are waiting, or the buffer is
full) and anything held in storage. Requests: production inputs up to their
buffer size, contract goods at the lander's export bay, and storage for
anything (lowest priority). Storage never hauls to storage. A hauler takes
the best-scoring pair it can reach and still get home from; the items are
reserved at both ends until it delivers or drops the job.
"""

import math

from game.content import world as W
from game.sim import production as P
from game.sim import units as UN


def _reserved(d):
    return sum(d.values())


def offers(world):
    for s in world.structures.values():
        if not s.built:
            continue
        if P.recipe(s):
            for item, n in s.outputs.items():
                avail = n - s.reserved_out.get(item, 0)
                if avail > 0 and (n >= W.JOB_OFFER_MIN or n >= P.output_cap(s, item)):
                    yield s, item, avail, "production"
        if s.stores():
            for item, n in s.storage.items():
                avail = n - s.reserved_out.get(item, 0)
                if avail > 0:
                    yield s, item, avail, "storage"


def requests(world):
    """(structure, item or None for anything, space, multiplier)."""
    contracts = world.contracts
    for s in world.structures.values():
        if not s.built:
            continue
        r = P.recipe(s)
        if r:
            mult = W.JOB_PRIORITY_MULT[s.priority]
            for item in r["in"]:
                space = P.input_cap(s, item) - s.inputs.get(item, 0) - s.reserved_in.get(item, 0)
                if space > 0:
                    yield s, item, space, mult
        if s.spec.get("export_bay") and contracts is not None:
            for item, remaining in contracts.needs().items():
                space = remaining - s.reserved_in.get(item, 0)
                if space > 0:
                    yield s, item, space, W.JOB_EXPORT_MULT
        if s.stores():
            space = s.spec["storage"] - s.stored() - _reserved(s.reserved_in)
            if space > 0:
                yield s, None, space, W.JOB_STORAGE_MULT


def _feasible(world, unit, d, rest, x, y):
    """A leg of d cost-cells to (x, y) then rest more: in range now, or via
    chargers on the way (units.relay)."""
    return UN.can_afford(world, unit, d + rest) or UN.relay(world, unit, x, y, rest) is not None


def best_job(world, unit, f, only_item=None):
    """Best (score, source, dest, item, amount) for a hauler, or None. A job
    counts if the hauler can do it in one go, or in legs with top-ups at
    chargers on the way (pick up, top up, deliver). With only_item, the hauler
    already carries that and only needs a destination."""
    grid = world.grid
    cap = unit.spec["cargo"]
    reqs = list(requests(world))
    best = None
    if only_item is not None:
        amount = unit.cargo.get(only_item, 0)
        for dst, item, space, mult in reqs:
            if item not in (None, only_item) or (item is None and not dst.accepts(only_item)):
                continue  # (cargo already aboard may go to storage over the item cap)
            d = f.dist[grid.node_at(dst.x, dst.y)]
            if d == math.inf:
                continue
            score = min(amount, space) / (d + W.JOB_DISTANCE_BIAS) * mult
            if best is not None and score <= best[0]:
                continue
            if not _feasible(world, unit, d, UN.back_cost(world, dst.x, dst.y), dst.x, dst.y):
                continue
            best = (score, None, dst, only_item, min(amount, space))
        return best
    for src, item, avail, kind in offers(world):
        d1 = f.dist[grid.node_at(src.x, src.y)]
        if d1 == math.inf:
            continue
        from_src = None
        pickup_ok = None
        room = None
        for dst, ritem, space, mult in reqs:
            if dst is src or (ritem is not None and ritem != item):
                continue
            if ritem is None and kind == "storage":
                continue  # no storage-to-storage shuffling
            if ritem is None and not dst.accepts(item):
                continue
            if ritem is None:
                if room is None:
                    room = world.storage_room(item)
                space = min(space, room)
            amount = min(avail, space, cap)
            if amount <= 0:
                continue
            if from_src is None:
                from_src = grid.field(grid.node_at(src.x, src.y))
            d2 = from_src.dist[grid.node_at(dst.x, dst.y)]
            if d2 == math.inf:
                continue
            score = amount / (d1 + d2 + W.JOB_DISTANCE_BIAS) * mult
            if best is not None and score <= best[0]:
                continue
            if not UN.can_afford(world, unit, d1 + d2 + UN.back_cost(world, dst.x, dst.y)):
                # In legs: the pickup (and back to a charger), then the drop-off from one.
                if pickup_ok is None:
                    pickup_ok = _feasible(world, unit, d1, UN.back_cost(world, src.x, src.y), src.x, src.y)
                if not pickup_ok or not UN.in_charger_range(world, unit, dst.x, dst.y):
                    continue
            best = (score, src, dst, item, amount)
    return best


def reserve(src, dst, item, amount):
    if src is not None:
        src.reserved_out[item] = src.reserved_out.get(item, 0) + amount
    dst.reserved_in[item] = dst.reserved_in.get(item, 0) + amount


def _release(d, item, amount):
    left = d.get(item, 0) - amount
    if left > 0:
        d[item] = left
    else:
        d.pop(item, None)


def release_out(src, item, amount):
    if src is not None:
        _release(src.reserved_out, item, amount)


def release_in(dst, item, amount):
    if dst is not None:
        _release(dst.reserved_in, item, amount)
