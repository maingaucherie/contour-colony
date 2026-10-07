"""Milestone 5 depth: clock speed, wear and repairs, maintenance drones."""

import math
import unittest

from game.content import structures as S
from game.content import world as W
from game.content.structures import STRUCTURES
from game.sim import production as P
from game.sim import structures as ST
from game.sim import units as UN
from game.sim import wear
from tests.test_build_power import find_spot
from tests.test_chain import built_structure, ledger_ok
from tests.test_world import make_world, minutes


def run_cycles(w, s, n):
    s.powered = True
    for _ in range(n):
        s.inputs = {k: 10 for k in s.spec["recipe"]["in"]}
        s.outputs = {}
        while True:
            P.update(w, s)
            if s.cycle_left_s <= 0.0:
                break


class ClockTests(unittest.TestCase):
    def test_underclock_any_time_overclock_after_research(self):
        w = make_world(1)
        c = built_structure(w, "crusher")
        draw = STRUCTURES["crusher"]["draw_kw"]
        self.assertEqual(ST.next_clock(w, c), 0.5)        # 150% is skipped until researched
        w.set_clock(c.id, 0.5)
        self.assertAlmostEqual(c.draw_kw(), draw * 0.45)
        self.assertAlmostEqual(P.speed(w, c), 0.5)
        w.research.done.add("overclocking")
        w.set_clock(c.id, 1.0)
        self.assertEqual(ST.next_clock(w, c), 1.5)
        w.set_clock(c.id, 1.5)
        self.assertAlmostEqual(c.draw_kw(), draw * 2.0)
        self.assertAlmostEqual(P.speed(w, c), 1.5)

    def test_switched_off_takes_nothing_and_draws_nothing(self):
        from game.sim import jobs
        w = make_world(1)
        c = built_structure(w, "crusher")
        w.set_clock(c.id, 0.5)
        self.assertEqual(ST.next_clock(w, c), 0.0)
        w.set_clock(c.id, 0.0)
        self.assertEqual(c.draw_kw(), 0.0)
        self.assertFalse(any(s is c for s, item, space, mult in jobs.requests(w)))
        c.inputs = {"ilmenite": 4}
        P.update(w, c)
        self.assertEqual(c.status, P.OFF)
        self.assertEqual(c.inputs, {"ilmenite": 4})
        self.assertEqual(ST.next_clock(w, c), 1.0)


class WearTests(unittest.TestCase):
    def test_wear_builds_up_and_slows_but_only_breaks_under_pressure(self):
        w = make_world(1)
        c = built_structure(w, "crusher")
        per = STRUCTURES["crusher"]["wear_per_cycle"]
        run_cycles(w, c, 10)
        self.assertAlmostEqual(c.wear, 10 * per)
        c.wear = 0.75
        self.assertAlmostEqual(wear.speed_factor(c), 0.75)
        c.wear = 1.0
        self.assertAlmostEqual(wear.speed_factor(c), S.WEAR["worn_speed"])
        c.cycle_left_s = 0.0
        P.update(w, c)
        self.assertNotEqual(c.status, P.BROKEN)           # calm: slow, never broken
        w.contracts.set_mode("pressure")
        P.update(w, c)
        self.assertEqual(c.status, P.BROKEN)

    def test_overclocking_wears_faster_and_bearings_slower(self):
        w = make_world(1)
        c = built_structure(w, "crusher")
        per = STRUCTURES["crusher"]["wear_per_cycle"]
        c.clock = 1.5
        run_cycles(w, c, 1)
        self.assertAlmostEqual(c.wear, per * 2.0)
        c.wear, c.clock = 0.0, 1.0
        w.research.done.add("hardened_bearings")
        run_cycles(w, c, 1)
        self.assertAlmostEqual(c.wear, per * 0.6)

    def test_constructor_repairs_with_machine_parts(self):
        w = make_world(1)
        c = built_structure(w, "crusher")
        c.wear = 0.72
        parts = w.stock("parts")
        for _ in range(minutes(6)):
            w.tick()
            if c.wear < 0.5:
                break
        self.assertLess(c.wear, 0.5)
        self.assertEqual(w.stock("parts") + sum(u.cargo.get("parts", 0) for u in w.units.values()),
                         parts - wear.parts_needed(ST.Structure(0, "crusher", 0, 0, wear=0.72)))
        self.assertTrue(ledger_ok(w, "parts")[0])
        self.assertIsNone(c.repairer)


class DroneTests(unittest.TestCase):
    def test_drone_flies_straight_and_repairs(self):
        w = make_world(1)
        w.research.done.update({"field_survey", "extraction", "sintering", "logistics_1", "electrolysis",
                                "reduction", "maintenance"})
        L = w.lander
        hx, hy = find_spot(w, "maintenance_hangar", (L.x, L.y), 4.0)
        hangar = ST.Structure(w.new_id(), "maintenance_hangar", hx, hy)
        w.structures[hangar.id] = hangar
        ST.complete(w, hangar)
        hangar.storage["parts"] = 10
        w.produced["parts"] = w.produced.get("parts", 0) + 10
        fx, fy = find_spot(w, "crusher", (L.x, L.y), 25.0, 45.0)
        far = ST.Structure(w.new_id(), "crusher", fx, fy)
        w.structures[far.id] = far
        ST.complete(w, far)
        far.wear = 0.9
        # Keep the constructors busy elsewhere: this job is the drone's.
        for u in list(w.units.values()):
            if u.kind == "constructor":
                del w.units[u.id]
        d = w.spawn_unit("maintenance_drone", hangar.x + 2, hangar.y)
        straight = True
        for _ in range(minutes(5)):
            w.tick()
            if d.state == UN.MOVING and len(d.path) > 1:
                straight = False
            if far.wear < 0.5:
                break
        self.assertTrue(straight, "drones fly straight, never along roads")
        self.assertLess(far.wear, 0.5)
        self.assertTrue(ledger_ok(w, "parts")[0])
        for _ in range(minutes(2)):
            w.tick()
        self.assertTrue(d.dock is not None and w.structures[d.dock].kind in ("maintenance_hangar", "lander"))

    def test_hangar_keeps_only_parts(self):
        w = make_world(1)
        w.research.done.add("maintenance")
        h = built_structure(w, "maintenance_hangar")
        self.assertEqual(w.store(h, "scrap", 5), 0)
        self.assertEqual(w.store(h, "parts", 5), 5)


if __name__ == "__main__":
    unittest.main()
