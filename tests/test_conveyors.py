"""Conveyors: planning rules, building, power and moving items."""

import math
import unittest

from game.content import structures as S
from game.content import world as W
from game.sim import conveyors as C
from game.sim import save
from game.sim import structures as ST
from tests.test_build_power import run_until
from tests.test_chain import built_structure, ledger_ok
from tests.test_industry import finish
from tests.test_world import make_world


def linked_pair(w, a, kind, gap=(4.0, 10.0)):
    """Finish a building of kind gap cells (edge to edge) from a, where a
    conveyor from a to it could be built. Returns it."""
    for want in [gap[0] + 0.5 * i for i in range(int((gap[1] - gap[0]) * 2) + 1)]:
        for deg in range(0, 360, 15):
            r = a.spec["footprint_cells"] + S.STRUCTURES[kind]["footprint_cells"] + want
            x, y = a.x + r * math.cos(math.radians(deg)), a.y + r * math.sin(math.radians(deg))
            if not ST.check_placement(w, kind, x, y)[0]:
                continue
            b = finish(w, kind, x, y)
            if C.plan(w, a, b)["ok"] and C.plan(w, a, b)["credits"] == 0:
                return b
            del w.structures[b.id]
    raise AssertionError(f"no spot for a conveyor to {kind}")


def researched(w):
    w.research.done.add("conveyors")
    return w


class PlanTests(unittest.TestCase):
    def test_rules(self):
        w = researched(make_world(1))
        crusher = built_structure(w, "crusher")
        furnace = linked_pair(w, crusher, "reduction_furnace")
        w.research.done.discard("conveyors")
        self.assertEqual(C.plan(w, crusher, furnace)["reason"], "NOT RESEARCHED")
        researched(w)
        p = C.plan(w, crusher, furnace)
        self.assertTrue(p["ok"], p["reason"])
        self.assertEqual(p["items"], ["concentrate"])
        self.assertIn("USES NOTHING", C.plan(w, furnace, crusher)["reason"])
        self.assertEqual(C.plan(w, crusher, crusher)["reason"], "PICK ANOTHER BUILDING")
        depot = built_structure(w, "depot")
        self.assertEqual(C.plan(w, w.lander, depot)["reason"], "HAULERS MOVE STORAGE TO STORAGE")
        self.assertFalse(C.can_start(built_structure(w, "pylon"))[0])

    def test_too_long_and_already_linked(self):
        w = researched(make_world(1))
        crusher = built_structure(w, "crusher")
        far = finish(w, "reduction_furnace", crusher.x + S.CONVEYOR_MAX_CELLS + 4, crusher.y)
        self.assertTrue(C.plan(w, crusher, far)["reason"].startswith("TOO LONG"))
        del w.structures[far.id]
        furnace = linked_pair(w, crusher, "reduction_furnace")
        c, reason = w.place_conveyor(crusher.id, furnace.id)
        self.assertIsNotNone(c, reason)
        self.assertEqual(C.plan(w, crusher, furnace)["reason"], "ALREADY LINKED")

    def test_cost_grows_with_length(self):
        w = researched(make_world(1))
        crusher = built_structure(w, "crusher")
        furnace = linked_pair(w, crusher, "reduction_furnace", gap=(6.0, 12.0))
        c, _ = w.place_conveyor(crusher.id, furnace.id)
        self.assertEqual(c.build_cost(), {"sinter": math.ceil(c.length - 1e-6)})
        self.assertGreater(c.build_time(), S.STRUCTURES["conveyor"]["build_time_s"] + c.length * 0.9)
        self.assertEqual(c.materials_needed(), c.build_cost())

    def test_buildings_cannot_sit_on_a_conveyor(self):
        w = researched(make_world(1))
        crusher = built_structure(w, "crusher")
        furnace = linked_pair(w, crusher, "reduction_furnace", gap=(7.0, 12.0))
        c, _ = w.place_conveyor(crusher.id, furnace.id)
        ok, reason = ST.check_placement(w, "pylon", c.x, c.y)
        self.assertFalse(ok)
        self.assertEqual(reason, "OVERLAPS CONVEYOR")


