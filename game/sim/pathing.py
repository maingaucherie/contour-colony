"""Ground pathing on a coarse node grid. Never imports pygame.

Each node covers NODE_CELLS x NODE_CELLS terrain cells. Its cost is the mean
of (1 + slope / divisor) over those cells, which is the expected cost of
crossing one cell there, so edge costs are in "cost-cells" (see content/units).

Searches are Dijkstra fields rather than point-to-point A*: one field from a
unit prices every candidate target at once, and one field from a charger
gives every unit its way home. Fields are cached per source node.
"""

import heapq
import math
from collections import OrderedDict

from game.content import units as U
from game.content import world as W

_SQRT2 = math.sqrt(2.0)
_DIRS = ((1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
         (1, 1, _SQRT2), (1, -1, _SQRT2), (-1, 1, _SQRT2), (-1, -1, _SQRT2))


class Field:
    """Result of a Dijkstra search: cost to reach each node, and the previous node."""

    __slots__ = ("source", "dist", "prev")

    def __init__(self, source, dist, prev):
        self.source = source
        self.dist = dist
        self.prev = prev

    def reachable(self, node):
        return self.dist[node] < math.inf

    def nodes_from_source(self, goal):
        """Node chain source -> goal (inclusive)."""
        chain = []
        node = goal
        while node != -1:
            chain.append(node)
            node = self.prev[node]
        chain.reverse()
        return chain


class PathGrid:
    def __init__(self, size, slopes, node_cells=W.PATH_NODE_CELLS):
        self.size = size
        self.slopes = slopes
        self.node_cells = node_cells
        self.n = math.ceil(size / node_cells)
        self.cost = [0.0] * (self.n * self.n)
        self.open = [False] * (self.n * self.n)
        for ny in range(self.n):
            for nx in range(self.n):
                total, steep, count = 0.0, 0, 0
                for y in range(ny * node_cells, min((ny + 1) * node_cells, size)):
                    row = y * size
                    for x in range(nx * node_cells, min((nx + 1) * node_cells, size)):
                        s = slopes[row + x]
                        total += self.cell_cost(s)
                        steep += s > W.SLOPE_ROAD_ONLY_DEG
                        count += 1
                i = ny * self.n + nx
                self.cost[i] = total / count
                self.open[i] = steep / count <= W.PATH_BLOCKED_FRACTION
        self._cache = OrderedDict()

    @staticmethod
    def cell_cost(slope):
        """Planning cost of crossing one cell: slope slows rovers, cliffs are avoided."""
        cost = 1.0 + slope / U.SLOPE_DIVISOR_DEG
        if slope > W.SLOPE_ROAD_ONLY_DEG:
            cost += W.PATH_STEEP_CELL_PENALTY
        return cost

    def segment_cost(self, a, b):
        """Cost of driving straight from a to b, sampled along the line."""
        (ax, ay), (bx, by) = a, b
        length = math.hypot(bx - ax, by - ay)
        steps = max(1, int(length / W.PATH_COST_SAMPLE_CELLS))
        n = self.size
        total = 0.0
        for i in range(steps):
            t = (i + 0.5) / steps
            x = min(max(int(ax + (bx - ax) * t + 0.5), 0), n - 1)
            y = min(max(int(ay + (by - ay) * t + 0.5), 0), n - 1)
            total += self.cell_cost(self.slopes[y * n + x])
        return total * length / steps

    # Geometry ---------------------------------------------------------------

    def node_at(self, x, y):
        nx = min(max(int(x / self.node_cells), 0), self.n - 1)
        ny = min(max(int(y / self.node_cells), 0), self.n - 1)
        return ny * self.n + nx

    def node_centre(self, node):
        ny, nx = divmod(node, self.n)
        half = self.node_cells / 2
        return (min(nx * self.node_cells + half, self.size - 1),
                min(ny * self.node_cells + half, self.size - 1))

    def neighbours(self, node):
        ny, nx = divmod(node, self.n)
        n, open_ = self.n, self.open
        for dx, dy, step in _DIRS:
            x, y = nx + dx, ny + dy
            if not (0 <= x < n and 0 <= y < n) or not open_[y * n + x]:
                continue
            if dx and dy and not (open_[ny * n + x] and open_[y * n + nx]):
                continue  # no cutting corners past blocked nodes
            yield y * n + x, step

    # Searches -----------------------------------------------------------------

    def field(self, source):
        """Full Dijkstra field from a node, cached (terrain is static for now).

        source may also be a tuple of nodes: a multi-source field giving the
        cost to the nearest of them (its .source is the first)."""
        cached = self._cache.get(source)
        if cached is not None:
            self._cache.move_to_end(source)
            return cached
        sources = source if isinstance(source, tuple) else (source,)
        dist = [math.inf] * (self.n * self.n)
        prev = [-1] * (self.n * self.n)
        result = Field(sources[0] if sources else -1, dist, prev)
        heap = []
        for s in sources:
            if self.open[s]:
                dist[s] = 0.0
                heap.append((0.0, s))
        if heap:
            heapq.heapify(heap)
            cost, scale = self.cost, self.node_cells * 0.5
            while heap:
                d, node = heapq.heappop(heap)
                if d > dist[node]:
                    continue
                c = cost[node]
                for nb, step in self.neighbours(node):
                    nd = d + (c + cost[nb]) * scale * step
                    if nd < dist[nb]:
                        dist[nb] = nd
                        prev[nb] = node
                        heapq.heappush(heap, (nd, nb))
        self._cache[source] = result
        if len(self._cache) > W.PATH_CACHE_SIZE:
            self._cache.popitem(last=False)
        return result

    def nearest_reachable(self, node, field):
        """node itself if the field reaches it, else the cheapest reachable neighbour.
        Units can graze a blocked node's corner on a shortcut; this steps them back."""
        if field.reachable(node):
            return node
        best = min(self.neighbours(node), key=lambda nb: field.dist[nb[0]], default=None)
        if best is not None and field.reachable(best[0]):
            return best[0]
        return field.source

    def invalidate(self):
        self._cache.clear()

    # Waypoints ------------------------------------------------------------------

    def line_open(self, a, b):
        """True if the straight segment a-b only crosses open nodes."""
        (ax, ay), (bx, by) = a, b
        length = math.hypot(bx - ax, by - ay)
        steps = max(1, int(length / (self.node_cells * W.PATH_LOS_STEP_NODES)))
        for i in range(steps + 1):
            t = i / steps
            if not self.open[self.node_at(ax + (bx - ax) * t, ay + (by - ay) * t)]:
                return False
        return True

    def waypoints(self, start, nodes, goal):
        """Turn a node chain into world waypoints from start to goal, shortcutting
        corners where the straight line stays on open ground and costs no more."""
        points = [start] + [self.node_centre(n) for n in nodes[1:-1]] + [goal]
        last = len(points) - 1
        # Cumulative cost along the node route, to judge shortcuts against.
        along = [0.0]
        for p, q in zip(points, points[1:]):
            along.append(along[-1] + self.segment_cost(p, q))
        out = []
        i = 0
        while i < last:
            j = i + 1
            while j < last:
                k = j + 1
                if not self.line_open(points[i], points[k]):
                    break
                if self.segment_cost(points[i], points[k]) > (along[k] - along[i]) * (1 + W.PATH_SHORTCUT_TOLERANCE):
                    break  # the straight line would climb something the route goes round
                j = k
            out.append(points[j])
            i = j
        return out  # the unit is already at start
