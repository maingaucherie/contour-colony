"""Surface debris: spawn weights, spawning and pickup. Never imports pygame.

Spawn weight = terrain weight per cell (open, not too steep; flat ground and
crater rims favoured) x a per-path-node weight for the charging network: zero
where a scavenger couldn't get there and back on a full battery, otherwise
falling off with distance to the nearest charging point. Only the node part
is recomputed when chargers are built, which keeps that cheap.
"""

import bisect
import math
from dataclasses import dataclass

from game.content import world as W


@dataclass(slots=True)
class Debris:
    id: int
    x: float
    y: float
    kind: str
    value: int
    claimed_by: int | None = None
    seen: bool = False      # hidden until a sensor, rover or scanner beam spots it


class SpawnMap:
    def __init__(self, heightmap, slopes, grid):
        size = heightmap.size
        self.size = size
        self.grid = grid
        rim = bytearray(size * size)
        lo, hi = W.DEBRIS_RIM_RANGE
        for cx, cy, r in heightmap.craters:
            reach = r * hi
            for y in range(max(0, int(cy - reach)), min(size, int(cy + reach) + 2)):
                for x in range(max(0, int(cx - reach)), min(size, int(cx + reach) + 2)):
                    if lo <= math.hypot(x - cx, y - cy) / r <= hi:
                        rim[y * size + x] = 1
        # Per node: its cells and their cumulative terrain weights.
        nodes = grid.n * grid.n
        self.node_cells = [[] for _ in range(nodes)]
        self.node_cum = [[] for _ in range(nodes)]
        for y in range(size):
            row = y * size
            for x in range(size):
                i = row + x
                s = slopes[i]
                node = grid.node_at(x, y)
                if s > W.SLOPE_ROAD_ONLY_DEG or not grid.open[node]:
                    continue
                w = W.DEBRIS_FLAT_BONUS if s < W.SLOPE_BUILDABLE_DEG else 1.0
                if rim[i]:
                    w *= W.DEBRIS_RIM_BONUS
                cum = self.node_cum[node]
                cum.append((cum[-1] if cum else 0.0) + w)
                self.node_cells[node].append(i)
        self.node_total = [c[-1] if c else 0.0 for c in self.node_cum]
        self.cumulative = [0.0] * nodes

    def update(self, charge_field, charger_xy, max_round_trip):
        """Recompute node weights for the current charging network."""
        two_sigma2 = 2.0 * W.DEBRIS_PROXIMITY_SIGMA_CELLS ** 2
        total = 0.0
        for node in range(len(self.cumulative)):
            base = self.node_total[node]
            if base > 0.0 and 2.0 * charge_field.dist[node] <= max_round_trip:
                x, y = self.grid.node_centre(node)
                d2 = min(((x - cx) ** 2 + (y - cy) ** 2 for cx, cy in charger_xy), default=0.0)
                total += base * max(math.exp(-d2 / two_sigma2), W.DEBRIS_PROXIMITY_FLOOR)
            self.cumulative[node] = total

    def total(self):
        return self.cumulative[-1] if self.cumulative else 0.0

    def cell_weight(self, cell_index):
        """Effective weight of one cell (0 if it can't receive debris)."""
        node = self.grid.node_at(cell_index % self.size, cell_index // self.size)
        node_w = self.cumulative[node] - (self.cumulative[node - 1] if node else 0.0)
        if node_w <= 0.0:
            return 0.0
        cells = self.node_cells[node]
        if cell_index not in cells:
            return 0.0
        k = cells.index(cell_index)
        cum = self.node_cum[node]
        return cum[k] - (cum[k - 1] if k else 0.0)

    def sample(self, rng):
        total = self.total()
        if total <= 0.0:
            return None
        node = min(bisect.bisect_right(self.cumulative, rng.random() * total), len(self.cumulative) - 1)
        cum = self.node_cum[node]
        if not cum:
            return None
        k = min(bisect.bisect_right(cum, rng.random() * cum[-1]), len(cum) - 1)
        return self.node_cells[node][k]


def try_spawn(world):
    """Place one debris object by weighted sampling. Returns it, or None."""
    size = world.heightmap.size
    rng = world.rng
    spacing2 = W.DEBRIS_MIN_SPACING_CELLS ** 2
    for _ in range(W.DEBRIS_SPAWN_ATTEMPTS):
        i = world.spawn_map.sample(rng)
        if i is None:
            return None
        cy, cx = divmod(i, size)
        x = min(max(cx + rng.random() - 0.5, 0.0), size - 1.0)
        y = min(max(cy + rng.random() - 0.5, 0.0), size - 1.0)
        if any((d.x - x) ** 2 + (d.y - y) ** 2 < spacing2 for d in world.debris.values()):
            continue
        if any(math.hypot(s.x - x, s.y - y) < s.spec["footprint_cells"] + W.DEBRIS_MIN_SPACING_CELLS
               for s in world.structures.values()):
            continue
        node = world.grid.node_at(x, y)
        if not world.grid.open[node] or world.charge_field.dist[node] == math.inf:
            continue  # the jitter nudged it into ground rovers can't reach
        piece = Debris(world.new_id(), x, y, rng.choice(W.DEBRIS_KINDS), W.DEBRIS_SCRAP_VALUE)
        world.debris[piece.id] = piece
        for s in world.structures.values():
            if s.built and math.hypot(s.x - x, s.y - y) <= s.spec.get("sight_cells", 0.0):
                piece.seen = True
        world.scrap_spawned += piece.value
        return piece
    return None


def update(world):
    """Respawn one piece every interval while below the cap."""
    world.debris_timer -= 1
    if world.debris_timer <= 0:
        world.debris_timer = round(W.DEBRIS_SPAWN_INTERVAL_S * W.TICK_RATE)
        if len(world.debris) < W.DEBRIS_MAX:
            try_spawn(world)
