"""Conveyors: a powered belt from one building to another. Never imports pygame.

A conveyor runs in a straight line from the edge of its source building to the
edge of its destination, at most CONVEYOR_MAX_CELLS long. Its ground must be
no steeper than the conveyor's max_slope_deg; ground up to GRADE_MAX_DEG is
graded for credits as part of the build (the conveyor bed). It costs sinter
per cell of length and constructors build it like any structure, working at
its midpoint. It draws power from its source's grid (or else its
destination's).

Built and powered, it moves CONVEYOR_ITEMS_PER_S, one item at a time:
  producer -> consumer   the consumer's ingredients that the producer makes
  producer -> storage    everything the producer makes (at the lander, contract
                         goods ship straight away)
  storage  -> consumer   the consumer's ingredients, from that store
Items a hauler has reserved are never taken; haulers still move the rest.
When either building is removed, its conveyors go too (with the usual refund).
"""

import math

from game.content import structures as S
from game.content import world as W
from game.content.structures import STRUCTURES
from game.sim import feeds
from game.sim import production as P
from game.sim import structures as ST


def is_producer(kind):
    r = STRUCTURES[kind].get("recipe")
    return bool(r and r["out"])


def is_consumer(kind):
    r = STRUCTURES[kind].get("recipe")
    return bool(r and r["in"])


def is_store(kind):
    return STRUCTURES[kind].get("storage", 0) > 0


def _accepts(kind, item):
    allowed = STRUCTURES[kind].get("accepts")
    return allowed is None or item in allowed


def items_for(a_kind, b_kind):
    """Items a conveyor from a building of a_kind to one of b_kind would carry."""
    a, b = STRUCTURES[a_kind], STRUCTURES[b_kind]
    if is_producer(a_kind) and is_consumer(b_kind):
        return feeds.items_between(a_kind, b_kind)
    if is_producer(a_kind) and is_store(b_kind):
        return [k for k in a["recipe"]["out"] if _accepts(b_kind, k)]
    if is_store(a_kind) and is_consumer(b_kind):
        return [k for k in b["recipe"]["in"] if _accepts(a_kind, k)]
    return []


def can_start(s):
    """(ok, reason) for picking s as a conveyor's source."""
    if s.is_line():
        return False, "PICK A BUILDING"
    if not (is_producer(s.kind) or is_store(s.kind)):
        return False, f"{s.spec['name'].upper()} HAS NOTHING TO SEND"
    return True, ""


def _cells_along(world, p0, p1):
    """Grid cells under the belt, each once, in order."""
    length = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    steps = max(1, int(length * 2) + 1)
    size = world.heightmap.size
    out = []
    for i in range(steps + 1):
        t = i / steps
        cx = int(round(p0[0] + (p1[0] - p0[0]) * t))
        cy = int(round(p0[1] + (p1[1] - p0[1]) * t))
        if 0 <= cx < size and 0 <= cy < size and (cx, cy) not in out:
            out.append((cx, cy))
    return out


def plan(world, a, b):
    """Check a conveyor from a to b. Returns a dict: ok, reason, and when it
    could be built, start, end, length, grade_deg and credits (for grading)."""
    out = {"ok": False, "reason": ""}
    spec = STRUCTURES["conveyor"]
    if not world.research.unlocked(spec.get("unlocked_by")):
        out["reason"] = "NOT RESEARCHED"
        return out
    ok, reason = can_start(a)
    if not ok:
        out["reason"] = reason
        return out
    if b is a or b.is_line():
        out["reason"] = "PICK ANOTHER BUILDING"
        return out
    items = items_for(a.kind, b.kind)
    if not items:
        both_stores = is_store(a.kind) and is_store(b.kind)
        out["reason"] = ("HAULERS MOVE STORAGE TO STORAGE" if both_stores
                         else f"{b.spec['name'].upper()} USES NOTHING {a.spec['name'].upper()} SENDS")
        return out
    if any(c.kind == "conveyor" and c.src == a.id and c.dst == b.id for c in world.structures.values()):
        out["reason"] = "ALREADY LINKED"
        return out
    p0, p1 = ST.link_ends(a, b)
    length = math.hypot(b.x - a.x, b.y - a.y) - a.spec["footprint_cells"] - b.spec["footprint_cells"]
    if length <= S.FEED_REACH_CELLS and feeds.items_between(a.kind, b.kind):
        out["reason"] = "ALREADY FED DIRECTLY"
        return out
    if length > S.CONVEYOR_MAX_CELLS:
        out["reason"] = f"TOO LONG ({length:.0f} CELLS, MAX {S.CONVEYOR_MAX_CELLS:.0f})"
        return out
    for o in world.structures.values():
        if o is a or o is b or o.is_line():
            continue
        if ST.distance_to_segment(o.x, o.y, p0, p1) < o.spec["footprint_cells"] + spec["footprint_cells"] / 2:
            out["reason"] = "BLOCKED BY " + o.spec["name"].upper()
            return out
    grade = 0.0
    size = world.heightmap.size
    for cx, cy in _cells_along(world, p0, p1):
        slope = world.slopes[cy * size + cx]
        if slope > S.GRADE_MAX_DEG:
            out["reason"] = f"TOO STEEP ({slope:.1f} DEG, GRADING MAX {S.GRADE_MAX_DEG:.0f})"
            return out
        grade += max(0.0, slope - spec["max_slope_deg"])
    credits = ST.grade_credits(spec, grade)
    if world.credits < credits:
        out["reason"] = f"GRADING NEEDS {credits} CR"
        return out
    out.update(ok=True, start=p0, end=p1, length=max(0.0, length), grade_deg=grade, credits=credits,
               items=items)
    return out


