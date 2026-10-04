"""Heightmap generation and terrain queries. Never imports pygame.

Generation runs as a generator that yields progress in [0, 1] and returns the
finished Heightmap, so the browser build can spread it over many frames.
"""

import math
import random
from array import array
from dataclasses import dataclass

from game.content import terrain as T


@dataclass(slots=True)
class Heightmap:
    size: int
    cell_m: float
    heights: array  # flat array('f'), row-major: index = y * size + x
    min_h: float
    max_h: float

    def at(self, x: int, y: int) -> float:
        return self.heights[y * self.size + x]

    def sample(self, x: float, y: float) -> float:
        """Bilinear height at a fractional cell position, clamped to the site."""
        n = self.size - 1
        x = min(max(x, 0.0), n)
        y = min(max(y, 0.0), n)
        ix, iy = min(int(x), n - 1), min(int(y), n - 1)
        tx, ty = x - ix, y - iy
        h = self.heights
        i = iy * self.size + ix
        top = h[i] + (h[i + 1] - h[i]) * tx
        bottom = h[i + self.size] + (h[i + self.size + 1] - h[i + self.size]) * tx
        return top + (bottom - top) * ty

    def slope_deg(self, x: float, y: float) -> float:
        """Slope in degrees from central differences one cell apart."""
        gx = (self.sample(x + 1, y) - self.sample(x - 1, y)) / (2 * self.cell_m)
        gy = (self.sample(x, y + 1) - self.sample(x, y - 1)) / (2 * self.cell_m)
        return math.degrees(math.atan(math.hypot(gx, gy)))


def run_to_completion(gen):
    """Drive a progress generator to the end and return its result."""
    while True:
        try:
            next(gen)
        except StopIteration as stop:
            return stop.value


def _smoothstep(t):
    return t * t * (3.0 - 2.0 * t)


def _crater_radius(rng):
    """Power-law radius: inverse-CDF sample of a Pareto distribution, truncated."""
    while True:
        u = rng.random()
        r = T.CRATER_RADIUS_MIN_CELLS * (1.0 - u) ** (-1.0 / T.CRATER_POWER_LAW_EXPONENT)
        if r <= T.CRATER_RADIUS_MAX_CELLS:
            return r