class TransferTests(unittest.TestCase):
    def build(self, w, a, b):
        c, reason = w.place_conveyor(a.id, b.id)
        self.assertIsNotNone(c, reason)
        ST.complete(w, c)
        w.tick()
        self.assertTrue(c.powered)
        return c

    def test_producer_to_consumer(self):
        w = researched(make_world(1))
        crusher = built_structure(w, "crusher")
        furnace = linked_pair(w, crusher, "reduction_furnace")
        c = self.build(w, crusher, furnace)
        self.assertEqual(c.grid, crusher.grid)
        crusher.outputs["concentrate"] = 4
        crusher.reserved_out["concentrate"] = 1   # a hauler's: never taken
        w.produced["concentrate"] = 4
        for _ in range(int(5 * W.TICK_RATE / S.CONVEYOR_ITEMS_PER_S)):
            w.tick()
        self.assertEqual(furnace.inputs.get("concentrate", 0), 3)
        self.assertEqual(crusher.outputs["concentrate"], 1)
        self.assertEqual(c.moved, 3)
        self.assertTrue(ledger_ok(w, "concentrate")[0])

    def test_unpowered_conveyor_stops(self):
        w = researched(make_world(1))
        crusher = built_structure(w, "crusher")
        furnace = linked_pair(w, crusher, "reduction_furnace")
        c = self.build(w, crusher, furnace)
        c.priority = "low"
        crusher.outputs["concentrate"] = 4
        w.lander.output_kw = 0.0
        w.dirty_power = True
        for _ in range(3 * W.TICK_RATE):
            w.tick()
        self.assertFalse(c.powered)
        self.assertEqual(furnace.inputs.get("concentrate", 0), 0)

    def test_producer_to_storage_and_storage_to_consumer(self):
        w = researched(make_world(1))
        kiln = built_structure(w, "sinter_kiln")
        c = self.build(w, kiln, w.lander)
        before = w.lander.storage.get("sinter", 0)
        kiln.outputs = {"sinter": 2}
        w.produced["sinter"] = w.produced.get("sinter", 0) + 2
        self.assertTrue(run_until(w, lambda: "sinter" not in kiln.outputs, 5))
        self.assertEqual(w.lander.storage.get("sinter", 0), before + 2)
        self.assertTrue(ledger_ok(w, "sinter")[0])
        # The lander can also feed a melter its ice.
        melter = linked_pair(w, w.lander, "ice_melter", gap=(3.0, 10.0))
        self.build(w, w.lander, melter)
        w.lander.storage["ice"] = 3
        w.produced["ice"] = w.produced.get("ice", 0) + 3
        self.assertTrue(run_until(w, lambda: melter.inputs.get("ice", 0) == 3, 5))
        self.assertTrue(ledger_ok(w, "ice")[0])
        self.assertGreater(c.moved, 0)


class LifecycleTests(unittest.TestCase):
    def test_constructors_build_it_from_sinter(self):
        w = researched(make_world(1))
        crusher = built_structure(w, "crusher")
        furnace = linked_pair(w, crusher, "reduction_furnace")
        w.lander.storage["sinter"] = 30
        c, _ = w.place_conveyor(crusher.id, furnace.id)
        self.assertTrue(run_until(w, lambda: c.built, 240))
        self.assertEqual(w.consumed.get("sinter", 0), c.cells())

    def test_removing_a_building_removes_its_conveyors(self):
        w = researched(make_world(1))
        crusher = built_structure(w, "crusher")
        furnace = linked_pair(w, crusher, "reduction_furnace")
        c = TransferTests.build(self, w, crusher, furnace)
        site, _ = w.place_conveyor(*sorted([crusher.id, furnace.id]))
        self.assertIsNone(site)  # already linked
        sinter = w.lander.storage.get("sinter", 0)
        ST.dismantle(w, furnace)
        self.assertNotIn(c.id, w.structures)
        furnace_refund = int(S.STRUCTURES["reduction_furnace"]["build_cost"]["sinter"] * S.DECONSTRUCT_REFUND)
        self.assertEqual(w.lander.storage.get("sinter", 0) - sinter,
                         furnace_refund + int(c.cells() * S.DECONSTRUCT_REFUND))

    def test_cancelling_a_site_cancels_its_conveyor_site(self):
        w = researched(make_world(1))
        crusher = built_structure(w, "crusher")
        furnace = linked_pair(w, crusher, "reduction_furnace")
        furnace.built = False
        c, _ = w.place_conveyor(crusher.id, furnace.id)
        self.assertTrue(w.cancel(furnace.id))
        self.assertNotIn(c.id, w.structures)

    def test_saved_and_loaded(self):
        w = researched(make_world(1))
        crusher = built_structure(w, "crusher")
        furnace = linked_pair(w, crusher, "reduction_furnace")
        c = TransferTests.build(self, w, crusher, furnace)
        data = save.read(save.dumps(w))
        fresh = researched(make_world(1))
        save.apply(fresh, data)
        loaded = fresh.structures[c.id]
        self.assertEqual((loaded.src, loaded.dst, loaded.length), (c.src, c.dst, c.length))
        fresh.tick()
        self.assertTrue(loaded.powered)


if __name__ == "__main__":
    unittest.main()