def place(world, src_id, dst_id):
    """Lay out a conveyor site from src to dst. Returns (site or None, reason)."""
    a, b = world.structures.get(src_id), world.structures.get(dst_id)
    if a is None or b is None:
        return None, "PICK A BUILDING"
    p = plan(world, a, b)
    if not p["ok"]:
        return None, p["reason"]
    (x0, y0), (x1, y1) = p["start"], p["end"]
    c = ST.Structure(world.new_id(), "conveyor", (x0 + x1) / 2, (y0 + y1) / 2, built=False,
                     created_tick=world.tick_count, src=a.id, dst=b.id, length=p["length"])
    c.grade_deg, c.grade_cr = p["grade_deg"], p["credits"]
    world.credits -= c.grade_cr
    world.structures[c.id] = c
    world.dirty_power = True
    return c, ""


def attached(world, s):
    """Conveyors that start or end at s."""
    return [c for c in world.structures.values() if c.kind == "conveyor" and s.id in (c.src, c.dst)]


# Moving items ---------------------------------------------------------------

def _free_at_source(a, item):
    held = a.outputs if P.recipe(a) and item in P.recipe(a)["out"] else a.storage
    return held.get(item, 0) - a.reserved_out.get(item, 0)


def _room_at_destination(world, b, item):
    r = P.recipe(b)
    if r and item in r["in"]:
        return P.input_cap(b, item) - b.inputs.get(item, 0) - b.reserved_in.get(item, 0)
    if b.spec.get("export_bay") and world.contracts.needs().get(item, 0) > 0:
        return 1
    if not b.stores() or not b.accepts(item):
        return 0
    return min(b.spec["storage"] - b.stored(), world.storage_room(item))


def next_item(world, c, a, b):
    """The item c moves next: of those it can, the one most piled up at the source."""
    best = None
    for item in items_for(a.kind, b.kind):
        free = _free_at_source(a, item)
        if free > 0 and _room_at_destination(world, b, item) > 0 and (best is None or free > best[0]):
            best = (free, item)
    return best[1] if best else None


def _move(world, a, b, item):
    held = a.outputs if P.recipe(a) and item in P.recipe(a)["out"] else a.storage
    held[item] -= 1
    if not held[item]:
        del held[item]
    r = P.recipe(b)
    if r and item in r["in"]:
        b.inputs[item] = b.inputs.get(item, 0) + 1
        b.fed += 1
    else:
        world.deliver(b, item, 1)


def update(world):
    every = max(1, round(W.TICK_RATE / S.CONVEYOR_ITEMS_PER_S))
    if world.tick_count % every:
        return
    for c in world.structures.values():
        if c.kind != "conveyor" or not c.built:
            continue
        a, b = world.structures.get(c.src), world.structures.get(c.dst)
        if not c.powered:
            c.status = P.UNPOWERED
            continue
        if a is None or b is None or not a.built or not b.built:
            c.status = P.IDLE
            continue
        item = next_item(world, c, a, b)
        if item is None:
            c.status = P.IDLE
            continue
        _move(world, a, b, item)
        c.moved += 1
        c.status = P.WORKING
