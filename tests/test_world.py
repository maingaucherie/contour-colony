import unittest

from game.content import units as U
from game.content import world as W
from game.content.items import ITEMS
from game.sim import debris as DB
from game.sim import units as US
from game.sim.terrain import generate_terrain, run_to_completion
from game.sim.world import build_world

_heightmaps = {}


def make_world(seed):
    if seed not in _heightmaps:
        _heightmaps[seed] = run_to_completion(generate_terrain(seed))
    return run_to_completion(build_world(seed, _heightmaps[seed]))


def minutes(m):
    return int(m * 60 * W.TICK_RATE)


class WorldSetupTests(unittest.TestCase):
    def test_lander_on_open_ground_with_starting_units_docked(self):
        w = make_world(1)
        self.assertTrue(w.grid.open[w.grid.node_at(w.lander.x, w.lander.y)])
        scavengers = [u for u in w.units.values() if u.kind == "scavenger"]
        self.assertEqual(len(scavengers), U.UNITS["scavenger"]["start_count"])
        for u in scavengers:
            self.assertTrue(u.docked)
            self.assertEqual(w.lander.dock_users[u.slot], u.id)

    def test_initial_debris_on_weighted_cells(self):
        w = make_world(1)
        self.assertEqual(len(w.debris), W.DEBRIS_INITIAL)
        size = w.heightmap.size
        for d in w.debris.values():
            i = int(d.y + 0.5) * size + int(d.x + 0.5)
            i = min(i, len(w.debris_weights) - 1)
            weight = w.debris_weights[i] - (w.debris_weights[i - 1] if i else 0.0)
            # Sampling jitters within half a cell, so check the sampled cell or a neighbour.
            near = [w.debris_weights[j] - w.debris_weights[j - 1] for j in (i - 1, i, i + 1) if 0 < j < len(w.debris_weights)]
            self.assertTrue(weight > 0 or any(v > 0 for v in near))


class ConservationAndReservationTests(unittest.TestCase):
    def test_scrap_is_conserved_and_never_double_claimed(self):
        w = make_world(2)
        for t in range(minutes(8)):
            w.tick()
            if t % 700 == 0:
                w.sell_scrap(5)
            self.assertEqual(w.scrap_accounted(), w.scrap_spawned)
            targets = [u.target for u in w.units.values() if u.target is not None]
            self.assertEqual(len(targets), len(set(targets)))
            for u in w.units.values():
                if u.target is not None:
                    self.assertEqual(w.debris[u.target].claimed_by, u.id)
            for d in w.debris.values():
                if d.claimed_by is not None:
                    self.assertEqual(w.units[d.claimed_by].target, d.id)
            self.assertLessEqual(len(w.debris), W.DEBRIS_MAX)
            self.assertLessEqual(w.lander.stored(), w.lander.spec["storage"])


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
            self.assertEqual(charged, set(w.units), f"seed {seed}: every scavenger should charge")

    def test_low_battery_drops_job_and_returns_home_before_dying(self):
        w = make_world(1)
        unit = next(iter(w.units.values()))
        # Let it leave on a job, then drain it to just above the low threshold.
        while unit.state != US.TO_DEBRIS:
            w.tick()
        target = unit.target
        low = U.LOW_BATTERY_FRACTION * unit.spec["battery"]
        unit.battery = low + 0.05
        while unit.state == US.TO_DEBRIS:
            w.tick()
        self.assertEqual(unit.state, US.TO_DOCK)
        self.assertIsNone(unit.target)
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
        for _ in range(minutes(2)):
            w.tick()
        stored = w.lander.storage.get("scrap", 0)
        self.assertGreater(stored, 0)
        sold = w.sell_scrap(stored + 100)
        self.assertEqual(sold, stored)
        self.assertEqual(w.credits, stored * ITEMS["scrap"]["sell_price"])
        self.assertEqual(w.lander.storage.get("scrap", 0), 0)
        self.assertEqual(w.sell_scrap(1), 0)

    def test_debris_respawns_one_per_interval_up_to_cap(self):
        w = make_world(4)
        for unit in w.units.values():
            unit.state, unit.timer = US.IDLE, 10 ** 9  # park the scavengers
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
        weights = w.debris_weights
        spec = U.UNITS["scavenger"]
        usable = (1.0 - U.LOW_BATTERY_FRACTION) * spec["battery"] - spec["pickup_energy"]
        max_trip = usable / (spec["drain_per_cost_cell"] * U.TRIP_SAFETY_FACTOR)
        size = w.heightmap.size
        for i in range(1, size * size, 97):
            node = w.grid.node_at(i % size, i // size)
            if 2 * w.home_field.dist[node] > max_trip:
                self.assertEqual(weights[i], weights[i - 1])


class DeterminismTests(unittest.TestCase):
    def run_world(self, seed, ticks):
        w = make_world(seed)
        for t in range(ticks):
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
