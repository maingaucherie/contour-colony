"""Worn tracks: how much each patch of ground has been driven over, and in
which direction. Never imports pygame.

Ground is divided into squares of TRACK_CELLS cells. Every tick a moving unit
adds wear to the square under it, along with its heading as a doubled-angle
vector, so driving there and back adds up instead of cancelling. Wear fades
slowly, so routes nobody uses any more disappear. For now tracks are only
drawn; graded roads could later grow out of them.
"""

import math

from game.content import world as W


class Tracks:
    def __init__(self, size):
        self.res = W.TRACK_CELLS
        self.n = math.ceil(size / self.res)
        self.cells = {}          # square index -> [wear, cos 2a sum, sin 2a sum]
        self.version = 0         # bumps whenever wear changes visibly, for renderers

    def drive(self, x, y, heading):
        n, res = self.n, self.res
        i = min(max(int(y / res), 0), n - 1) * n + min(max(int(x / res), 0), n - 1)
        cell = self.cells.get(i)
        if cell is None:
            cell = self.cells[i] = [0.0, 0.0, 0.0]
        if cell[0] < W.TRACK_WEAR_MAX:
            cell[0] += 1.0
        cell[1] += math.cos(2 * heading)
        cell[2] += math.sin(2 * heading)

    def fade(self):
        """Called every TRACK_FADE_EVERY_S: old wear fades, faint squares go."""
        k = W.TRACK_FADE
        for i in list(self.cells):
            cell = self.cells[i]
            cell[0] *= k
            cell[1] *= k
            cell[2] *= k
            if cell[0] < W.TRACK_FORGET:
                del self.cells[i]
        self.version += 1

    def visible(self):
        """[(x, y, angle, strength 0..1)] for squares worn enough to show."""
        res, n = self.res, self.n
        lo, hi = W.TRACK_SHOW_WEAR, W.TRACK_FULL_WEAR
        out = []
        for i, (wear, c2, s2) in self.cells.items():
            if wear < lo:
                continue
            y, x = divmod(i, n)
            out.append(((x + 0.5) * res, (y + 0.5) * res, math.atan2(s2, c2) / 2,
                        min(1.0, (wear - lo) / (hi - lo))))
        return out
