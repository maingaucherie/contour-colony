"""Tier II: waste stores, generators that burn fuel, reactor cooling, chance outputs."""

import unittest

from game.content import world as W
from game.content.structures import STRUCTURES
from game.sim import jobs
from game.sim import production as P
from game.sim import structures as ST
from tests.test_build_power import find_spot
from tests.test_chain import built_structure, ledger_ok
from tests.test_industry import finish
from tests.test_world import make_world

TIER2 = {"prospecting", "extraction", "aluminium", "fuel_cells", "rare_earths", "titanium", "fission",
         "volatiles", "fabrication", "solar_thermal"}


def site(seed=1):
    w = make_world(seed)
    w.research.done.update(TIER2)
    return w


def run_cycles(w, s, n):
    for _ in range(n * (int(P.recipe(s)["time_s"] * W.TICK_RATE) + 2) + 3):
        P.update(w, s)


class WasteTests(unittest.TestCase):
    def test_only_waste_stores_take_waste(self):
        w = site()
        self.assertFalse(w.lander.accepts("slag"))
        heap = built_structure(w, "slag_heap")
        self.assertTrue(heap.accepts("slag"))
        self.assertFalse(heap.accepts("iron"))
        self.assertNotIn(heap, w.general_storages())
        self.assertEqual(w.item_cap("slag"), STRUCTURES["slag_heap"]["storage"])

    def test_aluminium_cell_makes_slag_that_haulers_take_to_the_heap(self):
        w = site()
        cell = built_structure(w, "aluminium_cell")
        heap = built_structure(w, "slag_heap")
        cell.powered = True
        cell.inputs = {"anorthite": 4}
        w.produced["anorthite"] = 4
        run_cycles(w, cell, 2)
        self.assertEqual(cell.outputs.get("slag"), 2)
        self.assertEqual(cell.outputs.get("aluminium"), 2)
        cell.outputs["slag"] = P.output_cap(cell, "slag")
        dests = {(d.kind, i) for d, i, space, m in jobs.requests(w) if i is None and d.accepts("slag")}
        self.assertEqual(dests, {("slag_heap", None)})
        self.assertTrue(ledger_ok(w, "anorthite")[0])


class GeneratorTests(unittest.TestCase):
    def test_fuel_cells_generate_only_while_fuelled(self):
        w = site()
        bank = built_structure(w, "fuel_cell_bank")
        w.tick()
        self.assertEqual(bank.output_kw, 0.0)
        bank.inputs = {"hydrogen": 4, "oxygen": 2}
        w.produced["hydrogen"] = 4
        w.produced["oxygen"] = 2
        w.tick()
        self.assertEqual(bank.output_kw, STRUCTURES["fuel_cell_bank"]["generates_kw"])
        self.assertTrue(w.dirty_power or bank.grid != -1)
        run_cycles(w, bank, 3)
        P.update(w, bank)
        self.assertEqual(bank.output_kw, 0.0)
        self.assertEqual(bank.outputs.get("water"), 2)

    def test_reactor_needs_radiators_for_full_power(self):
        w = site()
        w.lander.storage["sinter"] = 100
        r = built_structure(w, "fission_reactor")
        w.structures_changed()
        self.assertAlmostEqual(r.cooling, 0.5)
        reach = r.spec["footprint_cells"] + STRUCTURES["radiator"]["footprint_cells"] + r.spec["cooling_reach_cells"]
        for _ in range(r.spec["cooling_radiators"]):
            x, y = find_spot(w, "radiator", (r.x, r.y), 1.0, reach - 0.1)
            finish(w, "radiator", x, y)
        w.structures_changed()
        self.assertAlmostEqual(r.cooling, 1.0)
        r.inputs = {"fuel_rods": 1}
        w.produced["fuel_rods"] = 1
        r.powered = True
        P.update(w, r)
        self.assertEqual(r.output_kw, r.spec["generates_kw"])

    def test_heliostat_output_follows_sunlight(self):
        w = site()
        h = built_structure(w, "heliostat_tower")
        w.structures_changed()
        self.assertAlmostEqual(h.output_kw, h.spec["power_kw"] * w.illumination_at(h.x, h.y))


class ChanceTests(unittest.TestCase):
    def test_volatiles_oven_finds_helium_now_and_then(self):
        w = site()
        oven = built_structure(w, "volatiles_oven")
        made = [P.cycle_outputs(w, oven, P.recipe(oven)) for _ in range(1000)]
        self.assertTrue(all(m["hydrogen"] == 2 for m in made))
        he3 = sum(m.get("he3", 0) for m in made)
        self.assertTrue(50 < he3 < 160, he3)


class SymbolTests(unittest.TestCase):
    def test_every_structure_has_a_symbol(self):
        from game.render import symbols
        missing = [k for k, spec in STRUCTURES.items() if k not in symbols.STRUCTURES and not spec.get("line")]
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
