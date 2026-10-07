import math
import unittest

from game.content import world as W
from game.content.research import RESEARCH
from game.content.structures import STRUCTURES
from game.sim import power
from game.sim import structures as ST
from game.sim import units as US
from game.sim.structures import Structure
from tests.test_world import make_world, minutes


def find_spot(w, kind, near, rmin=3.0, rmax=20.0):
    r = rmin
    while r <= rmax:
        for a in range(0, 360, 15):
            x = near[0] + r * math.cos(math.radians(a))
            y = near[1] + r * math.sin(math.radians(a))
            if ST.check_placement(w, kind, x, y)[0]:
                return x, y
        r += 0.5
    raise AssertionError(f"no spot for {kind}")


def run_until(w, cond, seconds):
    for _ in range(int(seconds * W.TICK_RATE)):
        w.tick()
        if cond():
            return True
    return False


def built(w, kind):
    return [s for s in w.structures.values() if s.kind == kind and s.built]


class PowerAllocationTests(unittest.TestCase):
    def test_priority_order_and_skipping(self):
        consumers = [("low_a", 4.0, "low"), ("normal_big", 8.0, "normal"),
                     ("high", 5.0, "high"), ("normal_small", 2.0, "normal")]
        powered, served = power.allocate(10.0, consumers)
        # high (5) first; normal_big (8) doesn't fit; normal_small (2) does; low_a (4) doesn't.
        self.assertEqual(powered, {"high", "normal_small"})
        self.assertEqual(served, 7.0)

    def test_enough_supply_powers_everything(self):
        powered, _ = power.allocate(100.0, [("a", 5.0, "low"), ("b", 5.0, "high")])
        self.assertEqual(powered, {"a", "b"})

    def test_grids_by_reach(self):
        lander = Structure(1, "lander", 50.0, 50.0, output_kw=15.0)
        near = Structure(2, "charging_pad", 54.0, 50.0)        # within the lander's 6-cell reach
        far = Structure(3, "charging_pad", 80.0, 50.0)         # nobody's reach
        pylon = Structure(4, "pylon", 55.0, 50.0)              # extends the grid 6 more cells
        via_pylon = Structure(5, "depot", 60.5, 50.0)
        summary = power.compute([lander, near, far, pylon, via_pylon])
        self.assertEqual(len(summary), 1)
        self.assertTrue(near.powered and via_pylon.powered)
        self.assertEqual(via_pylon.grid_parent, pylon.id)
        self.assertFalse(far.powered)
        self.assertEqual(far.grid, -1)

    def test_shortfall_respects_structure_priority(self):
        lander = Structure(1, "lander", 50.0, 50.0, output_kw=15.0)
        pads = [Structure(10 + i, "rover_bay", 52.0 + i, 52.0) for i in range(4)]  # 5 kW each, 20 kW total
        pads[3].priority = "high"
        pads[0].priority = "low"
        power.compute([lander] + pads)
        self.assertEqual([p.powered for p in pads], [False, True, True, True])


