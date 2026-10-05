"""Landing briefing and worn tracks."""

import unittest

from game.content import world as W
from game.sim import body
from tests.test_world import make_world, minutes


class BodyTests(unittest.TestCase):
    def test_deterministic_and_plausible(self):
        for seed in range(20):
            a, b = body.generate(seed), body.generate(seed)
            self.assertEqual(a, b)
            self.assertGreater(a["gravity_g"], 0)
            lo, hi = a["temp_c"]
            self.assertLess(lo, hi)
            lines = body.briefing_lines(seed, a)
            self.assertIn(str(seed), lines[0])
            self.assertTrue(all(line == line.upper() for line in lines))  # the Hershey font is capitals


class TrackTests(unittest.TestCase):
    def test_busy_routes_show_and_fade(self):
        w = make_world(1)
        for _ in range(minutes(10)):
            w.tick()
        shown = w.tracks.visible()
        self.assertTrue(shown, "ten minutes of scavenging should wear some tracks")
        for x, y, angle, strength in shown:
            self.assertTrue(0 <= strength <= 1)
        # Left alone, every track fades away.
        for _ in range(200):
            w.tracks.fade()
        self.assertEqual(w.tracks.visible(), [])
        self.assertLess(len(w.tracks.cells), 5)


if __name__ == "__main__":
    unittest.main()
