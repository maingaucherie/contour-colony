"""Graded roads: a site improvement rovers drive faster on. Never imports pygame.

A road is a straight strip ROAD_WIDTH_CELLS wide between two points, at most
ROAD_MAX_CELLS long. It is paid in credits when placed (so much per cell,
plus grading for ground steeper than the road's max_slope_deg) and a
constructor grades it like a structure site, working from its reachable end.

On a finished road rovers go ROAD_SPEED_MULT times as fast, slope slows them
less, and each cell costs that much less battery (see pathing.py). Roads can
cross ground up to ROAD_MAX_SLOPE_DEG, steeper than rovers can otherwise
drive, so a road can open a way up a crater wall. Routes find roads on their
own: there is nothing to assign.
"""

import math

from game.content import structures as S
from game.content.structures import STRUCTURES
from game.sim import structures as ST

SPEC = STRUCTURES["road"]


def cells_under(world, p0, p1, half_width=S.ROAD_WIDTH_CELLS / 2):
    """Terrain cells whose centres lie within half_width of the segment p0-p1."""
    size = world.heightmap.size
    x_lo = max(0, int(min(p0[0], p1[0]) - half_width) - 1)
    x_hi = min(size - 1, int(max(p0[0], p1[0]) + half_width) + 1)
    y_lo = max(0, int(min(p0[1], p1[1]) - half_width) - 1)
    y_hi = min(size - 1, int(max(p0[1], p1[1]) + half_width) + 1)
    return [(x, y) for y in range(y_lo, y_hi + 1) for x in range(x_lo, x_hi + 1)
            if ST.distance_to_segment(x, y, p0, p1) <= half_width]


def _reachable(world, x, y):
    node = world.grid.node_at(x, y)
    return world.grid.open[node] and world.home_field.reachable(node)


def plan(world, p0, p1):
    """Check a road from p0 to p1. Returns a dict: ok, reason, and when it can
    be built, length, grade_deg and credits."""
    out = {"ok": False, "reason": ""}
    size = world.heightmap.size
    for x, y in (p0, p1):
        if not (1 <= x <= size - 2 and 1 <= y <= size - 2):
            out["reason"] = "OUTSIDE THE SITE"
            return out
    length = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    if length < 1.0:
        out["reason"] = "TOO SHORT"
        return out
    if length > S.ROAD_MAX_CELLS:
        out["reason"] = f"TOO LONG ({length:.0f} CELLS, MAX {S.ROAD_MAX_CELLS:.0f})"
        return out
    if not (_reachable(world, *p0) or _reachable(world, *p1)):
        out["reason"] = "NEITHER END REACHABLE FOR ROVERS"
        return out
    for o in world.structures.values():
        if o.is_line():
            continue
        if ST.distance_to_segment(o.x, o.y, p0, p1) < o.spec["footprint_cells"] + SPEC["footprint_cells"]:
            out["reason"] = "BLOCKED BY " + o.spec["name"].upper()
            return out
    grade = 0.0
    steps = max(1, int(length))
    for i in range(steps + 1):   # one sample per cell along the middle of the road
        t = i / steps
        cx = int(round(p0[0] + (p1[0] - p0[0]) * t))
        cy = int(round(p0[1] + (p1[1] - p0[1]) * t))
        slope = world.slopes[cy * size + cx]
        if slope > S.ROAD_MAX_SLOPE_DEG:
            out["reason"] = f"TOO STEEP ({slope:.1f} DEG, ROADS MAX {S.ROAD_MAX_SLOPE_DEG:.0f})"
            return out
        grade += max(0.0, slope - SPEC["max_slope_deg"])
    cells = max(1, math.ceil(length - 1e-6))
    credits = SPEC["credits_per_cell"] * cells + ST.grade_credits(SPEC, grade)
    if world.credits < credits:
        out["reason"] = f"NEEDS {credits} CR"
        return out
    out.update(ok=True, length=length, grade_deg=grade, credits=credits)
    return out


def place(world, p0, p1):
    """Lay out a road site from p0 to p1. Returns (site or None, reason)."""
    p0, p1 = (float(p0[0]), float(p0[1])), (float(p1[0]), float(p1[1]))
    p = plan(world, p0, p1)
    if not p["ok"]:
        return None, p["reason"]
    # Constructors work from the middle, or from an end they can reach.
    mid = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
    x, y = next(q for q in (mid, p0, p1) if _reachable(world, *q))
    s = ST.Structure(world.new_id(), "road", x, y, built=False, created_tick=world.tick_count,
                     ends=[p0, p1], length=p["length"])
    s.grade_deg = p["grade_deg"]
    s.grade_cr = p["credits"]   # all of it comes back if the site is cancelled
    world.credits -= s.grade_cr
    world.structures[s.id] = s
    return s, ""


def refresh(world):
    """Rebuild the path grid's road cells from every finished road. Returns
    True if anything changed (routes and reachability are then recomputed)."""
    cells = set()
    for s in world.structures.values():
        if s.kind == "road" and s.built:
            cells.update(cells_under(world, *ST.line_of(world, s)))
    return world.grid.set_roads(cells)
