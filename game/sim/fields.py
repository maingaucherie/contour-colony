"""Resource fields: hidden mineral and ice deposits. Never imports pygame.

A field is a blob with a smooth, wobbly edge: radius r(theta) = radius *
(1 + wobble * f(theta)). Membership and the boundary polyline both come from
that formula, so the boundary can be revealed piece by piece as it is surveyed.
"""

import math
from dataclasses import dataclass, field

from game.content import world as W
from game.sim import geology as G

BOUNDARY_POINTS = 48


@dataclass(slots=True)
class Field:
    id: int
    kind: str              # "ilmenite", "anorthite", "kreep" or "ice"
    cx: float
    cy: float
    radius: float
    richness: float
    phases: tuple          # edge wobble phases
    hint_dx: float = 0.0   # the level-1 hint is a fuzzy ring, offset from the truth
    hint_dy: float = 0.0
    hinted: bool = False
    confirmed: bool = False
    signal_passes: int = 0  # scanner beam passes over it
    survey_done: bool = False  # every reachable part surveyed in detail (cliffs may hide the rest)
    mined: int = 0             # mine cycles taken from it

    def reserve(self):
        return W.FIELD_RESERVE_CYCLES * self.richness * (self.radius / 5.0) ** 2

    def reserves_left(self):
        """Fraction of the reserve not yet mined, 0..1."""
        return max(0.0, 1.0 - self.mined / self.reserve())

    def yield_factor(self):
        """Mine speed multiplier: richness, falling to a floor as it runs out."""
        floor = W.FIELD_DEPLETED_FLOOR
        return self.richness * (floor + (1 - floor) * self.reserves_left())
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


def _count(kind, size, rng):
    lo, hi = W.FIELD_COUNTS[kind]
    scale = (size / W.FIELD_COUNT_SIZE) ** 2
    return max(1, round(rng.randint(lo, hi) * scale))


def generate(world, rng):
    """Place each mineral's fields in its zone (geology.py): ilmenite on the
    maria (the first one near the lander), anorthite in the highlands, KREEP
    in its province, ice at the darkest reachable spot of each cold trap."""
    hm, slopes, grid = world.heightmap, world.slopes, world.grid
    size = hm.size
    geo = hm.geology
    lx, ly = world.lander.x, world.lander.y
    fields = []

    def ok_spot(x, y, radius):
        if not (radius < x < size - 1 - radius and radius < y < size - 1 - radius):
            return False
        # A drill must fit at the centre: its whole footprint on buildable ground.
        r = W.FIELD_FLAT_RADIUS_CELLS
        for cy in range(int(y - r), int(y + r) + 2):
            for cx in range(int(x - r), int(x + r) + 2):
                if math.hypot(cx - x, cy - y) <= r + 0.5 and slopes[cy * size + cx] > W.FIELD_MAX_SLOPE_DEG:
                    return False
        node = grid.node_at(x, y)
        if not (grid.open[node] and world.home_field.reachable(node)):
            return False
        if math.hypot(x - lx, y - ly) < radius + W.FIELD_MIN_SPACING_CELLS / 2:
            return False
        return all(math.hypot(x - f.cx, y - f.cy) > f.radius + radius + W.FIELD_MIN_SPACING_CELLS
                   for f in fields)

    def place(kind, count, candidate, zone=None):
        """Try random candidate spots; the first half of the tries must be in zone."""
        for k in range(count):
            radius = rng.uniform(*W.FIELD_RADIUS_CELLS[kind])
            for attempt in range(W.FIELD_CANDIDATES):
                x, y = candidate(k)
                strict = zone is not None and attempt < W.FIELD_CANDIDATES // 2
                if ok_spot(x, y, radius) and (not strict or G.zone_at(geo, x, y) == zone):
                    fields.append(_make(len(fields) + 1, kind, x, y, radius, rng))
                    break

    def anywhere(k):
        return rng.uniform(0, size - 1), rng.uniform(0, size - 1)

    def ilmenite_spot(k):
        if k == 0:  # the first is a short drive from the lander
            d = rng.uniform(*W.FIELD_NEAR_LANDER_CELLS)
            a = rng.uniform(0, 2 * math.pi)
            return lx + d * math.cos(a), ly + d * math.sin(a)
        return anywhere(k)

    def kreep_spot(k):
        kx, ky, kr = geo.kreep
        a, d = rng.uniform(0, 2 * math.pi), kr * math.sqrt(rng.random())
        return kx + d * math.cos(a), ky + d * math.sin(a)

    place("ilmenite", _count("ilmenite", size, rng), ilmenite_spot, G.MARE)
    place("anorthite", _count("anorthite", size, rng), anywhere, G.HIGHLANDS)
    place("kreep", _count("kreep", size, rng), kreep_spot, G.KREEP)

    # Ice: in each cold trap (floor, foot of the wall, rim: wherever a drill
    # fits), at the most shadowed reachable spot. If the traps can't hold
    # enough, the largest other craters on the pole half of the site.
    want = _count("ice", size, rng)
    lo_r, hi_r = W.ICE_FLOOR_RING
    mid = size / 2

    def floor_spot(cx, cy, r, radius):
        best = None
        for _ in range(W.ICE_FLOOR_SAMPLES):
            a = rng.uniform(0, 2 * math.pi)
            d = r * rng.uniform(lo_r, hi_r)
            x, y = cx + d * math.cos(a), cy + d * math.sin(a)
            if ok_spot(x, y, radius):
                light = world.illumination_at(x, y)
                if best is None or light < best[0]:
                    best = (light, x, y)
        return best

    def pole_side(c):
        return (c[0] - mid) * geo.pole[0] + (c[1] - mid) * geo.pole[1] > 0

    others = sorted((c for c in hm.craters if c not in geo.cold_traps and pole_side(c)
                     and c[2] >= W.ICE_MIN_CRATER_RADIUS_CELLS), key=lambda c: -c[2])
    for cx, cy, r in list(geo.cold_traps) + others:
        if sum(1 for f in fields if f.kind == "ice") >= want:
            break
        radius = max(W.ICE_MIN_RADIUS_CELLS, r * rng.uniform(*W.ICE_RADIUS_FRACTION))
        best = floor_spot(cx, cy, r, radius)
        if best is not None:
            fields.append(_make(len(fields) + 1, "ice", best[1], best[2], radius, rng))
    return fields


def field_at(fields, x, y, kind=None):
    for f in fields:
        if (kind is None or f.kind == kind) and f.contains(x, y):
            return f
    return None
