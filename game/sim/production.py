"""Recipe cycles, buffers and backpressure. Never imports pygame.

A cycle starts when every input is in the buffer, there is room for every
output, and the structure is powered; inputs are consumed at the start and
outputs appear when it finishes. A full output buffer stops the structure
(blocked); a missing input starves it.
"""

from game.content import structures as S
from game.content import world as W
from game.content.items import ITEMS

WORKING, STARVED, BLOCKED, UNPOWERED, IDLE = "working", "starved", "blocked", "unpowered", "idle"


def recipe(s):
    return s.spec.get("recipe")


def input_cap(s, item):
    r = recipe(s)
    if not r or item not in r["in"]:
        return 0
    return max(r["in"][item] * S.INPUT_BUFFER_CYCLES, S.INPUT_BUFFER_MIN)


def output_cap(s, item):
    return S.OUTPUT_BUFFER


def cycle_time(s):
    r = recipe(s)
    return r["time_s"] / max(0.1, s.richness)


def update(world, s):
    r = recipe(s)
    if r is None or not s.built:
        return
    dt = 1.0 / W.TICK_RATE
    if s.cycle_left_s > 0.0:
        if not s.powered:
            s.status = UNPOWERED
            return
        s.status = WORKING
        s.cycle_left_s -= dt
        if s.cycle_left_s <= 0.0:
            s.cycle_left_s = 0.0
            for item, n in r["out"].items():
                world.produced[item] = world.produced.get(item, 0) + n
                keep = min(n, output_cap(s, item) - s.outputs.get(item, 0))
                s.outputs[item] = s.outputs.get(item, 0) + keep
                if n > keep:  # a gas with nowhere to go is vented
                    world.consumed[item] = world.consumed.get(item, 0) + n - keep
                    s.vented += n - keep
            s.cycles += 1
        return
    if any(s.inputs.get(item, 0) < n for item, n in r["in"].items()):
        s.status = STARVED
        return
    if any(s.outputs.get(item, 0) + n > output_cap(s, item) and not ITEMS[item].get("vents")
           for item, n in r["out"].items()):
        s.status = BLOCKED
        return
    if not s.powered:
        s.status = UNPOWERED
        return
    for item, n in r["in"].items():
        s.inputs[item] -= n
        world.consumed[item] = world.consumed.get(item, 0) + n
    s.cycle_left_s = cycle_time(s)
    s.status = WORKING


def progress(s):
    if s.cycle_left_s <= 0.0:
        return 0.0
    return 1.0 - s.cycle_left_s / cycle_time(s)
