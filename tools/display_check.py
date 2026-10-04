"""Find which display step crashes on this machine.

Usage: python tools/display_check.py

Each window mode runs in its own subprocess, so a segfault in one doesn't stop
the rest. Every step prints a line as it finishes; the first missing line is
the step that crashed. Paste the whole output into a bug report.
"""

import os
import subprocess
import sys

MODES = {
    "scaled": "pygame.SCALED | pygame.RESIZABLE",
    "plain": "0",
}

STEPS = r'''
import faulthandler, sys
faulthandler.enable()
sys.path.insert(0, __ROOT__)

def step(name):
    print("ok:", name, flush=True)

import pygame
pygame.init()
step("pygame.init")
window = pygame.display.set_mode((960, 540), __FLAGS__)
step("set_mode")
print("    driver:", pygame.display.get_driver(), flush=True)
info = window.get_size(), window.get_bitsize(), [hex(m) for m in window.get_masks()]
print("    window surface:", info, flush=True)
step("read window surface")
pygame.Surface((240, 135))
step("Surface(size) - format copied from the window")
pygame.Surface((240, 135), 0, window)
step("Surface(size, 0, window) - what the old glow code did")
frame = pygame.Surface((960, 540), 0, 32)
small = pygame.Surface((240, 135), 0, 32)
step("Surface(size, 0, 32) - explicit format, what the game uses now")
pygame.transform.smoothscale(frame, (240, 135), small)
step("smoothscale between explicit surfaces")
pygame.draw.aalines(frame, (255, 255, 255), False, [(0, 0), (500, 300), (900, 100)])
window.blit(frame, (0, 0))
pygame.display.flip()
step("blit frame to window + flip")
pygame.event.pump()
step("event pump")
from game.app import App
pygame.display.quit()
app = App(1, scaled=__SCALED__)
step("game App created")
for _ in range(240):
    app.frame()
step("game ran 240 frames (loader done: %s)" % (app.loader is None))
'''


def run(mode, flags, extra_env):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    code = STEPS.replace("__ROOT__", repr(root)).replace("__FLAGS__", flags)
    code = code.replace("__SCALED__", "True" if mode == "scaled" else "False")
    env = dict(os.environ, **extra_env)
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env)
    return proc.returncode, proc.stdout, proc.stderr


def main():
    import platform
    print("python", sys.version.split()[0], platform.platform())
    for key in ("XDG_SESSION_TYPE", "WAYLAND_DISPLAY", "DISPLAY", "SDL_VIDEODRIVER", "SDL_RENDER_DRIVER"):
        print(f"{key}={os.environ.get(key, '')}")
    variants = [("default driver", {})]
    if os.environ.get("WAYLAND_DISPLAY"):
        variants.append(("wayland", {"SDL_VIDEODRIVER": "wayland"}))
    if os.environ.get("DISPLAY"):
        variants.append(("x11", {"SDL_VIDEODRIVER": "x11"}))
    variants.append(("software renderer", {"SDL_RENDER_DRIVER": "software"}))
    for label, env in variants:
        for mode, flags in MODES.items():
            code, out, err = run(mode, flags, env)
            status = "OK" if code == 0 else f"CRASHED (exit {code})"
            print(f"\n=== {label} / {mode} window: {status}")
            print(out.rstrip())
            if code != 0:
                lines = [l for l in err.splitlines() if l.strip()]
                print("    stderr tail:")
                for line in lines[-12:]:
                    print("    " + line)


if __name__ == "__main__":
    main()
