import math
import unittest

from game.sim.terrain import generate_terrain, run_to_completion

SMALL = 64  # small sites keep the tests fast; generation code is size-independent


class TerrainTests(unittest.TestCase):
    def test_same_seed_same_heightmap(self):
        a = run_to_completion(generate_terrain(7, SMALL))
        b = run_to_completion(generate_terrain(7, SMALL))
        self.assertEqual(a.heights.tobytes(), b.heights.tobytes())

    def test_different_seeds_differ(self):
        a = run_to_completion(generate_terrain(7, SMALL))
        b = run_to_completion(generate_terrain(8, SMALL))
        self.assertNotEqual(a.heights.tobytes(), b.heights.tobytes())

    def test_heights_finite_and_bounds_correct(self):
        hm = run_to_completion(generate_terrain(3, SMALL))
        self.assertEqual(len(hm.heights), SMALL * SMALL)
        self.assertTrue(all(math.isfinite(h) for h in hm.heights))
        self.assertEqual(hm.min_h, min(hm.heights))
        self.assertEqual(hm.max_h, max(hm.heights))
        self.assertGreater(hm.max_h - hm.min_h, 0.0)

    def test_progress_is_monotonic_and_ends_at_one(self):
        gen = generate_terrain(5, SMALL)
        values = []
        while True:
            try:
                values.append(next(gen))
            except StopIteration:
                break
        self.assertGreater(len(values), 1)
        self.assertEqual(values, sorted(values))
        self.assertGreaterEqual(values[0], 0.0)
        self.assertAlmostEqual(values[-1], 1.0)

    def test_sample_matches_grid_points_and_slope_is_sane(self):
        hm = run_to_completion(generate_terrain(4, SMALL))
        for x, y in ((0, 0), (10, 20), (SMALL - 1, SMALL - 1)):
            self.assertAlmostEqual(hm.sample(x, y), hm.at(x, y), places=3)
        for x, y in ((5.5, 5.5), (30.2, 12.9)):
            self.assertTrue(0.0 <= hm.slope_deg(x, y) < 90.0)


if __name__ == "__main__":
    unittest.main()
