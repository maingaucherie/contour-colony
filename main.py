"""Contour Colony entry point. pygbag requires main.py at the root and an
async main loop that yields to the browser once per frame."""

import asyncio
import sys

from game.app import App


def _seed_from_args(argv):
    if "--seed" in argv:
        return int(argv[argv.index("--seed") + 1])
    return None


async def main():
    app = App(_seed_from_args(sys.argv))
    while app.running:
        app.frame()
        await asyncio.sleep(0)


asyncio.run(main())
