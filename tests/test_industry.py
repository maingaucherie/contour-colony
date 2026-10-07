"""Building rules, snapping, direct feed, grading and outposts."""

import math
import unittest

from game.content import structures as S
from game.content import world as W
from game.content.structures import STRUCTURES
from game.sim import production as P
from game.sim import structures as ST
from tests.test_build_power import find_spot
from tests.test_chain import built_structure, ledger_ok
from tests.test_world import make_world, minutes

ALL_RESEARCH = {"prospecting", "extraction", "sorting", "logistics_1", "electrolysis", "reduction"}


def finish(w, kind, x, y):
    s = ST.Structure(w.new_id(), kind, x, y)
    w.structures[s.id] = s
    ST.complete(w, s)
    return s


class BuildingRuleTests(unittest.TestCase):
    def test_mines_slow_as_reserves_run_out(self):
        w = make_world(1)
        f = w.fields[0]
        w.research.done.update(ALL_RESEARCH)
        mine = finish(w, "ilmenite_mine", f.cx, f.cy)
        self.assertEqual(mine.field_id, f.id)
        fresh = P.speed(w, mine)
        self.assertAlmostEqual(fresh, f.richness, places=6)
        f.mined = math.ceil(f.reserve())
        self.assertAlmostEqual(P.speed(w, mine), f.richness * W.FIELD_DEPLETED_FLOOR, places=6)
        f.mined = 0
        mine.powered = True
        for _ in range(int(P.cycle_time(w, mine) * W.TICK_RATE) + 2):
            P.update(w, mine)
        self.assertEqual(f.mined, 1)

    def test_kiln_runs_faster_in_the_sun(self):
        w = make_world(1)
        kiln = built_structure(w, "sinter_kiln")
        lo, hi = STRUCTURES["sinter_kiln"]["sun_speed"]
        k = P.speed(w, kiln)
        self.assertTrue(lo <= k <= hi)
        dark, bright = W.ILLUMINATION_RANGE
        expected = lo + (hi - lo) * (w.illumination_at(kiln.x, kiln.y) - dark) / (bright - dark)
        self.assertAlmostEqual(k, expected, places=6)

    def test_furnace_warms_while_working_and_cools_when_idle(self):
        w = make_world(1)
        f = built_structure(w, "reduction_furnace")
        heat = STRUCTURES["reduction_furnace"]["heat"]
        self.assertAlmostEqual(P.speed(w, f), heat["cold_speed"])
        f.powered = True
        f.inputs = {"concentrate": 10, "hydrogen": 10}
        for _ in range(int(heat["warm_up_s"] / 2 * W.TICK_RATE)):
            f.inputs = {"concentrate": 10, "hydrogen": 10}
            f.outputs = {}
            P.update(w, f)
        self.assertAlmostEqual(f.heat, 0.5, delta=0.05)
        f.inputs = {}
        f.cycle_left_s = 0.0
        for _ in range(int(heat["cool_s"] * W.TICK_RATE)):
            P.update(w, f)
        self.assertEqual(f.heat, 0.0)

    def test_melter_beside_a_working_kiln_runs_double(self):
        w = make_world(1)
        kiln = built_structure(w, "sinter_kiln")
        spec = STRUCTURES["ice_melter"]
        gap = STRUCTURES["sinter_kiln"]["footprint_cells"] + spec["footprint_cells"] + S.PLACEMENT_GAP_CELLS + 0.1
        x, y = find_spot(w, "ice_melter", (kiln.x, kiln.y), gap, gap + 0.6)
        melter = finish(w, "ice_melter", x, y)
        kiln.status = P.WORKING
        w.tick_count = 0
        P.update(w, melter)
        self.assertTrue(melter.warm)
        self.assertAlmostEqual(P.speed(w, melter), spec["waste_heat"]["speed"])


