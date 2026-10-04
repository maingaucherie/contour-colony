"""Surface debris: spawn weights, spawning and pickup. Never imports pygame."""

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


def spawn_weights(heightmap, slopes, grid, home_field, home_xy, max_round_trip):
    """Cumulative spawn weight per terrain cell.

    Only open ground within max_round_trip cost-cells (there and back) of home
    gets weight. Flat ground and crater rims are favoured, and weight falls
    off with distance from home down to a floor.
    """
    size = heightmap.size
    rim = bytearray(size * size)
    lo, hi = W.DEBRIS_RIM_RANGE
    for cx, cy, r in heightmap.craters:
        reach = r * hi
        for y in range(max(0, int(cy - reach)), min(size, int(cy + reach) + 2)):
            for x in range(max(0, int(cx - reach)), min(size, int(cx + reach) + 2)):
                if lo <= math.hypot(x - cx, y - cy) / r <= hi:
                    rim[y * size + x] = 1

    hx, hy = home_xy
    two_sigma2 = 2.0 * W.DEBRIS_PROXIMITY_SIGMA_CELLS ** 2
    cumulative = [0.0] * (size * size)
    total = 0.0
    for y in range(size):
        row = y * size
        for x in range(size):
            i = row + x
            s = slopes[i]
            node = grid.node_at(x, y)
            if (s <= W.SLOPE_ROAD_ONLY_DEG and grid.open[node]
                    and 2.0 * home_field.dist[node] <= max_round_trip):
                w = W.DEBRIS_FLAT_BONUS if s < W.SLOPE_BUILDABLE_DEG else 1.0
                if rim[i]:
                    w *= W.DEBRIS_RIM_BONUS
                d2 = (x - hx) ** 2 + (y - hy) ** 2
                w *= max(math.exp(-d2 / two_sigma2), W.DEBRIS_PROXIMITY_FLOOR)
                total += w
            cumulative[i] = total
    return cumulative


def try_spawn(world):
    """Place one debris object by weighted sampling. Returns it, or None."""
    cumulative = world.debris_weights
    total = cumulative[-1]
    if total <= 0.0:
        return None
    size = world.heightmap.size
    rng = world.rng
    spacing2 = W.DEBRIS_MIN_SPACING_CELLS ** 2
    for _ in range(W.DEBRIS_SPAWN_ATTEMPTS):
        i = bisect.bisect_right(cumulative, rng.random() * total)
        i = min(i, len(cumulative) - 1)
        cy, cx = divmod(i, size)
        x = min(max(cx + rng.random() - 0.5, 0.0), size - 1.0)
        y = min(max(cy + rng.random() - 0.5, 0.0), size - 1.0)
        if any((d.x - x) ** 2 + (d.y - y) ** 2 < spacing2 for d in world.debris.values()):
            continue
        piece = Debris(world.new_id(), x, y, rng.choice(W.DEBRIS_KINDS), W.DEBRIS_SCRAP_VALUE)
        world.debris[piece.id] = piece
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
