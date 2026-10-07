"""Tier III: the molten regolith cell, helium harvesters and fusion."""

import unittest

from game.content.structures import STRUCTURES
from game.sim import geology as G
from game.sim import production as P
from tests.test_build_power import run_until
from tests.test_chain import built_structure, ledger_ok
from tests.test_tier2 import TIER2
from tests.test_world import make_world, minutes

TIER3 = TIER2 | {"molten_regolith", "harvesters", "fusion"}


def site(seed=1):
    w = make_world(seed)
    w.research.done.update(TIER3)
    w.research.phase = 3
    return w


class MoltenRegolithTests(unittest.TestCase):
    def test_metals_from_raw_regolith_depend_on_the_ground(self):
        w = site()
        cell = built_structure(w, "molten_regolith_cell")
        zone = G.zone_at(w.heightmap.geology, cell.x, cell.y)
        odds = STRUCTURES["molten_regolith_cell"]["chance_by_zone"][zone]
        made = [P.cycle_outputs(w, cell, P.recipe(cell)) for _ in range(1000)]
        self.assertTrue(all(m["iron"] == 1 and m["slag"] == 2 for m in made))
        for item, p in odds.items():
            share = sum(item in m for m in made) / len(made)
            self.assertAlmostEqual(share, p, delta=0.06)


class FusionTests(unittest.TestCase):
    def test_fusion_runs_on_helium_and_deuterium_and_wants_radiators(self):
        w = site()
        r = built_structure(w, "fusion_reactor")
        w.structures_changed()
        self.assertAlmostEqual(r.cooling, 0.5)
        r.inputs = {"he3": 1, "deuterium": 1}
        w.produced.update(he3=1, deuterium=1)
        r.powered = True
        P.update(w, r)
        self.assertEqual(r.output_kw, 150.0)
        self.assertEqual(r.inputs, {"he3": 0, "deuterium": 0})
        self.assertTrue(ledger_ok(w, "he3")[0])


class HarvesterTests(unittest.TestCase):
    def test_a_harvester_brings_back_helium_and_no_regolith(self):
        w = site(2)
        L = w.lander
        u = w.spawn_unit("harvester", L.x + 2, L.y + 2)
        self.assertTrue(run_until(w, lambda: w.stock("he3") > 0, 8 * 60))
        self.assertEqual(set(u.cargo) - {"he3"}, set())
        self.assertTrue(ledger_ok(w, "he3")[0])

    def test_mare_yields_more_than_highlands(self):
        from game.content import units as U
        y = U.UNITS["harvester"]["yield_by_zone"]
        self.assertGreater(y[G.MARE], y[G.KREEP])
        self.assertGreater(y[G.KREEP], y[G.HIGHLANDS])


if __name__ == "__main__":
    unittest.main()
