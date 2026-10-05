"""Contour geometry: marching squares, stitching, simplification, chunks and tiers.

Pure Python (no pygame) so it can be tested headlessly. Coordinates are in
cell units: height sample (i, j) sits at world position (i, j).

A level is an integer k; its height is k * interval. Each chunk stores, per
detail tier, the levels in that tier and their simplified polylines.
"""

import math
from dataclasses import dataclass, field

from game.content import terrain as T


@dataclass(slots=True)
class Polyline:
    points: list  # [(x, y), ...]; closed loops repeat the first point at the end
    min_x: float
    min_y: float
    max_x: float
    max_y: float
    mx: float = 0.0  # midpoint, for sampling survey knowledge
    my: float = 0.0


@dataclass(slots=True)
class ChunkContours:
    cx: int
    cy: int
    x0: int  # sample index range covered, inclusive
    y0: int
    x1: int
    y1: int
    tiers: list = field(default_factory=list)  # per tier: [(k, [Polyline, ...]), ...]


@dataclass(slots=True)
class ContourSet:
    interval: float
    k_min: int
    k_max: int
    chunk_cells: int
    chunks_per_side: int
    chunks: list  # row-major ChunkContours
    tier_specs: tuple


def nice_interval(height_range: float, target_levels: int = T.CONTOUR_TARGET_LEVELS,
                  steps=T.CONTOUR_NICE_STEPS) -> float:
    """The 'nice' interval (step x 10^n) whose level count is closest to target_levels."""
    if height_range <= 0:
        return steps[0]
    raw = height_range / target_levels
    exponent = math.floor(math.log10(raw))
    candidates = [step * 10.0 ** e for e in (exponent - 1, exponent, exponent + 1) for step in steps]
    return min(candidates, key=lambda c: abs(math.log(raw / c)))


def level_range(min_h: float, max_h: float, interval: float):
    """Levels k with min_h <= k * interval < max_h (those that can cross a cell)."""
    return math.ceil(min_h / interval), math.ceil(max_h / interval) - 1


def march_chunk(heights, size, x0, y0, x1, y1, interval):
    """Marching squares over cells [x0, x1) x [y0, y1) for every level.

    Returns {k: ([(key_a, key_b), ...], {key: (x, y)})}. An edge key names a
    grid edge (horizontal from sample (i, j) to (i+1, j), or vertical from
    (i, j) to (i, j+1)), so neighbouring cells and chunks agree on it exactly.
    A corner counts as above the level when its height is strictly greater.
    """
    levels = {}

    def edge_point(key, k_height):
        base, vertical = divmod(key, 2)
        j, i = divmod(base, size)
        h0 = heights[base]
        h1 = heights[base + size] if vertical else heights[base + 1]
        t = (k_height - h0) / (h1 - h0)
        return (i, j + t) if vertical else (i + t, j)

    for j in range(y0, y1):
        row = j * size
        for i in range(x0, x1):
            ia = row + i
            a = heights[ia]
            b = heights[ia + 1]
            c = heights[ia + size + 1]
            d = heights[ia + size]
            lo = min(a, b, c, d)
            hi = max(a, b, c, d)
            k_lo = math.ceil(lo / interval)
            k_hi = math.ceil(hi / interval) - 1
            if k_hi < k_lo:
                continue
            top = ia * 2
            left = ia * 2 + 1
            right = (ia + 1) * 2 + 1
            bottom = (ia + size) * 2
            for k in range(k_lo, k_hi + 1):
                lv = k * interval
                above_a, above_b, above_c, above_d = a > lv, b > lv, c > lv, d > lv
                crossed = []
                if above_a != above_b:
                    crossed.append(top)
                if above_b != above_c:
                    crossed.append(right)
                if above_d != above_c:
                    crossed.append(bottom)
                if above_a != above_d:
                    crossed.append(left)
                if not crossed:
                    continue
                level = levels.get(k)
                if level is None:
                    level = levels[k] = ([], {})
                segs, points = level
                for key in crossed:
                    if key not in points:
                        points[key] = edge_point(key, lv)
                if len(crossed) == 2:
                    segs.append((crossed[0], crossed[1]))
                else:
                    # Saddle: the centre value decides which corners are cut off.
                    centre_above = (a + b + c + d) * 0.25 > lv
                    if above_a == centre_above:
                        # a and c joined through the centre; b and d are isolated.
                        segs.append((top, right))
                        segs.append((bottom, left))
                    else:
                        segs.append((left, top))
                        segs.append((right, bottom))
    return levels


def stitch(segments, points):
    """Join undirected segments that share edge keys into polylines."""
    adj = {}
    for a, b in segments:
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)

    def walk(start):
        line = [start]
        cur = start
        while adj[cur]:
            nxt = adj[cur].pop()
            adj[nxt].remove(cur)
            line.append(nxt)
            cur = nxt
        return line

    lines = []
    for key in list(adj):  # open lines first, starting from their ends
        if len(adj[key]) == 1:
            lines.append(walk(key))
    for key in list(adj):  # what remains is closed loops
        if adj[key]:
            lines.append(walk(key))

    out = []
    for keys in lines:
        pts = []
        for key in keys:
            p = points[key]
            if not pts or pts[-1] != p:
                pts.append(p)
        if len(pts) >= 2:
            out.append(pts)
    return out


