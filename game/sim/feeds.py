"""Direct feed: buildings placed touching hand items straight across.
Never imports pygame.

A link joins a producer to a touching building whose recipe consumes one of
the producer's outputs. Each link moves one item at a time, FEED_ITEMS_PER_S,
from the producer's output buffer to the consumer's input buffer, never
touching items a hauler has reserved. Haulers still take whatever is left.
"""

import math

from game.content import structures as S
from game.content import world as W
from game.sim import production as P


def touching(a_kind, ax, ay, b_kind, bx, by):
    from game.content.structures import STRUCTURES
    gap = math.hypot(ax - bx, ay - by) - STRUCTURES[a_kind]["footprint_cells"] - STRUCTURES[b_kind]["footprint_cells"]
    return gap <= S.FEED_REACH_CELLS


def items_between(a_kind, b_kind):
    """Items a building of a_kind could feed to one of b_kind."""
    from game.content.structures import STRUCTURES
    ra, rb = STRUCTURES[a_kind].get("recipe"), STRUCTURES[b_kind].get("recipe")
    if not ra or not rb:
        return []
    return [k for k in ra["out"] if k in rb["in"]]


def links(world):
    """[(producer, consumer, item)] between built, touching buildings."""
    built = [s for s in world.structures.values() if s.built and P.recipe(s)]
    out = []
    for a in built:
        for b in built:
            if a is b:
                continue
            for item in items_between(a.kind, b.kind):
                if touching(a.kind, a.x, a.y, b.kind, b.x, b.y):
                    out.append((a, b, item))
    return out


def partners(world, kind, x, y):
    """For the placement ghost: names of buildings a new kind at (x, y) would
    feed, and be fed by."""
    feeds, fed_by = [], []
    for o in world.structures.values():
        if not touching(kind, x, y, o.kind, o.x, o.y):
            continue
        if items_between(kind, o.kind):
            feeds.append(o.spec["name"])
        if items_between(o.kind, kind):
            fed_by.append(o.spec["name"])
    return feeds, fed_by


def update(world):
    every = max(1, round(W.TICK_RATE / S.FEED_ITEMS_PER_S))
    if world.tick_count % every:
        return
    for a, b, item in world.feed_links():
        free = a.outputs.get(item, 0) - a.reserved_out.get(item, 0)
        room = P.input_cap(b, item) - b.inputs.get(item, 0) - b.reserved_in.get(item, 0)
        if free > 0 and room > 0:
            a.outputs[item] -= 1
            if not a.outputs[item]:
                del a.outputs[item]
            b.inputs[item] = b.inputs.get(item, 0) + 1
            b.fed += 1
