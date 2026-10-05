"""Regression tests for playtest feedback after Milestone 3."""

import math
import unittest

from game.content import world as W
from game.sim import units as US
from tests.test_build_power import find_spot, run_until
from tests.test_world import make_world


def build(w, kind, near, rmin=3, rmax=12):
    site, reason = w.place(kind, *find_spot(w, kind, near, rmin, rmax))
    assert site is not None, reason
    assert run_until(w, lambda: site.built, 400), f"{kind} not built"
    return site


class DepotUnloadTests(unittest.TestCase):
    def test_scavenger_keeps_working_after_unloading_at_a_depot(self):
        w = make_world(1)
        w.research.done.add("logistics_1")
        depot = build(w, "depot", (w.lander.x, w.lander.y), 6, 14)
        scav = next(u for u in w.units.values() if u.kind == "scavenger")
        # Half-charged (below the top-up line, above the reserve), carrying scrap, docked at the depot.
        US.release_dock(w, scav)
        scav.x, scav.y = depot.docks[0]
        depot.dock_users[0] = scav.id
        scav.dock, scav.slot, scav.docked = depot.id, 0, True
        scav.cargo = {"scrap": 2}
        scav.battery = 0.45 * US.capacity(w, scav)
        scav.state, scav.activity = US.IDLE, "idle"
        scav.timer = 1
        idle_ticks = 0
        for _ in range(int(60 * W.TICK_RATE)):
            w.tick()
            if scav.activity == "idle" and not scav.cargo:
                idle_ticks += 1
        self.assertEqual(depot.storage.get("scrap", 0) >= 2, True)
        self.assertLess(idle_ticks, 5 * W.TICK_RATE, "scavenger parked at the depot instead of charging or working")


if __name__ == "__main__":
    unittest.main()


class PathAvoidanceTests(unittest.TestCase):
    def test_paths_bend_around_structures_they_are_not_visiting(self):
        w = make_world(2)
        w.place("solar", *find_spot(w, "solar", (w.lander.x, w.lander.y), 8, 14))
        solar = next(s for s in w.structures.values() if s.kind == "solar")
        scav = next(u for u in w.units.values() if u.kind == "scavenger")
        # Plan straight through the solar array's footprint.
        dx, dy = solar.x - scav.x, solar.y - scav.y
        goal = (solar.x + dx * 0.8, solar.y + dy * 0.8)
        path = US.path_to(w, scav, goal)
        self.assertIsNotNone(path)
        r = solar.spec["footprint_cells"]
        prev = (scav.x, scav.y)
        from game.sim.units import _seg_point_dist
        for p in path:
            d, _ = _seg_point_dist(prev[0], prev[1], p[0], p[1], solar.x, solar.y)
            self.assertGreaterEqual(d, r, f"segment {prev}->{p} cuts through the solar array")
            prev = p

    def test_visiting_a_structure_is_not_blocked(self):
        w = make_world(2)
        scav = next(u for u in w.units.values() if u.kind == "scavenger")
        goal = w.lander.docks[3]
        path = US.path_to(w, scav, goal)
        self.assertEqual(path[-1], goal)


class DrivingFeelTests(unittest.TestCase):
    def test_drawn_position_stays_near_the_planned_path_and_settles(self):
        w = make_world(1)
        scav = next(u for u in w.units.values() if u.kind == "scavenger")
        worst = 0.0
        for _ in range(int(90 * W.TICK_RATE)):
            w.tick()
            worst = max(worst, math.hypot(scav.vx - scav.x, scav.vy - scav.y))
        self.assertLess(worst, 1.2)
        # Parked: the drawn position settles onto the real one.
        scav.state, scav.timer = US.IDLE, 10 ** 6
        for _ in range(30):
            w.tick()
        self.assertLess(math.hypot(scav.vx - scav.x, scav.vy - scav.y), 0.01)


class DeconstructionTests(unittest.TestCase):
    def test_constructor_dismantles_and_refunds(self):
        from game.content.structures import DECONSTRUCT_REFUND, STRUCTURES
        w = make_world(1)
        pad = build(w, "charging_pad", (w.lander.x, w.lander.y), 4, 9)
        parts = w.stock("parts")
        self.assertFalse(w.toggle_deconstruct(w.lander.id)[0])
        self.assertTrue(w.toggle_deconstruct(pad.id)[0])
        self.assertTrue(run_until(w, lambda: pad.id not in w.structures, 120))
        refund = int(STRUCTURES["charging_pad"]["build_cost"]["parts"] * DECONSTRUCT_REFUND)
        self.assertEqual(w.stock("parts"), parts + refund)
        self.assertEqual(w.scrap_accounted(), w.scrap_spawned)
        for _ in range(int(30 * W.TICK_RATE)):
            w.tick()
        for u in w.units.values():
            self.assertNotEqual(u.dock, pad.id)

    def test_unmarking_keeps_the_structure(self):
        w = make_world(1)
        pad = build(w, "charging_pad", (w.lander.x, w.lander.y), 4, 9)
        w.toggle_deconstruct(pad.id)
        w.toggle_deconstruct(pad.id)
        for _ in range(int(60 * W.TICK_RATE)):
            w.tick()
        self.assertIn(pad.id, w.structures)