def generate_terrain(seed: int, size: int = T.GRID_SIZE):
    """Generator: yields progress in [0, 1], returns a Heightmap."""
    rng = random.Random(seed)
    h = [0.0] * (size * size)

    # Plan all features up front so progress can be measured in cells touched.
    basins = []
    for _ in range(rng.randint(*T.BASIN_COUNT_RANGE)):
        basins.append((
            rng.uniform(0, size), rng.uniform(0, size),
            rng.uniform(*T.BASIN_RADIUS_RANGE_CELLS),
            rng.uniform(*T.BASIN_DEPTH_RANGE_M),
        ))
    radii = [rng.uniform(*T.CRATER_LARGE_RADIUS_RANGE_CELLS) for _ in range(T.CRATER_GUARANTEED_LARGE)]
    radii += [_crater_radius(rng) for _ in range(T.CRATER_COUNT)]
    radii.sort(reverse=True)  # big first, so small craters overprint them
    craters = [(rng.uniform(0, size), rng.uniform(0, size), r) for r in radii]

    def box(cx, cy, reach):
        return (max(0, int(cx - reach)), min(size - 1, int(cx + reach) + 1),
                max(0, int(cy - reach)), min(size - 1, int(cy + reach) + 1))

    total = size * size
    total += sum((b[1] - b[0] + 1) * (b[3] - b[2] + 1) for b in (box(x, y, r) for x, y, r, _ in basins))
    total += sum((b[1] - b[0] + 1) * (b[3] - b[2] + 1)
                 for b in (box(x, y, r * T.CRATER_EJECTA_EXTENT) for x, y, r in craters))
    done = 0

    # 1. Fractal value noise, one row at a time.
    octaves = []
    period, amp = T.NOISE_BASE_PERIOD_CELLS, T.NOISE_AMPLITUDE_M
    for _ in range(T.NOISE_OCTAVES):
        m = int(size / period) + 2
        lattice = [rng.uniform(-1.0, 1.0) for _ in range(m * m)]
        cols = []
        for x in range(size):
            f = x / period
            i = int(f)
            cols.append((i, _smoothstep(f - i)))
        octaves.append((period, amp, m, lattice, cols))
        period /= T.NOISE_LACUNARITY
        amp *= T.NOISE_PERSISTENCE
    for y in range(size):
        row = y * size
        for period, amp, m, lattice, cols in octaves:
            f = y / period
            j = int(f)
            ty = _smoothstep(f - j)
            r0, r1 = j * m, (j + 1) * m
            for x in range(size):
                i, tx = cols[x]
                a = lattice[r0 + i]
                b = lattice[r0 + i + 1]
                top = a + (b - a) * tx
                c = lattice[r1 + i]
                d = lattice[r1 + i + 1]
                bottom = c + (d - c) * tx
                h[row + x] += amp * (top + (bottom - top) * ty)
        done += size
        yield done / total

    # 2. Flooded basins: carve a smooth bowl, then flatten below the flood level.
    for cx, cy, radius, depth in basins:
        x0, x1, y0, y1 = box(cx, cy, radius)
        inside = []
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                d = math.hypot(x - cx, y - cy) / radius
                if d < 1.0:
                    idx = y * size + x
                    h[idx] -= depth * 0.5 * (1.0 + math.cos(math.pi * d))
                    inside.append(idx)
        ci = min(size - 1, int(cy)) * size + min(size - 1, int(cx))
        level = h[ci] + depth * T.BASIN_FLOOD_FRACTION
        for idx in inside:
            if h[idx] < level:
                h[idx] = level + (h[idx] - level) * T.BASIN_FLOOD_RESIDUAL
        done += (x1 - x0 + 1) * (y1 - y0 + 1)
        yield done / total

    # 3. Craters, largest first.
    for cx, cy, radius in craters:
        depth = min(T.CRATER_DEPTH_PER_DIAMETER * 2 * radius * T.CELL_SIZE_M, T.CRATER_MAX_DEPTH_M)
        rim = depth * T.CRATER_RIM_RATIO
        complex_ = radius >= T.CRATER_COMPLEX_RADIUS_CELLS
        floor = T.CRATER_COMPLEX_FLOOR_FRACTION if complex_ else 0.0
        peak = depth * T.CRATER_COMPLEX_PEAK_RATIO if complex_ else 0.0
        peak_r = T.CRATER_COMPLEX_PEAK_RADIUS_FRACTION
        extent = T.CRATER_EJECTA_EXTENT
        ejecta_tail = extent ** -3

        # Reference height: mean of the terrain around the rim.
        ring = []
        for s in range(T.CRATER_RIM_SAMPLES):
            a = 2 * math.pi * s / T.CRATER_RIM_SAMPLES
            rx = min(max(int(cx + radius * math.cos(a)), 0), size - 1)
            ry = min(max(int(cy + radius * math.sin(a)), 0), size - 1)
            ring.append(h[ry * size + rx])
        base = sum(ring) / len(ring)

        x0, x1, y0, y1 = box(cx, cy, radius * extent)
        for y in range(y0, y1 + 1):
            row = y * size
            for x in range(x0, x1 + 1):
                d = math.hypot(x - cx, y - cy) / radius
                if d >= extent:
                    continue
                idx = row + x
                if d < 1.0:
                    if d < floor:
                        p = -depth
                    else:
                        t = (d - floor) / (1.0 - floor)
                        p = -depth + (depth + rim) * t * t
                    if d < peak_r:
                        p += peak * 0.5 * (1.0 + math.cos(math.pi * d / peak_r))
                    # Level the floor and inner walls against the rim height.
                    blend = T.CRATER_FLOOR_BLEND_INNER
                    m = 1.0 if d <= blend else _smoothstep((1.0 - d) / (1.0 - blend))
                    h[idx] = (h[idx] + p) * (1.0 - m) + (base + p) * m
                else:
                    h[idx] += rim * (d ** -3 - ejecta_tail) / (1.0 - ejecta_tail)
            done += x1 - x0 + 1
            yield done / total

    heights = array("f", h)
    return Heightmap(size, T.CELL_SIZE_M, heights, min(heights), max(heights))
