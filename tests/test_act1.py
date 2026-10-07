"""Act I: scrapers, the sorter, the scrap furnace, construction priority and the mass driver."""

import unittest

from game.content import units as U
from game.content import world as W
from game.content.structures import STRUCTURES
from game.sim import geology as G
from game.sim import jobs
from game.sim import massdriver as MD
from game.sim import production as P
from game.sim import save
from game.sim import structures as ST
from game.sim.terrain import run_to_completion
from game.sim.world import build_world
from tests.test_build_power import find_spot, run_until
from tests.test_chain import built_structure, ledger_ok
from tests.test_world import make_world, minutes


def scraper(w):
    return next(u for u in w.units.values() if u.kind == "scraper")


class ScraperTests(unittest.TestCase):
    def test_a_scraper_sweeps_its_zone_for_regolith(self):
        w = make_world(2)
        u = scraper(w)
        seen = set()
        for _ in range(minutes(6)):
            w.tick()
            seen.add(u.activity)
        self.assertIn("scraping", seen)
        self.assertGreater(w.stock("regolith"), 20)
        self.assertTrue(ledger_ok(w, "regolith")[0])
        self.assertLess(abs(u.zone[0] - w.lander.x) + abs(u.zone[1] - w.lander.y), 10)

    def test_passes_alternate_direction_and_step_sideways(self):
        from game.sim import scraper as SC
        w = make_world(2)
        u = scraper(w)
        u.zone = (w.lander.x + 20, w.lander.y + 20)
        a = SC.lane_segment(w, u, 0, False)
        b = SC.lane_segment(w, u, 1, True)
        if a and b:
            self.assertAlmostEqual(b[0][1] - a[0][1], u.spec["lane_spacing_cells"])
            self.assertGreater(a[1][0], a[0][0])   # east, then
            self.assertLess(b[1][0], b[0][0])      # back west

    def test_lumpy_ground_gets_levelled_and_saved(self):
        w = make_world(2)
        size = w.heightmap.size
        lumpy = next(i for i in range(size * size)
                     if U.SCRAPE_FLATTEN_FROM_DEG + 1 < w.slopes[i] < U.SCRAPE_FLATTEN_MAX_DEG)
        cliff = next(i for i in range(size * size) if w.slopes[i] > U.SCRAPE_FLATTEN_MAX_DEG + 3)
        for _ in range(U.SCRAPE_PASSES):
            w.scrape(lumpy)
            w.scrape(cliff)
        self.assertEqual(w.slopes[lumpy], U.SCRAPE_FLATTEN_TO_DEG)
        self.assertGreater(w.slopes[cliff], U.SCRAPE_FLATTEN_MAX_DEG)   # cliffs stay cliffs
        w.relevel()
        fresh = run_to_completion(build_world(2, w.heightmap))
        save.apply(fresh, save.read(save.dumps(w)))
        self.assertEqual(fresh.slopes[lumpy], U.SCRAPE_FLATTEN_TO_DEG)
        self.assertIn(lumpy, fresh.flattened)

    def test_ordering_a_scraper_moves_its_zone(self):
        w = make_world(2)
        u = scraper(w)
        x, y = find_spot(w, "solar", (w.lander.x, w.lander.y), 15, 30)
        ok, _ = w.command_unit(u.id, "move", x, y)
        self.assertTrue(ok)
        self.assertEqual(u.zone, (x, y))


class SorterTests(unittest.TestCase):
    def test_sorter_picks_by_the_ground_it_stands_on(self):
        w = make_world(3)
        w.research.done.add("sorting")
        s = built_structure(w, "sorter")
        zone = G.zone_at(w.heightmap.geology, s.x, s.y)
        weights = STRUCTURES["sorter"]["sorts"][zone]
        counts = {}
        for _ in range(600):
            out = P.cycle_outputs(w, s, P.recipe(s))
            self.assertEqual(sum(out.values()), 1)
            k = next(iter(out))
            counts[k] = counts.get(k, 0) + 1
        top = max(weights, key=weights.get)
        self.assertEqual(max(counts, key=counts.get), top)

    def test_scrap_furnace_makes_iron(self):
        w = make_world(1)
        f = built_structure(w, "scrap_furnace")
        f.powered = True
        f.inputs = {"scrap": 4}
        w.produced["scrap"] = w.produced.get("scrap", 0)
        for _ in range(2 * int(P.recipe(f)["time_s"] * W.TICK_RATE) + 4):
            P.update(w, f)
        self.assertEqual(f.outputs.get("iron", 0), 2)


