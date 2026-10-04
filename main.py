"""Contour Colony entry point. pygbag requires main.py at the root and an
async main loop that yields to the browser once per frame."""

import asyncio
import sys

from game.app import App


def _seed_from_args(argv):
    if "--seed" in argv:
        return int(argv[argv.index("--seed") + 1])
    return None


async def show_error(text):
    """Draw a traceback on screen and wait, so browser failures aren't a silent freeze."""
    import pygame

    print(text)
    surface = pygame.display.get_surface() or pygame.display.set_mode((960, 540))
    surface.fill((0, 0, 0))
    font = pygame.font.Font(None, 18)
    y = 8
    for line in ["CONTOUR COLONY CRASHED - please report this text:", ""] + text.splitlines():
        surface.blit(font.render(line, True, (255, 90, 80)), (8, y))
        y += 16
    pygame.display.flip()
    while True:
        pygame.event.pump()
        await asyncio.sleep(0.1)


async def main():
    try:
        if "--no-scale" in sys.argv:
            app = App(_seed_from_args(sys.argv), scaled=False)
        else:
            app = App(_seed_from_args(sys.argv))
        while app.running:
            app.frame()
            await asyncio.sleep(0)
    except Exception:
        import traceback

        await show_error(traceback.format_exc())


asyncio.run(main())
