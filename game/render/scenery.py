"""Scenery: low-detail terrain around the site, so it reads as one patch of a
larger body rather than a square floating in black. Pure Python, no pygame.

Heights are sampled on a coarse grid (SCENERY_STEP_CELLS apart) over a band
SCENERY_MARGIN_CELLS wide around the site. At the site's edge they equal the
site's own heights, so contour lines carry on across the border; further out
they blend into independent noise with a few craters. Contours use the
site's interval but only every SCENERY_LEVEL_STEP-th level, and are drawn
fading out with distance (see draw.py). Nothing is simulated out there.
"""

import math
import random

from game.content import terrain as T
from game.render import contours as C


def _smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


class _ValueNoise:
    """Fractal value noise on an integer lattice, seeded."""

    def __init__(self, seed):
        self.seed = seed

    def _lattice(self, i, j):
        h = (i * 374761393 + j * 668265263 + self.seed * 982451653) & 0xFFFFFFFF
        h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
        return (h & 0xFFFF) / 65535.0 * 2.0 - 1.0

    def _smooth(self, x, y):
        i, j = math.floor(x), math.floor(y)
        fx, fy = x - i, y - j
        sx, sy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
        a, b = self._lattice(i, j), self._lattice(i + 1, j)
        c, d = self._lattice(i, j + 1), self._lattice(i + 1, j + 1)
        return (a + (b - a) * sx) + ((c + (d - c) * sx) - (a + (b - a) * sx)) * sy

    def fractal(self, x, y, period, octaves):
        total, amp, norm = 0.0, 1.0, 0.0
        for _ in range(octaves):
            total += self._smooth(x / period, y / period) * amp
            norm += amp
            amp *= 0.5
            period /= 2.0
        return total / norm


class Scenery:
    def __init__(self, interval, levels):
        self.interval = interval
        self.levels = levels          # [(k, [Polyline])], world (cell) coordinates


def build_scenery(heightmap, interval, seed):
    """Generator: yields progress in [0, 1], returns a Scenery."""
    size = heightmap.size
    edge = size - 1
    m, step = T.SCENERY_MARGIN_CELLS, T.SCENERY_STEP_CELLS
    n = int((edge + 2 * m) / step) + 1
    noise = _ValueNoise(seed)
    rng = random.Random(f"{seed}/scenery")
    mid = (heightmap.min_h + heightmap.max_h) / 2
    amp = (heightmap.max_h - heightmap.min_h) * T.SCENERY_RELIEF
    craters = []
    for _ in range(T.SCENERY_CRATERS):
        r = rng.uniform(*T.SCENERY_CRATER_RADIUS_CELLS)
        while True:
            cx, cy = rng.uniform(-m, edge + m), rng.uniform(-m, edge + m)
            if not (-r < cx < edge + r and -r < cy < edge + r):
                break
        craters.append((cx, cy, r, amp * rng.uniform(0.5, 1.0)))
    heights = [0.0] * (n * n)
    for j in range(n):
        y = -m + j * step
        for i in range(n):
            x = -m + i * step
            cxl, cyl = min(max(x, 0.0), edge), min(max(y, 0.0), edge)
            base = heightmap.sample(cxl, cyl)
            d = math.hypot(x - cxl, y - cyl)                     # distance outside the site
            far = mid + amp * noise.fractal(x, y, T.SCENERY_NOISE_PERIOD_CELLS, 4)
            for ccx, ccy, r, depth in craters:
                q = math.hypot(x - ccx, y - ccy) / r
                if q < 1.4:
                    far += depth * (-(1 - q * q) if q < 1.0 else 0.35 * math.sin((q - 1.0) / 0.4 * math.pi))
            w = _smoothstep(d / T.SCENERY_BLEND_CELLS)
            heights[j * n + i] = base * (1 - w) + far * w
        if j % 16 == 0:
            yield 0.6 * j / n
    # March the whole coarse grid, keeping only segments outside the site.
    marched = C.march_chunk(heights, n, 0, 0, n - 1, n - 1, interval)
    yield 0.75

    def world(p):
        return -m + p[0] * step, -m + p[1] * step

    def inside(p):
        x, y = world(p)
        return 0.0 < x < edge and 0.0 < y < edge

    levels = []
    for k, (segs, points) in sorted(marched.items()):
        if k % T.SCENERY_LEVEL_STEP:
            continue
        outside = [(a, b) for a, b in segs if not (inside(points[a]) and inside(points[b]))]
        kept = []
        for pts in C.stitch(outside, points):
            s = C.simplify([world(p) for p in pts], T.SCENERY_TOLERANCE_CELLS)
            if s is not None and len(s) >= 2:
                kept.extend(C._polyline(p) for p in C.pieces(s))
        if kept:
            levels.append((k, kept))
    yield 1.0
    return Scenery(interval, levels)
