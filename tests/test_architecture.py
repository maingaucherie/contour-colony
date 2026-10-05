import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class ArchitectureTests(unittest.TestCase):
    def test_simulation_and_contour_geometry_do_not_import_pygame(self):
        code = (
            "import sys, game.sim.world, game.sim.terrain, game.render.contours, game.audio.synth, game.content.terrain, game.content.display; "
            "sys.exit('pygame' in sys.modules)"
        )
        result = subprocess.run([sys.executable, "-c", code], cwd=ROOT)
        self.assertEqual(result.returncode, 0, "pygame was imported by headless modules")


if __name__ == "__main__":
    unittest.main()


class KeyBindingTests(unittest.TestCase):
    def test_every_one_shot_binding_is_a_trigger(self):
        try:
            import pygame  # noqa: F401
        except ImportError:
            self.skipTest("pygame not installed")
        from game.content import display as D
        from game.ui import input as I
        held = {a for a in D.KEY_BINDINGS if a.startswith(("pan_", "zoom_"))}
        self.assertEqual(set(D.KEY_BINDINGS) - held - set(I._TRIGGERS), set())