class ConstructionFirstTests(unittest.TestCase):
    def test_storage_keeps_back_what_sites_need(self):
        w = make_world(1)
        built_structure(w, "scrap_furnace")
        w.lander.storage["scrap"] = 20
        site, _ = w.place("solar", *find_spot(w, "solar", (w.lander.x, w.lander.y), 5, 15))
        need = site.materials_needed()["scrap"]
        offered = sum(n for s, item, n, kind in jobs.offers(w) if kind == "storage" and item == "scrap")
        self.assertEqual(offered, 20 - need)


class MassDriverTests(unittest.TestCase):
    def setUp(self):
        self.w = make_world(1)
        L = self.w.lander
        x, y = find_spot(self.w, "mass_driver", (L.x, L.y), 7, 40)
        self.md, _ = self.w.place("mass_driver", x, y)
        ST.complete(self.w, self.md)

    def test_only_one(self):
        L = self.w.lander
        self.assertEqual(self.w.place("mass_driver", L.x + 30, L.y)[1], "ONLY ONE MASS DRIVER")

    def test_phases_open_research_and_the_launch_wins(self):
        w, md = self.w, self.md
        self.assertEqual(w.start_research("prospecting")[1], "NEEDS MASS DRIVER PHASE 1")
        for i, ph in enumerate(MD.phases(md)):
            for k, n in ph["needs"].items():
                w.produced[k] = w.produced.get(k, 0) + n
                self.assertEqual(w.deliver(md, k, n + 5), n)   # never more than the bill
            w.tick()
            self.assertEqual(md.phase, i + 1)
            self.assertEqual(w.research.phase, i + 1)
            for k in ph["needs"]:
                self.assertTrue(ledger_ok(w, k)[0], k)
        self.assertTrue(w.start_research("prospecting")[0])
        self.assertEqual(md.status, MD.CHARGING)
        self.assertEqual(md.draw_kw(), md.spec["launch_kw"])
        w.tick()
        self.assertFalse(md.powered)        # the lander alone can't carry it
        md.powered = True
        w.dirty_power = False
        for _ in range(int(md.spec["launch_charge_s"] * W.TICK_RATE) + 2):
            md.powered = True
            MD.update(w, md)
        self.assertEqual(w.outcome, "won")

    def test_haulers_are_asked_for_the_current_bill(self):
        w, md = self.w, self.md
        wanted = {item: space for s, item, space, mult in jobs.requests(w) if s is md}
        self.assertEqual(wanted, MD.phases(md)[0]["needs"])


if __name__ == "__main__":
    unittest.main()


class ProductionPanelTests(unittest.TestCase):
    def test_history_rates_and_colony_output(self):
        from game.sim import stats
        w = make_world(2)
        for _ in range(minutes(6)):
            w.tick()
        self.assertEqual(len(w.history), 6 * 60 // W.HISTORY_SAMPLE_S)
        self.assertIn("regolith", stats.made_items(w))
        series = stats.series(w, "regolith")
        self.assertEqual(len(series), len(w.history) - 1)
        self.assertGreater(max(series), 0)
        made = stats.made(w)["scrap"] - (w.history[0][1].get("scrap", 0))
        self.assertGreaterEqual(made, 0)
        self.assertGreaterEqual(stats.colony_output(w), 0.0)
        loaded = run_to_completion(build_world(2, w.heightmap))
        save.apply(loaded, save.read(save.dumps(w)))
        self.assertEqual(stats.series(loaded, "regolith"), series)
