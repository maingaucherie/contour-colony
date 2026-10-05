"""Resource fields: hidden ilmenite and ice deposits. Never imports pygame.

A field is a blob with a smooth, wobbly edge: radius r(theta) = radius *
(1 + wobble * f(theta)). Membership and the boundary polyline both come from
that formula, so the boundary can be revealed piece by piece as it is surveyed.
"""

import math
from dataclasses import dataclass, field

from game.content import world as W

BOUNDARY_POINTS = 48


@dataclass(slots=True)
class Field:
    id: int
    kind: str              # "ilmenite" or "ice"
    cx: float
    cy: float
    radius: float
    richness: float
    phases: tuple          # edge wobble phases
    hint_dx: float = 0.0   # the level-1 hint is a fuzzy ring, offset from the truth
    hint_dy: float = 0.0
    hinted: bool = False
    confirmed: bool = False
    boundary: list = field(default_factory=list)  # closed polyline [(x, y), ...]

    def edge(self, theta):
        p1, p2, p3 = self.phases
        f = 0.5 * math.sin(3 * theta + p1) + 0.3 * math.sin(5 * theta + p2) + 0.2 * math.sin(2 * theta + p3)
        return self.radius * (1.0 + W.FIELD_EDGE_WOBBLE * f)

    def contains(self, x, y):
        dx, dy = x - self.cx, y - self.cy
        d = math.hypot(dx, dy)
        if d > self.radius * (1.0 + W.FIELD_EDGE_WOBBLE):
            return False
        return d <= self.edge(math.atan2(dy, dx))

    def sample_points(self, spacing):
        """Grid of points inside the field, for survey targeting."""
        pts = []
        r = self.radius * (1.0 + W.FIELD_EDGE_WOBBLE)
        steps = int(r / spacing)
        for j in range(-steps, steps + 1):
            for i in range(-steps, steps + 1):
                x, y = self.cx + i * spacing, self.cy + j * spacing
                if self.contains(x, y):
                    pts.append((x, y))
        return pts or [(self.cx, self.cy)]


def _make(fid, kind, x, y, radius, rng):
    f = Field(fid, kind, x, y, radius, round(rng.uniform(*W.FIELD_RICHNESS), 1),
              tuple(rng.uniform(0, 2 * math.pi) for _ in range(3)))
    a = rng.uniform(0, 2 * math.pi)
    off = rng.uniform(0.15, 0.35) * radius
    f.hint_dx, f.hint_dy = off * math.cos(a), off * math.sin(a)
    f.boundary = [(x + f.edge(t) * math.cos(t), y + f.edge(t) * math.sin(t))
                  for t in (2 * math.pi * k / BOUNDARY_POINTS for k in range(BOUNDARY_POINTS))]
    f.boundary.append(f.boundary[0])
    return f


def generate(world, rng):
    """Place ilmenite fields (mare flats and crater ejecta) and ice fields (deep,
    shadowed crater floors). The first ilmenite field is near the lander."""
    hm, slopes, grid = world.heightmap, world.slopes, world.grid
    size = hm.size
    lx, ly = world.lander.x, world.lander.y
    fields = []
    # Mare-like flats: the lower part of the height range.
    sorted_h = sorted(hm.heights[::97])
    low_cut = sorted_h[int(len(sorted_h) * 0.4)]
    craters = hm.craters

    def ok_spot(x, y, radius):
        if not (radius < x < size - 1 - radius and radius < y < size - 1 - radius):
            return False
        ix, iy = int(x), int(y)
        if slopes[iy * size + ix] > W.FIELD_MAX_SLOPE_DEG:
            return False
        node = grid.node_at(x, y)
        if not (grid.open[node] and world.home_field.reachable(node)):
            return False
        if math.hypot(x - lx, y - ly) < radius + W.FIELD_MIN_SPACING_CELLS / 2:
            return False
        return all(math.hypot(x - f.cx, y - f.cy) > f.radius + radius + W.FIELD_MIN_SPACING_CELLS
                   for f in fields)

    def ilmenite_like(x, y):
        if hm.at(int(x), int(y)) <= low_cut:
            return True
        return any(1.2 <= math.hypot(x - cx, y - cy) / r <= 2.0 for cx, cy, r in craters if r >= 4)

    count = rng.randint(*W.ILMENITE_FIELD_COUNT)
    for k in range(count):
        radius = rng.uniform(*W.ILMENITE_RADIUS_CELLS)
        for attempt in range(W.FIELD_CANDIDATES):
            if k == 0:
                d = rng.uniform(*W.FIELD_NEAR_LANDER_CELLS)
                a = rng.uniform(0, 2 * math.pi)
                x, y = lx + d * math.cos(a), ly + d * math.sin(a)
            else:
                x, y = rng.uniform(0, size - 1), rng.uniform(0, size - 1)
            strict = attempt < W.FIELD_CANDIDATES // 2
            if ok_spot(x, y, radius) and (not strict or ilmenite_like(x, y)):
                fields.append(_make(len(fields) + 1, "ilmenite", x, y, radius, rng))
                break

    # Ice: on the flat floor ring of large craters (between the central peak and
    # the wall), at the most shadowed reachable spot found.
    want = rng.randint(*W.ICE_FIELD_COUNT)
    hosts = sorted((c for c in craters if c[2] >= W.ICE_MIN_CRATER_RADIUS_CELLS), key=lambda c: -c[2])
    lo_r, hi_r = W.ICE_FLOOR_RING
    for cx, cy, r in hosts:
        if sum(1 for f in fields if f.kind == "ice") >= want:
            break
        radius = max(W.ICE_MIN_RADIUS_CELLS, r * rng.uniform(*W.ICE_RADIUS_FRACTION))
        best = None
        for _ in range(W.ICE_FLOOR_SAMPLES):
            a = rng.uniform(0, 2 * math.pi)
            d = r * rng.uniform(lo_r, hi_r)
            x, y = cx + d * math.cos(a), cy + d * math.sin(a)
            if ok_spot(x, y, radius):
                light = world.illumination_at(x, y)
                if best is None or light < best[0]:
                    best = (light, x, y)
        if best is not None:
            fields.append(_make(len(fields) + 1, "ice", best[1], best[2], radius, rng))
    return fields


def field_at(fields, x, y, kind=None):
    for f in fields:
        if (kind is None or f.kind == kind) and f.contains(x, y):
            return f
    return None
