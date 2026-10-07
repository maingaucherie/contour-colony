import unittest

from game.content import units as U
from game.content import world as W
from game.content.items import ITEMS
from game.sim import units as US
from game.sim.terrain import generate_terrain, run_to_completion
from game.sim.world import build_world

_heightmaps = {}
TEST_SIZE = 256   # a quarter of the game's site: the same rules, much faster tests


def make_world(seed):
    if seed not in _heightmaps:
        _heightmaps[seed] = run_to_completion(generate_terrain(seed, TEST_SIZE))
    return run_to_completion(build_world(seed, _heightmaps[seed]))


def minutes(m):
    return int(m * 60 * W.TICK_RATE)


def scavengers(w):
    return [u for u in w.units.values() if u.kind == "scavenger"]


class WorldSetupTests(unittest.TestCase):
    def test_lander_on_open_ground_with_starting_units_docked(self):
        w = make_world(1)
        self.assertTrue(w.grid.open[w.grid.node_at(w.lander.x, w.lander.y)])
        for kind in ("scavenger", "constructor"):
            units = [u for u in w.units.values() if u.kind == kind]
            self.assertEqual(len(units), U.UNITS[kind]["start_count"])
        for u in w.units.values():
            self.assertTrue(u.docked)
            self.assertEqual(w.lander.dock_users[u.slot], u.id)

    def test_initial_debris_on_weighted_cells(self):
        w = make_world(1)
        self.assertEqual(len(w.debris), W.DEBRIS_INITIAL)
        size = w.heightmap.size
        for d in w.debris.values():
            # Sampling jitters within half a cell, so check the sampled cell or a neighbour.
            cells = [int(d.y + oy) * size + int(d.x + ox) for ox in (-0.5, 0, 0.5) for oy in (-0.5, 0, 0.5)]
            self.assertTrue(any(w.spawn_map.cell_weight(i) > 0 for i in cells if 0 <= i < size * size))

    def test_landing_area_is_surveyed(self):
        w = make_world(1)
        self.assertEqual(w.survey.level_at(w.lander.x, w.lander.y), 2)
        self.assertGreater(w.survey.coverage(1), 0.0)
        self.assertLess(w.survey.coverage(1), 0.2)


class ConservationAndReservationTests(unittest.TestCase):
    def test_scrap_is_conserved_and_never_double_claimed(self):
        w = make_world(2)
        for t in range(minutes(8)):
            w.tick()
            if t % 700 == 0:
                w.sell_scrap(5)
            self.assertEqual(w.scrap_accounted(), w.scrap_spawned)
            targets = [u.target for u in scavengers(w) if u.activity in ("to_debris", "pickup")]
            self.assertEqual(len(targets), len(set(targets)))
            for u in scavengers(w):
                if u.activity in ("to_debris", "pickup"):
                    self.assertEqual(w.debris[u.target].claimed_by, u.id)
            for d in w.debris.values():
                if d.claimed_by is not None:
                    self.assertEqual(w.units[d.claimed_by].target, d.id)
            self.assertLessEqual(len(w.debris), W.DEBRIS_MAX)
            for s in w.storages():
                self.assertLessEqual(s.stored(), s.spec["storage"])


class BatteryTests(unittest.TestCase):
    def test_scavengers_never_run_flat_and_do_recharge(self):
        for seed in (1, 3, 4):
            w = make_world(seed)
            charged = set()
            for _ in range(minutes(20)):
                w.tick()
                for u in w.units.values():
                    self.assertGreater(u.battery, 0.0, f"seed {seed} unit {u.id}")
                    self.assertNotEqual(u.state, US.STRANDED)
                    if u.state == US.CHARGING:
                        charged.add(u.id)
            self.assertLessEqual({u.id for u in scavengers(w)}, charged, f"seed {seed}: every scavenger should charge")

    def test_low_battery_drops_job_and_returns_home_before_dying(self):
        w = make_world(1)
        unit = scavengers(w)[0]
        # Let it leave on a job, then drain it to just above the low threshold.
        while unit.activity != "to_debris":
            w.tick()
        target = unit.target
        unit.battery = U.LOW_BATTERY_FRACTION * US.capacity(w, unit) + 0.05
        while unit.activity == "to_debris":
            w.tick()
        self.assertEqual(unit.activity, "to_charge")
        if target in w.debris:
            self.assertIsNone(w.debris[target].claimed_by)
        for _ in range(minutes(3)):
            w.tick()
            self.assertGreater(unit.battery, 0.0)
            if unit.state == US.CHARGING:
                break
        self.assertEqual(unit.state, US.CHARGING)
        self.assertTrue(unit.docked)


