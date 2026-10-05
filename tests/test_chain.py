"""Milestone 4: production, the job board, contracts, orbital passes, win and loss."""

import os
import sys
import unittest

from game.content import contracts as C
from game.content import world as W
from game.content.items import ITEMS
from game.sim import production as P
from game.sim import structures as ST
from game.sim.orbit import Orbit
from tests.test_build_power import find_spot
from tests.test_world import make_world, minutes

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import autoplay  # noqa: E402


def built_structure(w, kind, near=None, rmin=4.0):
    """A finished, powered structure placed next to the lander (no construction)."""
    w.research.done.update({"field_survey", "extraction", "sintering", "logistics_1", "electrolysis", "reduction"})
    L = w.lander
    x, y = find_spot(w, kind, near or (L.x, L.y), rmin)
    s = ST.Structure(w.new_id(), kind, x, y)
    w.structures[s.id] = s
    ST.complete(w, s)
    return s


def ledger_ok(w, item):
    start = W.START_STORAGE.get(item, 0)
    if item == "scrap":
        expected = start + w.scrap_spawned + w.produced.get(item, 0) - w.consumed.get(item, 0) - w.scrap_sold
    else:
        expected = start + w.produced.get(item, 0) - w.consumed.get(item, 0)
    return w.item_total(item) == expected, (item, w.item_total(item), expected)


class ProductionTests(unittest.TestCase):
    def test_cycle_consumes_produces_and_backpressures(self):
        w = make_world(1)
        crusher = built_structure(w, "crusher")
        w.dirty_power = True
        w.tick()
        self.assertTrue(crusher.powered)
        self.assertEqual(crusher.status, P.STARVED)
        crusher.inputs["ilmenite"] = 6
        w.produced["ilmenite"] = 6  # put there by hand
        P.update(w, crusher)
        self.assertEqual(crusher.status, P.WORKING)
        self.assertEqual(crusher.inputs["ilmenite"], 4)
        for _ in range(int(P.cycle_time(crusher) * W.TICK_RATE) + 1):
            P.update(w, crusher)
        self.assertEqual(crusher.outputs.get("concentrate"), 1)
        # A full output buffer blocks the next cycle.
        crusher.outputs["concentrate"] = P.output_cap(crusher, "concentrate")
        crusher.cycle_left_s = 0.0
        P.update(w, crusher)
        self.assertEqual(crusher.status, P.BLOCKED)
        crusher.outputs["concentrate"] = 0
        crusher.powered = False
        P.update(w, crusher)
        self.assertEqual(crusher.status, P.UNPOWERED)


class ChainRunTests(unittest.TestCase):
    """A bot-played site: items are conserved and reservations stay consistent."""

    @classmethod
    def setUpClass(cls):
        cls.w = autoplay.make(5)
        cls.bot = autoplay.Bot(cls.w)
        cls.violations = []
        cls.ledger = []
        w = cls.w
        for t in range(minutes(40)):
            if t % W.TICK_RATE == 0:
                cls.bot.step()
            w.tick()
            if t % 50 == 0:
                cls._check(w)
            if w.outcome:
                break

    @classmethod
    def _check(cls, w):
        for item in ITEMS:
            ok, info = ledger_ok(w, item)
            if not ok:
                cls.ledger.append((w.time_s(), info))
        # Every reservation is backed by a hauler's job, and never exceeds what's there.
        out, into = {}, {}
        for u in w.units.values():
            if u.haul is not None:
                src, dst, item, amount = u.haul
                if src is not None and not u.cargo_total():
                    out[(src, item)] = out.get((src, item), 0) + amount
                if dst is not None:
                    into[(dst, item)] = into.get((dst, item), 0) + amount
        for s in w.structures.values():
            for item, n in s.reserved_out.items():
                if out.get((s.id, item), 0) != n:
                    cls.violations.append((w.time_s(), "out", s.kind, item, n, out.get((s.id, item), 0)))
                held = (s.outputs if P.recipe(s) and item in s.outputs else s.storage).get(item, 0)
                if n > held:
                    cls.violations.append((w.time_s(), "over", s.kind, item, n, held))
            for item, n in s.reserved_in.items():
                if into.get((s.id, item), 0) != n:
                    cls.violations.append((w.time_s(), "in", s.kind, item, n, into.get((s.id, item), 0)))

    def test_production_happened(self):
        self.assertGreater(self.w.produced.get("concentrate", 0), 20)
        self.assertGreater(self.w.contracts.filled, 0)

    def test_items_are_conserved(self):
        self.assertEqual(self.ledger[:5], [])

    def test_reservations_match_hauler_jobs(self):
        self.assertEqual(self.violations[:5], [])