class PlacementTests(unittest.TestCase):
    def test_rules(self):
        w = make_world(1)
        L = w.lander
        ok, reason = ST.check_placement(w, "scanner", L.x + 4, L.y)
        self.assertFalse(ok)
        self.assertEqual(reason, "NOT RESEARCHED")
        self.assertEqual(ST.check_placement(w, "solar", L.x, L.y)[1], "OVERLAPS LANDER")
        self.assertEqual(ST.check_placement(w, "solar", 0.2, 0.2)[1], "OUTSIDE THE SITE")
        # Somewhere steep.
        size = w.heightmap.size
        steep = next(i for i in range(size * size) if w.slopes[i] > 20 and 3 < i % size < size - 3 and 3 < i // size < size - 3)
        ok, reason = ST.check_placement(w, "solar", steep % size, steep // size)
        self.assertFalse(ok)

    def test_mine_needs_a_confirmed_field(self):
        w = make_world(1)
        w.research.done.update({"prospecting", "extraction"})
        f = next(f for f in w.fields if f.kind == "ilmenite")
        w.hint_field(f)  # the scanner's job
        saved = bytes(w.survey.levels)
        w.survey_area(f.cx, f.cy, f.radius * 2, 2)
        self.assertTrue(f.hinted and f.confirmed)
        spot = next((p for p in f.sample_points(0.5) if ST.check_placement(w, "ilmenite_mine", *p)[0]), None)
        self.assertIsNotNone(spot)
        # The same spot before the survey reached level 2 is refused.
        w.survey.levels[:] = saved
        self.assertIn("CONFIRMED", ST.check_placement(w, "ilmenite_mine", *spot)[1])
        # Not outside the field, even on surveyed ground.
        self.assertIn("FIELD", ST.check_placement(w, "ilmenite_mine", w.lander.x + 3, w.lander.y + 3)[1])


class ConstructionTests(unittest.TestCase):
    def test_constructor_builds_a_solar_array_and_materials_are_consumed(self):
        w = make_world(1)
        start = {k: w.stock(k) for k in ("scrap", "parts")}
        spot = find_spot(w, "solar", (w.lander.x, w.lander.y))
        site, _ = w.place("solar", *spot)
        cost = STRUCTURES["solar"]["build_cost"]
        self.assertTrue(run_until(w, lambda: site.built, 240))
        self.assertEqual(w.consumed.get("parts", 0), cost["parts"])
        self.assertEqual(w.stock("parts"), start["parts"] - cost["parts"])
        self.assertEqual(w.scrap_accounted(), w.scrap_spawned)
        self.assertGreater(site.output_kw, 0.0)
        w.tick()
        self.assertGreater(w.power_grids[w.lander.grid]["supply"], STRUCTURES["lander"]["power_kw"])

    def test_cancel_refunds_delivered_materials(self):
        w = make_world(1)
        spot = find_spot(w, "solar", (w.lander.x, w.lander.y))
        site, _ = w.place("solar", *spot)
        run_until(w, lambda: sum(site.delivered.values()) > 0, 120)
        self.assertTrue(w.cancel(site.id))
        for _ in range(minutes(2)):
            w.tick()
        self.assertNotIn(site.id, w.structures)
        self.assertEqual(w.stock("parts"), W.START_STORAGE["parts"])
        self.assertEqual(w.scrap_accounted(), w.scrap_spawned)

    def test_charging_pad_extends_charging(self):
        w = make_world(2)
        spot = find_spot(w, "charging_pad", (w.lander.x, w.lander.y), 3, 6)
        site, _ = w.place("charging_pad", *spot)
        self.assertTrue(run_until(w, lambda: site.built, 240))
        w.tick()
        self.assertTrue(site.powered)
        self.assertIn(site, w.chargers())
        self.assertEqual(len(site.docks), 2)


class ResearchTests(unittest.TestCase):
    def test_prerequisites_cost_and_one_at_a_time(self):
        w = make_world(1)
        self.assertEqual(w.start_research("better_batteries")[1], "PREREQUISITES MISSING")
        self.assertEqual(w.start_research("prospecting")[1], "NEEDS MASS DRIVER PHASE 1")
        credits = w.credits
        self.assertTrue(w.start_research("logistics_1")[0])
        self.assertEqual(w.credits, credits - RESEARCH["logistics_1"]["cost"])
        w.credits += 1000
        self.assertEqual(w.start_research("sorting")[1], "ANOTHER PROJECT IS RUNNING")
        ticks = round(RESEARCH["logistics_1"]["time_s"] * W.TICK_RATE)
        for _ in range(ticks - 1):
            w.tick()
        self.assertNotIn("logistics_1", w.research.done)
        w.tick()
        self.assertIn("logistics_1", w.research.done)
        self.assertTrue(w.unlocked("hauler"))
        w.research.phase = 1
        self.assertTrue(w.start_research("prospecting")[0])

    def test_better_batteries_raise_capacity(self):
        w = make_world(1)
        base = w.battery_capacity("scavenger")
        w.research.done.add("better_batteries")
        self.assertAlmostEqual(w.battery_capacity("scavenger"), base * 1.5)


class SurveyAndOrdersTests(unittest.TestCase):
    def test_survey_order_reaches_level_two(self):
        w = make_world(3)
        rover = w.spawn_unit("survey_rover", w.lander.x + 2, w.lander.y + 2)
        target = None
        for d in range(8, 30):
            x, y = w.lander.x + d, w.lander.y
            if w.home_field.reachable(w.grid.node_at(x, y)) and w.survey.level_at(x, y) < 2:
                target = (x, y)
                break
        ok, reason = w.command_unit(rover.id, "survey", *target)
        self.assertTrue(ok, reason)
        self.assertTrue(run_until(w, lambda: w.survey.level_at(*target) == 2, 120))
        self.assertIsNone(rover.order)

    def test_out_of_range_order_is_refused(self):
        w = make_world(3)
        rover = w.spawn_unit("survey_rover", w.lander.x, w.lander.y)
        rover.battery = 25.0
        far = max(range(w.grid.n * w.grid.n), key=lambda n: w.home_field.dist[n] if w.home_field.reachable(n) else -1)
        ok, reason = w.command_unit(rover.id, "survey", *w.grid.node_centre(far))
        self.assertFalse(ok)
        self.assertIn("RANGE", reason)

    def test_rover_bay_builds_units_from_storage(self):
        w = make_world(1)
        w.research.done.add("prospecting")
        spot = find_spot(w, "rover_bay", (w.lander.x, w.lander.y), 3, 5)
        site, _ = w.place("rover_bay", *spot)
        self.assertTrue(run_until(w, lambda: site.built, 300))
        before = len(w.units)
        w.lander.storage["scrap"] = w.lander.storage.get("scrap", 0) + 20  # don't depend on scavenging speed
        parts = w.stock("parts")
        self.assertTrue(w.order_unit(site.id, "survey_rover")[0])
        self.assertTrue(run_until(w, lambda: len(w.units) > before, 60))
        self.assertEqual(w.stock("parts"), parts - 4)


class ExitCriterionTest(unittest.TestCase):
    """Milestone 3 exit: you can survey a field and place a mine on it."""

    def test_survey_a_field_then_build_a_mine_on_it(self):
        w = make_world(1)
        L = w.lander
        w.research.phase = 1   # as if the mass driver's foundation were done
        self.assertTrue(w.start_research("prospecting")[0])
        self.assertTrue(run_until(w, lambda: "prospecting" in w.research.done, 60))
        bay, _ = w.place("rover_bay", *find_spot(w, "rover_bay", (L.x, L.y), 3, 5))
        self.assertTrue(run_until(w, lambda: bay.built, 300))
        w.order_unit(bay.id, "survey_rover")
        scanner, _ = w.place("scanner", *find_spot(w, "scanner", (L.x, L.y), 3, 8))
        # The scanner flags fields; the survey rover confirms an ilmenite one on its own.
        self.assertTrue(run_until(w, lambda: any(f.kind == "ilmenite" and f.confirmed for f in w.fields), 600))
        w.credits += 100  # skip waiting for scrap sales
        self.assertTrue(w.start_research("extraction")[0])
        self.assertTrue(run_until(w, lambda: "extraction" in w.research.done, 60))
        field = next(f for f in w.fields if f.kind == "ilmenite" and f.confirmed)
        spot = next(p for p in field.sample_points(0.5) if ST.check_placement(w, "ilmenite_mine", *p)[0])
        mine, reason = w.place("ilmenite_mine", *spot)
        self.assertIsNotNone(mine, reason)
        self.assertTrue(run_until(w, lambda: mine.built, 600))
        self.assertEqual(w.scrap_accounted(), w.scrap_spawned)
        for u in w.units.values():
            self.assertNotEqual(u.state, US.STRANDED)


if __name__ == "__main__":
    unittest.main()