class SnapAndFeedTests(unittest.TestCase):
    def test_solar_arrays_snap_into_a_farm(self):
        w = make_world(1)
        a = built_structure(w, "solar")
        cw, ch = STRUCTURES["solar"]["snap"]["cell"]
        x, y = ST.snap_position(w, "solar", a.x + cw + 0.4, a.y + 0.2)
        self.assertTrue(ST.check_placement(w, "solar", x, y)[0])
        self.assertAlmostEqual(math.hypot(x - a.x, y - a.y), cw, places=6)   # clicked onto its right edge
        b = finish(w, "solar", x, y)
        w.structures_changed()
        bonus = 1 + STRUCTURES["solar"]["snap"]["farm_bonus"]
        self.assertAlmostEqual(a.output_kw, STRUCTURES["solar"]["power_kw"] * w.illumination_at(a.x, a.y) * bonus)
        self.assertEqual(ST.farm_neighbours(w, b), 1)

    def test_touching_buildings_feed_directly(self):
        w = make_world(1)
        kiln = built_structure(w, "sinter_kiln")
        # A melter can't feed a kiln; a crusher next to a furnace can.
        crusher = built_structure(w, "crusher")
        r = STRUCTURES["crusher"]["footprint_cells"] + STRUCTURES["reduction_furnace"]["footprint_cells"]
        x, y = find_spot(w, "reduction_furnace", (crusher.x, crusher.y), r + S.PLACEMENT_GAP_CELLS + 0.05,
                         r + S.FEED_REACH_CELLS - 0.05)
        furnace = finish(w, "reduction_furnace", x, y)
        w.structures_changed()
        self.assertIn((crusher, furnace, "concentrate"), w.feed_links())
        self.assertFalse(any(kiln in (a, b) for a, b, _ in w.feed_links()))
        crusher.outputs["concentrate"] = 3
        w.produced["concentrate"] = 3
        for _ in range(int(3 * W.TICK_RATE / S.FEED_ITEMS_PER_S) + 1):
            w.tick()
        self.assertEqual(furnace.inputs.get("concentrate", 0), 3)   # no hydrogen yet, so it waits
        self.assertEqual(furnace.fed, 3)
        self.assertTrue(ledger_ok(w, "concentrate")[0])


class GradingTests(unittest.TestCase):
    def test_borderline_ground_can_be_graded(self):
        w = make_world(1)
        L = w.lander
        spec = STRUCTURES["depot"]
        w.research.done.update(ALL_RESEARCH)
        spot = None
        for r in range(4, 40):
            for a in range(0, 360, 10):
                x, y = L.x + r * math.cos(math.radians(a)), L.y + r * math.sin(math.radians(a))
                g = ST.grading_needed(w, "depot", x, y)
                if 1.0 < g and ST.steepest_under(w, x, y, spec["footprint_cells"]) < S.GRADE_MAX_DEG \
                        and ST.check_placement(w, "depot", x, y)[0]:
                    spot = (x, y, g)
                    break
            if spot:
                break
        self.assertIsNotNone(spot)
        x, y, g = spot
        credits = w.credits
        site, _ = w.place("depot", x, y)
        cost = ST.grade_credits(spec, g)
        self.assertEqual(w.credits, credits - cost)
        self.assertGreater(site.build_time(), spec["build_time_s"])
        w.cancel(site.id)
        self.assertEqual(w.credits, credits)
        w.credits = 0
        self.assertEqual(ST.check_placement(w, "depot", x, y), (False, f"GRADING NEEDS {cost} CR"))


class OutpostTests(unittest.TestCase):
    def test_outpost_powers_itself_charges_and_stores(self):
        w = make_world(1)
        w.research.done.update(ALL_RESEARCH)
        L = w.lander
        x, y = find_spot(w, "outpost", (L.x, L.y), 20.0, 40.0)
        o = finish(w, "outpost", x, y)
        w.tick()
        self.assertTrue(o.powered)
        self.assertIn(o, w.chargers())
        self.assertIn(o, w.storages())
        self.assertEqual(w.capacity(), STRUCTURES["lander"]["storage"] + STRUCTURES["outpost"]["storage"])


if __name__ == "__main__":
    unittest.main()
