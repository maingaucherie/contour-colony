"""Graded roads: planning, building, faster and cheaper driving, opening passes."""

import math
import unittest

from game.content import structures as S
from game.content import units as U
from game.sim import roads as R
from game.sim import save
from game.sim import structures as ST
from tests.test_build_power import run_until
from tests.test_world import make_world


def straight_road(w, length=12.0, near=None):
    """Ends of a buildable road of about this length near the lander (or near)."""
    L = w.lander
    cx, cy = near or (L.x, L.y)
    for r in (6.0, 8.0, 10.0, 12.0):
        for deg in range(0, 360, 20):
            a = math.radians(deg)
            p0 = (cx + r * math.cos(a), cy + r * math.sin(a))
            p1 = (p0[0] + length * math.cos(a), p0[1] + length * math.sin(a))
            if R.plan(w, p0, p1)["ok"]:
                return p0, p1
    raise AssertionError("no road spot")


def build_road(w, p0, p1):
    s, reason = w.place_road(p0, p1)
    assert s is not None, reason
    ST.complete(w, s)
    return s


class PlanTests(unittest.TestCase):
    def test_rules_and_credits(self):
        w = make_world(1)
        w.credits = 1000
        L = w.lander
        self.assertTrue(R.plan(w, (L.x + 5, L.y), (L.x + 5 + S.ROAD_MAX_CELLS + 2, L.y))["reason"]
                        .startswith("TOO LONG"))
        self.assertEqual(R.plan(w, (L.x - 6, L.y), (L.x + 6, L.y))["reason"], "BLOCKED BY LANDER")
        p0, p1 = straight_road(w)
        p = R.plan(w, p0, p1)
        self.assertGreaterEqual(p["credits"], S.STRUCTURES["road"]["credits_per_cell"] * 12)
        s, _ = w.place_road(p0, p1)
        self.assertEqual(w.credits, 1000 - p["credits"])
        self.assertTrue(w.cancel(s.id))
        self.assertEqual(w.credits, 1000)

    def test_too_poor(self):
        w = make_world(1)
        p0, p1 = straight_road(w)
        w.credits = 1
        self.assertIn("CR", R.plan(w, p0, p1)["reason"])

    def test_buildings_cannot_sit_on_a_road(self):
        w = make_world(1)
        w.credits = 1000
        p0, p1 = straight_road(w)
        s = build_road(w, p0, p1)
        mid = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
        self.assertEqual(ST.check_placement(w, "pylon", *mid), (False, "OVERLAPS ROAD"))


class DrivingTests(unittest.TestCase):
    def test_road_cells_are_faster_and_cheaper(self):
        w = make_world(1)
        w.credits = 1000
        p0, p1 = straight_road(w, 16.0)
        a, b = w.grid.node_at(*p0), w.grid.node_at(*p1)
        before = w.grid.field(a).dist[b]
        build_road(w, p0, p1)
        mid = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
        n = w.heightmap.size
        slope = w.slopes[int(mid[1] + 0.5) * n + int(mid[0] + 0.5)]
        self.assertAlmostEqual(w.grid.cell_factor(*mid),
                               (1 + slope * U.ROAD_SLOPE_FACTOR / U.SLOPE_DIVISOR_DEG) / U.ROAD_SPEED_MULT)
        after = w.grid.field(a).dist[b]
        self.assertLess(after, before * 0.75)
        # Routes along it pass over the road, not the nodes' centres.
        f = w.grid.field(a)
        points = w.grid.waypoints(p0, f.nodes_from_source(b), p1)
        for x, y in points[:-1]:
            self.assertLessEqual(ST.distance_to_segment(x, y, p0, p1), S.ROAD_WIDTH_CELLS)

    def test_a_road_opens_ground_too_steep_to_drive(self):
        w = make_world(1)
        g = w.grid
        closed = next(i for i in range(len(g.open)) if not g.open[i])
        x, y = g.node_centre(closed)
        self.assertTrue(g.set_roads({(int(x), int(y))}))
        self.assertTrue(g.open[closed])
        self.assertEqual(g.node_point(closed), (int(x), int(y)))
        g.set_roads(set())
        self.assertFalse(g.open[closed])


class LifecycleTests(unittest.TestCase):
    def test_constructor_grades_it(self):
        w = make_world(1)
        w.credits = 1000
        p0, p1 = straight_road(w)
        s, _ = w.place_road(p0, p1)
        self.assertTrue(run_until(w, lambda: s.built, 240))
        self.assertTrue(any(w.grid.road))

    def test_dismantled_roads_go_and_saves_keep_them(self):
        w = make_world(1)
        w.credits = 1000
        p0, p1 = straight_road(w)
        s = build_road(w, p0, p1)
        road = bytes(w.grid.road)
        fresh = make_world(1)
        save.apply(fresh, save.read(save.dumps(w)))
        self.assertEqual(bytes(fresh.grid.road), road)
        self.assertEqual(fresh.structures[s.id].ends, [p0, p1])
        ST.dismantle(w, s)
        self.assertFalse(any(w.grid.road))


if __name__ == "__main__":
    unittest.main()
