"""Power grids: connectivity and allocation by priority. Never imports pygame.

Structures with a grid reach (lander, solar arrays, pylons) link to each other
when either one's reach covers the other; any other structure joins a grid if
it lies within a linked structure's reach. Each connected grid sums its supply
and serves demand in priority order; structures that don't fit go unpowered.
"""

import math

from game.content import world as W

_RANK = {p: i for i, p in enumerate(W.PRIORITIES)}


def allocate(supply, consumers):
    """consumers: [(key, draw_kw, priority)] -> (set of powered keys, kW served).

    Highest priority first; within a priority, in the given order. A consumer
    that doesn't fit is skipped, but smaller ones after it may still fit.
    """
    powered, served = set(), 0.0
    for key, draw, priority in sorted(consumers, key=lambda c: _RANK[c[2]]):
        if served + draw <= supply + 1e-9:
            powered.add(key)
            served += draw
    return powered, served


def compute(structures):
    """Recompute grid membership and power state for built structures.

    Sets on each structure: grid (id or -1), grid_parent (structure id it
    connected through, or None), powered. Returns {grid id: summary dict}.
    """
    built = [s for s in structures if s.built]
    nodes = [s for s in built if s.spec.get("grid_reach_cells", 0) > 0]
    for s in built:
        s.grid, s.grid_parent, s.powered = -1, None, False

    def reach(a, b):
        d = math.hypot(a.x - b.x, a.y - b.y)
        return d <= max(a.spec.get("grid_reach_cells", 0), b.spec.get("grid_reach_cells", 0))

    grids = {}
    gid = 0
    for root in nodes:
        if root.grid != -1:
            continue
        root.grid = gid
        frontier = [root]
        members = [root]
        while frontier:
            cur = frontier.pop()
            for other in nodes:
                if other.grid == -1 and reach(cur, other):
                    other.grid, other.grid_parent = gid, cur.id
                    frontier.append(other)
                    members.append(other)
        grids[gid] = members
        gid += 1

    for s in built:
        if s.grid != -1:
            continue
        best = None
        for n in nodes:
            d = math.hypot(s.x - n.x, s.y - n.y)
            if d <= n.spec["grid_reach_cells"] and (best is None or d < best[0]):
                best = (d, n)
        if best:
            s.grid, s.grid_parent = best[1].grid, best[1].id
            grids[s.grid].append(s)

    summary = {}
    for g, members in grids.items():
        supply = sum(m.output_kw for m in members)
        consumers = [(m.id, m.spec.get("draw_kw", 0.0), m.priority) for m in members if m.spec.get("draw_kw", 0.0) > 0]
        on, served = allocate(supply, consumers)
        for m in members:
            m.powered = m.spec.get("draw_kw", 0.0) <= 0 or m.id in on
        demand = sum(c[1] for c in consumers)
        summary[g] = {"supply": supply, "demand": demand, "served": served,
                      "members": [m.id for m in members]}
    return summary