class ContractTests(unittest.TestCase):
    def test_offer_fill_and_expire(self):
        w = make_world(2)
        while not w.contracts.open:
            w.tick()
        self.assertAlmostEqual(w.time_s(), C.FIRST_CONTRACT_S, delta=0.2)
        c = w.contracts.open[0]
        credits, rep = w.credits, w.contracts.reputation
        # Haulers delivering to the lander's export bay fill it.
        taken = w.deliver(w.lander, c.good, c.qty + 5)
        self.assertEqual(taken, min(c.qty + 5, c.qty + w.lander.spec["storage"] - w.lander.stored()))
        w.tick()
        self.assertNotIn(c, w.contracts.open)
        self.assertEqual(w.credits, credits + c.payout())
        self.assertAlmostEqual(w.contracts.reputation, rep + C.REPUTATION_ON_TIME, delta=0.1)
        # The next one runs out: late first, then expired.
        while not w.contracts.open:
            w.tick()
        c2 = w.contracts.open[0]
        while c2 in w.contracts.open and not c2.late:
            w.tick()
        self.assertTrue(c2.late)
        rep = w.contracts.reputation
        while c2 in w.contracts.open:
            w.tick()
        self.assertEqual(w.contracts.expired, 1)
        self.assertLess(w.contracts.reputation, rep + C.REPUTATION_EXPIRED + 1)

    def test_building_materials_in_the_hold_are_not_shipped(self):
        w = make_world(2)
        c = w.contracts._issue(0.0, {"good": "parts", "qty": (5, 5), "minutes": 10})
        parts = w.lander.storage["parts"]
        w.tick()
        self.assertEqual(w.lander.storage["parts"], parts)
        self.assertEqual(c.delivered, 0)

    def test_neglect_loses_and_stops_the_clock(self):
        w = make_world(3)
        for _ in range(minutes(60)):
            w.tick()
            if w.outcome:
                break
        self.assertEqual(w.outcome, "lost")
        ticks = w.tick_count
        w.tick()
        self.assertEqual(w.tick_count, ticks)

    def test_standing_contract_win_needs_two_fills_without_drops(self):
        w = make_world(2)
        built_structure(w, "machine_shop")
        w.contracts.filled = C.STANDING_AFTER
        w.credits = 10_000

        def fill_standing():
            while not any(c.standing for c in w.contracts.open):
                w.tick()
            c = next(c for c in w.contracts.open if c.standing)
            w.contracts.receive(w, c.good, c.remaining())
            w.tick()

        fill_standing()
        self.assertEqual(w.contracts.standing_streak, 1)
        w.order_supply(0)            # a drop in between breaks the streak
        fill_standing()
        self.assertIsNone(w.outcome)
        self.assertEqual(w.contracts.standing_streak, 1)
        fill_standing()
        self.assertEqual(w.outcome, "won")
        self.assertGreater(w.score(), 0)


class OrbitTests(unittest.TestCase):
    def test_pass_windows(self):
        self.assertFalse(Orbit.overhead(C.FIRST_PASS_S - 1))
        self.assertTrue(Orbit.overhead(C.FIRST_PASS_S + 1))
        self.assertFalse(Orbit.overhead(C.FIRST_PASS_S + C.PASS_DURATION_S + 1))
        self.assertTrue(Orbit.overhead(C.FIRST_PASS_S + C.PASS_PERIOD_S + 1))
        self.assertAlmostEqual(Orbit.seconds_to_change(C.FIRST_PASS_S + 10), C.PASS_DURATION_S - 10)

    def test_drops_land_during_a_pass(self):
        w = make_world(1)
        w.credits = 1000
        parts = w.lander.storage["parts"]
        units = len(w.units)
        crate = next(i for i, e in enumerate(C.SUPPLY) if e.get("items", {}).get("parts"))
        hauler = next(i for i, e in enumerate(C.SUPPLY) if e.get("unit") == "hauler")
        self.assertTrue(w.order_supply(crate)[0])
        self.assertTrue(w.order_supply(hauler)[0])
        self.assertEqual(w.credits, 1000 - C.SUPPLY[crate]["cost"] - C.SUPPLY[hauler]["cost"])
        while w.time_s() < C.FIRST_PASS_S - 1:
            w.tick()
        self.assertEqual(w.lander.storage["parts"], parts)   # nothing before the pass
        while w.time_s() < C.FIRST_PASS_S + C.DROP_FALL_S + 1:
            w.tick()
        self.assertEqual(w.lander.storage["parts"] - parts, C.SUPPLY[crate]["items"]["parts"])
        self.assertEqual(len(w.units), units + 1)
        self.assertTrue(ledger_ok(w, "parts")[0])

    def test_one_scan_per_pass(self):
        w = make_world(1)
        self.assertFalse(w.orbital_scan(10, 10)[0])          # not overhead yet
        while not Orbit.overhead(w.time_s()):
            w.tick()
        w.tick()
        x, y = w.lander.x + 60, w.lander.y
        self.assertTrue(w.orbital_scan(x, y)[0])
        self.assertGreaterEqual(w.survey.level_at(x, y), 1)
        self.assertFalse(w.orbital_scan(x, y)[0])


class ExitTests(unittest.TestCase):
    """Milestone 4 exit: one full site is winnable and losable."""

    def test_a_played_site_is_won(self):
        w = autoplay.make(5)
        autoplay.play(w, 80)
        self.assertEqual(w.outcome, "won", autoplay.status(w))

    def test_a_neglected_site_is_lost(self):
        w = autoplay.make(5)
        autoplay.play(w, 80, neglect=True)
        self.assertEqual(w.outcome, "lost")


if __name__ == "__main__":
    unittest.main()