class EconomyTests(unittest.TestCase):
    def test_scrap_accumulates_and_sells_for_credits(self):
        w = make_world(3)
        start_scrap = w.lander.storage.get("scrap", 0)
        for _ in range(minutes(2)):
            w.tick()
        stored = w.lander.storage.get("scrap", 0)
        self.assertGreater(stored, start_scrap)
        credits = w.credits
        sold = w.sell_scrap(stored + 100)
        self.assertEqual(sold, stored)
        self.assertEqual(w.credits - credits, stored * ITEMS["scrap"]["sell_price"])
        self.assertEqual(w.lander.storage.get("scrap", 0), 0)
        self.assertEqual(w.sell_scrap(1), 0)

    def test_debris_respawns_one_per_interval_up_to_cap(self):
        w = make_world(4)
        for unit in w.units.values():
            unit.state, unit.timer = US.IDLE, 10 ** 9  # park everyone
        w.debris.clear()
        w.scrap_spawned = 0
        interval = round(W.DEBRIS_SPAWN_INTERVAL_S * W.TICK_RATE)
        w.debris_timer = interval
        for _ in range(interval * 3):
            w.tick()
        self.assertEqual(len(w.debris), 3)
        for _ in range(interval * (W.DEBRIS_MAX + 5)):
            w.tick()
        self.assertEqual(len(w.debris), W.DEBRIS_MAX)

    def test_spawn_weights_zero_beyond_round_trip_range(self):
        w = make_world(1)
        spec = U.UNITS["scavenger"]
        usable = (1.0 - U.LOW_BATTERY_FRACTION) * spec["battery"] - spec["pickup_energy"]
        max_trip = usable / (spec["drain_per_cost_cell"] * U.TRIP_SAFETY_FACTOR)
        cum = w.spawn_map.cumulative
        for node in range(len(cum)):
            weight = cum[node] - (cum[node - 1] if node else 0.0)
            if 2 * w.charge_field.dist[node] > max_trip:
                self.assertEqual(weight, 0.0)


class DeterminismTests(unittest.TestCase):
    def run_world(self, seed, ticks):
        w = make_world(seed)
        for t in range(ticks):
            if t == 50:
                w.start_research("sorting")
            if t in (1200, 3100):
                w.sell_scrap(3)
            w.tick()
        return w.digest()

    def test_same_seed_same_inputs_same_state_after_5000_ticks(self):
        self.assertEqual(self.run_world(5, 5000), self.run_world(5, 5000))

    def test_different_seed_differs(self):
        self.assertNotEqual(self.run_world(5, 500), self.run_world(6, 500))


if __name__ == "__main__":
    unittest.main()


class StrandedTests(unittest.TestCase):
    def test_stranded_units_trickle_charge_and_head_home(self):
        w = make_world(1)
        unit = scavengers(w)[0]
        unit.x, unit.y = w.lander.x + 20, w.lander.y
        US.release_dock(w, unit)
        unit.battery = 0.0
        unit.state, unit.activity = US.STRANDED, "stranded"
        for _ in range(minutes(20)):
            w.tick()
            if unit.state != US.STRANDED:
                break
        self.assertNotEqual(unit.state, US.STRANDED)
        self.assertIn(unit.activity, ("to_charge", "charging", "idle", "waiting for a dock"))
        for _ in range(minutes(3)):
            w.tick()
        self.assertGreater(unit.battery, 0.0)
