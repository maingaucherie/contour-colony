"""Survey levels: what the commander knows about each patch of ground.

Levels live on a grid of SURVEY_CELLS x SURVEY_CELLS terrain cells:
0 orbital (coarse contours, no fields), 1 surveyed (normal contours, field
hints), 2 detailed (fine contours, exact field boundaries, mines allowed).
Never imports pygame.
"""

import math

from game.content import world as W


class SurveyMap:
    def __init__(self, size, chunk_cells):
        self.size = size
        self.res = W.SURVEY_CELLS
        self.n = math.ceil(size / self.res)
        self.levels = bytearray(self.n * self.n)
        self.chunk_cells = chunk_cells
        self.chunks_per_side = math.ceil((size - 1) / chunk_cells)
        self.version = 0          # bumps on every change, for renderers and caches
        self._chunk_cache = None
        self._chunk_version = -1

    def index_at(self, x, y):
        sx = min(max(int(x / self.res), 0), self.n - 1)
        sy = min(max(int(y / self.res), 0), self.n - 1)
        return sy * self.n + sx

    def level_at(self, x, y):
        return self.levels[self.index_at(x, y)]

    def raise_area(self, x, y, radius, level):
        """Raise every survey cell whose centre is within radius to at least level.
        Returns the list of indices that changed."""
        res = self.res
        changed = []
        r2 = radius * radius
        x0 = max(0, int((x - radius) / res))
        x1 = min(self.n - 1, int((x + radius) / res))
        y0 = max(0, int((y - radius) / res))
        y1 = min(self.n - 1, int((y + radius) / res))
        for sy in range(y0, y1 + 1):
            cy = (sy + 0.5) * res
            for sx in range(x0, x1 + 1):
                cx = (sx + 0.5) * res
                if (cx - x) ** 2 + (cy - y) ** 2 <= r2:
                    i = sy * self.n + sx
                    if self.levels[i] < level:
                        self.levels[i] = level
                        changed.append(i)
        if changed:
            self.version += 1
        return changed

    def chunk_levels(self):
        """Highest survey level inside each contour chunk (row-major), cached."""
        if self._chunk_version == self.version:
            return self._chunk_cache
        per = self.chunks_per_side
        out = [0] * (per * per)
        step = self.chunk_cells / self.res
        for sy in range(self.n):
            cy = min(int(sy / step), per - 1)
            row = sy * self.n
            for sx in range(self.n):
                level = self.levels[row + sx]
                if level:
                    ci = cy * per + min(int(sx / step), per - 1)
                    if level > out[ci]:
                        out[ci] = level
        self._chunk_cache, self._chunk_version = out, self.version
        return out

    def coverage(self, level):
        """Fraction of the site surveyed to at least level."""
        return sum(1 for v in self.levels if v >= level) / len(self.levels)
