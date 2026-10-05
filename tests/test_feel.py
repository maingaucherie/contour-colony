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


class SceneryTests(unittest.TestCase):
    def test_scenery_surrounds_the_site_and_fades_in_from_its_edge(self):
        from game.content import terrain as T
        from game.render.contours import build_contours
        from game.render.scenery import build_scenery
        from game.sim.terrain import generate_terrain, run_to_completion
        hm = run_to_completion(generate_terrain(4))
        contours = run_to_completion(build_contours(hm))
        sc = run_to_completion(build_scenery(hm, contours.interval, 4))
        self.assertTrue(sc.levels)
        edge = hm.size - 1
        m = T.SCENERY_MARGIN_CELLS
        for k, lines in sc.levels:
            self.assertEqual(k % T.SCENERY_LEVEL_STEP, 0)
            for pl in lines:
                inside = all(0 < x < edge and 0 < y < edge for x, y in pl.points)
                self.assertFalse(inside, "scenery never redraws the site itself")
                self.assertTrue(-m - 1 <= pl.min_x and pl.max_x <= edge + m + 1)


class AmbientSoundTests(unittest.TestCase):
    def test_close_up_loops_are_one_second_and_seam_quietly(self):
        from game.audio.synth import ambient_loop
        from game.content import audio as A
        rate = 8000
        for kind in A.AMBIENT_LOOPS:
            s = ambient_loop(kind, rate)
            self.assertEqual(len(s), rate)
            self.assertLessEqual(max(abs(v) for v in s), 0.8 + 1e-9)
            self.assertLess(abs(s[0]) + abs(s[-1]), 0.05)
