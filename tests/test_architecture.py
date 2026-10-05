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
