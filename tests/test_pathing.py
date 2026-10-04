import math
import unittest
from array import array

from game.sim.pathing import PathGrid

SIZE = 32      # cells
NODE = 4       # cells per node -> 8 x 8 nodes
STEEP = 40.0   # degrees, blocks a node
WALL_X = 4     # node column holding the wall
GAP_Y = 6      # node row left open in the wall


def wall_slopes():
    """Flat ground with a steep wall down node column WALL_X, open only at node row GAP_Y."""
    s = array("f", [0.0] * (SIZE * SIZE))
    for y in range(SIZE):
        if y // NODE == GAP_Y:
            continue
        for x in range(WALL_X * NODE, (WALL_X + 1) * NODE):
            s[y * SIZE + x] = STEEP
    return s


class PathGridTests(unittest.TestCase):
    def setUp(self):
        self.grid = PathGrid(SIZE, wall_slopes(), NODE)

    def node(self, nx, ny):
        return ny * self.grid.n + nx

    def test_wall_nodes_blocked_and_gap_open(self):
        g = self.grid
        self.assertFalse(g.open[self.node(WALL_X, 0)])
        self.assertTrue(g.open[self.node(WALL_X, GAP_Y)])
        self.assertTrue(g.open[self.node(0, 0)])

    def test_field_routes_through_the_gap(self):
        g = self.grid
        f = g.field(self.node(0, 0))
        goal = self.node(g.n - 1, 0)
        self.assertTrue(f.reachable(goal))
        chain = f.nodes_from_source(goal)
        self.assertEqual(chain[0], self.node(0, 0))
        self.assertEqual(chain[-1], goal)
        self.assertIn(self.node(WALL_X, GAP_Y), chain)
        for node in chain:
            self.assertTrue(g.open[node])
        # Straight across would be 7 flat nodes; the detour must cost more.
        self.assertGreater(f.dist[goal], 7 * NODE)

    def test_blocked_node_unreachable(self):
        f = self.grid.field(self.node(0, 0))
        self.assertFalse(f.reachable(self.node(WALL_X, 0)))

    def test_no_diagonal_corner_cutting(self):
        g = self.grid
        for node in range(g.n * g.n):
            if not g.open[node]:
                continue
            ny, nx = divmod(node, g.n)
            for nb, _ in g.neighbours(node):
                by, bx = divmod(nb, g.n)
                if bx != nx and by != ny:
                    self.assertTrue(g.open[ny * g.n + bx] and g.open[by * g.n + nx])

    def test_waypoints_stay_on_open_ground(self):
        g = self.grid
        start, goal = (2.0, 2.0), (SIZE - 2.0, 2.0)
        f = g.field(g.node_at(*start))
        chain = f.nodes_from_source(g.node_at(*goal))
        points = g.waypoints(start, chain, goal)
        self.assertEqual(points[-1], goal)
        self.assertLess(len(points), len(chain))  # shortcuts removed some corners
        for a, b in zip([start] + points, points):
            self.assertTrue(g.line_open(a, b), (a, b))

    def test_slope_raises_cost(self):
        s = array("f", [0.0] * (SIZE * SIZE))
        for i in range(SIZE * SIZE // 2):
            s[i] = 10.0  # top half sloped 10 degrees
        g = PathGrid(SIZE, s, NODE)
        self.assertAlmostEqual(g.cost[0], 1.0 + 10.0 / 5.0)
        self.assertAlmostEqual(g.cost[g.n * g.n - 1], 1.0)

    def test_field_is_cached(self):
        g = self.grid
        self.assertIs(g.field(0), g.field(0))


if __name__ == "__main__":
    unittest.main()