def _segment_dist2(p, a, b):
    ax, ay = a
    dx, dy = b[0] - ax, b[1] - ay
    px, py = p[0] - ax, p[1] - ay
    length2 = dx * dx + dy * dy
    if length2 > 0.0:
        t = max(0.0, min(1.0, (px * dx + py * dy) / length2))
        px -= t * dx
        py -= t * dy
    return px * px + py * py


def _rdp(pts, tol2):
    n = len(pts)
    if n < 3:
        return list(pts)
    keep = [False] * n
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        s, e = stack.pop()
        a, b = pts[s], pts[e]
        best, best_i = tol2, -1
        for i in range(s + 1, e):
            d2 = _segment_dist2(pts[i], a, b)
            if d2 > best:
                best, best_i = d2, i
        if best_i >= 0:
            keep[best_i] = True
            stack.append((s, best_i))
            stack.append((best_i, e))
    return [p for p, k in zip(pts, keep) if k]


def simplify(pts, tolerance):
    """Ramer-Douglas-Peucker. Endpoints are kept, so chunk seams still meet.

    Closed loops are split at the point farthest from the start. Returns None
    when a closed loop collapses below a triangle.
    """
    tol2 = tolerance * tolerance
    if len(pts) > 3 and pts[0] == pts[-1]:
        x0, y0 = pts[0]
        far = max(range(len(pts)), key=lambda i: (pts[i][0] - x0) ** 2 + (pts[i][1] - y0) ** 2)
        out = _rdp(pts[: far + 1], tol2) + _rdp(pts[far:], tol2)[1:]
        return out if len(out) >= 4 else None
    if len(pts) >= 2 and pts[0] == pts[-1]:
        return None
    return _rdp(pts, tol2)


def _polyline(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return Polyline(pts, min(xs), min(ys), max(xs), max(ys), sum(xs) / len(xs), sum(ys) / len(ys))


def pieces(pts, max_segments=T.CONTOUR_PIECE_SEGMENTS):
    """Cut a polyline into consecutive pieces sharing their end points."""
    out = []
    i = 0
    while i < len(pts) - 1:
        out.append(pts[i: i + max_segments + 1])
        i += max_segments
    return out


def level_rank(k, tier_specs=T.CONTOUR_TIERS):
    """The coarsest tier that contains level k (0 = every 4th level ... 2 = all)."""
    for i, spec in enumerate(tier_specs):
        if k % spec["level_step"] == 0:
            return i
    return len(tier_specs) - 1


def build_chunk(heights, size, cx, cy, interval, tier_specs=T.CONTOUR_TIERS,
                chunk_cells=T.CONTOUR_CHUNK_CELLS):
    """March, stitch and simplify one chunk for every tier."""
    x0, y0 = cx * chunk_cells, cy * chunk_cells
    x1, y1 = min(x0 + chunk_cells, size - 1), min(y0 + chunk_cells, size - 1)
    chunk = ChunkContours(cx, cy, x0, y0, x1, y1)
    levels = march_chunk(heights, size, x0, y0, x1, y1, interval)
    stitched = {k: stitch(segs, points) for k, (segs, points) in sorted(levels.items())}
    for spec in tier_specs:
        step, tol = spec["level_step"], spec["tolerance_cells"]
        levels = []
        for k, lines in stitched.items():
            if k % step:
                continue
            kept = []
            for pts in lines:
                s = simplify(pts, tol)
                if s is not None and len(s) >= 2:
                    kept.extend(_polyline(p) for p in pieces(s))
            if kept:
                levels.append((k, kept))
        chunk.tiers.append(levels)
    return chunk


def build_contours(heightmap, tier_specs=T.CONTOUR_TIERS, chunk_cells=T.CONTOUR_CHUNK_CELLS):
    """Generator: yields progress in [0, 1], returns a ContourSet."""
    size = heightmap.size
    interval = nice_interval(heightmap.max_h - heightmap.min_h)
    k_min, k_max = level_range(heightmap.min_h, heightmap.max_h, interval)
    per_side = math.ceil((size - 1) / chunk_cells)
    chunks = []
    total = per_side * per_side
    for cy in range(per_side):
        for cx in range(per_side):
            chunks.append(build_chunk(heightmap.heights, size, cx, cy, interval, tier_specs, chunk_cells))
            yield len(chunks) / total
    return ContourSet(interval, k_min, k_max, chunk_cells, per_side, chunks, tier_specs)


def tier_for_zoom(zoom: float, tier_specs=T.CONTOUR_TIERS) -> int:
    tier = 0
    for i, spec in enumerate(tier_specs):
        if zoom >= spec["min_zoom"]:
            tier = i
    return tier
