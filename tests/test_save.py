"""Saving and loading: a loaded site carries on exactly as if it never stopped."""

import os
import sys
import unittest

from game.content import world as W
from game.sim import save
from game.sim.terrain import run_to_completion
from game.sim.world import build_world
from tests.test_world import make_world, minutes

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import autoplay  # noqa: E402


def reload(world):
    text = save.dumps(world)
    return save.load(text, world.heightmap, build_world, run_to_completion), text


class SaveTests(unittest.TestCase):
    def test_a_loaded_site_continues_identically(self):
        # A busy site: the bot builds, researches, hauls and takes contracts.
        w = autoplay.make(3)
        bot = autoplay.Bot(w)
        for t in range(minutes(25)):
            if t % W.TICK_RATE == 0:
                bot.step()
            w.tick()
        loaded, text = reload(w)
        self.assertEqual(loaded.digest(), w.digest())
        for _ in range(minutes(5)):
            w.tick()
            loaded.tick()
        self.assertEqual(loaded.digest(), w.digest())
        self.assertLess(len(text), 600_000, "a save should stay small enough for browser storage")

    def test_fresh_site_round_trip_and_version_check(self):
        w = make_world(1)
        loaded, text = reload(w)
        self.assertEqual(loaded.digest(), w.digest())
        bad = text.replace(f'"version":{W.SAVE_VERSION}', '"version":-1', 1)
        with self.assertRaises(save.SaveError):
            save.read(bad)
        self.assertIsNone(save.summary(bad))
        self.assertEqual(save.summary(text)["seed"], 1)


if __name__ == "__main__":
    unittest.main()
