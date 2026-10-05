"""Long routes: units working far from home along a chain of chargers must
never run flat, however crowded the chargers get."""

import math
import unittest

from game.sim import structures as ST
from game.sim import units as UN
from tests.test_world import make_world, minutes

ALL_RESEARCH = {"field_survey", "extraction", "sintering", "logistics_1", "electrolysis", "reduction"}


def _spot(w, kind, near, r0=0.0, r1=8.0):
    r = r0
    while r <= r1:
        for a in range(0, 360, 15):
            x, y = near[0] + r * math.cos(math.radians(a)), near[1] + r * math.sin(math.radians(a))
            if ST.check_placement(w, kind, x, y)[0]:
                return x, y
        r += 0.5
    return None


def _finish(w, kind, x, y):
    s = ST.Structure(w.new_id(), kind, x, y)
    w.structures[s.id] = s
    ST.complete(w, s)
    return s


def long_route_site(seed, charger, step, haulers):
    """The farthest ice field, mined, with a chain of chargers every `step`
    cost-cells along the road home and a melter at the lander."""
    w = make_world(seed)
    w.research.done.update(ALL_RESEARCH)
    w.credits = 10 ** 6
    home = w.home_field
    ice = [f for f in w.fields if f.kind == "ice" and home.reachable(w.grid.node_at(f.cx, f.cy))]
    f = max(ice, key=lambda f: home.dist[w.grid.node_at(f.cx, f.cy)])
    last = 0.0
    chargers = 0
    for n in home.nodes_from_source(w.grid.node_at(f.cx, f.cy)):
        if home.dist[n] - last >= step:
            at = _spot(w, charger, w.grid.node_centre(n))
            if at:
                _finish(w, charger, *at)
                chargers += 1
                last = home.dist[n]
                if charger == "charging_pad":       # a solar array beside it for power
                    sp = _spot(w, "solar", at, 2.5, 4.0)
                    if sp:
                        _finish(w, "solar", *sp)
    mine = _finish(w, "ice_mine", f.cx, f.cy)      # field centres are always buildable
    at = _spot(w, "outpost", (mine.x, mine.y), 3.0, 6.0)
    if at:
        _finish(w, "outpost", *at)
    _finish(w, "ice_melter", *_spot(w, "ice_melter", (w.lander.x, w.lander.y), 3.0, 6.0))
    w.structures_changed()
    for i in range(haulers):
        w.spawn_unit("hauler", w.lander.x + 2 + i * 0.3, w.lander.y + 2)
    return w, chargers


class LongRouteTests(unittest.TestCase):
    def check(self, seed, charger, step, haulers, mins):
        w, chargers = long_route_site(seed, charger, step, haulers)
        self.assertGreater(chargers, 1)
        for _ in range(minutes(mins)):
            w.tick()
            for u in w.units.values():
                self.assertNotEqual(u.state, UN.STRANDED,
                                    f"{u.kind} {u.id} ran flat at {w.time_s() / 60:.1f} min, "
                                    f"{w.charge_field.dist[w.grid.node_at(u.x, u.y)]:.0f} cost-cells from a charger")
        made = sum(s.cycles for s in w.structures.values() if s.kind == "ice_melter")
        self.assertGreater(made, 0, "ice should reach the melter along the route")

    def test_crowded_pads_far_apart(self):
        # Pads near the limit of one battery apart, more haulers than docks.
        self.check(1, "charging_pad", 65, 14, 30)

    def test_outposts_far_apart(self):
        self.check(6, "outpost", 75, 14, 25)


class DockTests(unittest.TestCase):
    def test_every_dock_is_on_drivable_ground(self):
        for seed in (1, 4, 6):
            w, _ = long_route_site(seed, "charging_pad", 45, 0)
            for s in w.structures.values():
                for x, y in s.docks:
                    node = w.grid.node_at(x, y)
                    self.assertTrue(w.grid.open[node] and w.home_field.reachable(node),
                                    f"seed {seed}: a {s.kind} dock at ({x:.1f}, {y:.1f}) is on a cliff")


if __name__ == "__main__":
    unittest.main()
