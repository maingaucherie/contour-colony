"""Production history for the production panel and the HUD. Never imports pygame.

Every HISTORY_SAMPLE_S the world notes how much of each item has been made so
far (World.history). Rates are differences between samples, per minute.
"""

from game.content import world as W
from game.content.items import ITEMS


def made(world):
    """{item: made so far}: what production made, plus scrap scavengers picked up."""
    counts = dict(world.produced)
    if world.scrap_collected:
        counts["scrap"] = counts.get("scrap", 0) + world.scrap_collected
    return counts


def sample(world):
    world.history.append((world.time_s(), made(world)))


def series(world, item):
    """Items per minute in each interval between samples, oldest first."""
    h = world.history
    out = []
    for (t0, a), (t1, b) in zip(h, h[1:]):
        out.append((b.get(item, 0) - a.get(item, 0)) * 60.0 / max(1e-6, t1 - t0))
    return out


def rate_now(world, item):
    """Items per minute over the last RATE_NOW_S (or as much history as there is)."""
    h = world.history
    if not h:
        return 0.0
    now = world.time_s()
    then_t, then = h[0]
    for t, counts in reversed(h):
        if now - t >= W.RATE_NOW_S:
            then_t, then = t, counts
            break
    span = now - then_t
    if span <= 0:
        return 0.0
    return (made(world).get(item, 0) - then.get(item, 0)) * 60.0 / span


def made_items(world):
    """Items the colony has made at all, in the item table's order."""
    counts = made(world)
    return [k for k in ITEMS if counts.get(k, 0) > 0]


def colony_output(world):
    """Everything made per minute right now, gathered goods included."""
    return sum(rate_now(world, k) for k in made_items(world) if ITEMS[k]["tier"] != "waste")
