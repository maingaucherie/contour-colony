"""Recipe cycles, buffers and backpressure. Never imports pygame.

A cycle starts when every input is in the buffer, there is room for every
output, and the structure is powered; inputs are consumed at the start and
outputs appear when it finishes. A full output buffer stops the structure
(blocked); a missing input starves it.

How fast a cycle runs depends on the building (speed() below): mines on
their field's richness and remaining reserves, the kiln on sunlight, the
furnace on its heat, the melter on waste heat from a neighbour.
"""

import math

from game.content import structures as S
from game.content import world as W
from game.content.items import ITEMS
from game.sim import geology as G
from game.sim import wear

WORKING, STARVED, BLOCKED, UNPOWERED, IDLE, BROKEN = "working", "starved", "blocked", "unpowered", "idle", "broken"


def recipe(s):
    return s.spec.get("recipe")


def input_cap(s, item):
    r = recipe(s)
    if not r or item not in r["in"]:
        return 0
    return max(r["in"][item] * S.INPUT_BUFFER_CYCLES, S.INPUT_BUFFER_MIN)


def output_cap(s, item):
    return S.OUTPUT_BUFFER


def field_of(world, s):
    if s.field_id is None:
        return None
    return next((f for f in world.fields if f.id == s.field_id), None)


def _waste_heat_source(world, s, spec):
    for o in world.structures.values():
        if (o.kind in spec["from"] and o.built and o.status == WORKING
                and math.hypot(o.x - s.x, o.y - s.y) <= s.spec["footprint_cells"] + o.spec["footprint_cells"]
                + spec["gap_cells"]):
            return o
    return None


def speed(world, s):
    """Recipe speed multiplier for this building, here and now."""
    spec = s.spec
    k = 1.0
    if spec.get("requires_field"):
        f = field_of(world, s)
        k *= f.yield_factor() if f else s.richness
    if "sun_speed" in spec:
        lo, hi = spec["sun_speed"]
        dark, bright = W.ILLUMINATION_RANGE
        light = (world.illumination_at(s.x, s.y) - dark) / (bright - dark)
        k *= lo + (hi - lo) * max(0.0, min(1.0, light))
    if "heat" in spec:
        k *= max(spec["heat"]["cold_speed"], s.heat)
    if "waste_heat" in spec and s.warm:
        k *= spec["waste_heat"]["speed"]
    return max(0.05, k * s.clock * wear.speed_factor(s))


def cycle_time(world, s):
    """Seconds per cycle at the current speed."""
    return recipe(s)["time_s"] / speed(world, s)


def update(world, s):
    r = recipe(s)
    if r is None or not s.built:
        return
    dt = 1.0 / W.TICK_RATE
    _update_heat(world, s, dt)
    if wear.broken(world, s):
        s.status = BROKEN
        return
    if s.cycle_left_s > 0.0:
        if not s.powered:
            s.status = UNPOWERED
            return
        s.status = WORKING
        s.cycle_left_s -= dt * speed(world, s)    # cycle_left_s counts base recipe seconds
        if s.cycle_left_s <= 0.0:
            s.cycle_left_s = 0.0
            for item, n in cycle_outputs(world, s, r).items():
                world.produced[item] = world.produced.get(item, 0) + n
                keep = min(n, output_cap(s, item) - s.outputs.get(item, 0))
                s.outputs[item] = s.outputs.get(item, 0) + keep
                if n > keep:  # a gas with nowhere to go is vented
                    world.consumed[item] = world.consumed.get(item, 0) + n - keep
                    s.vented += n - keep
            s.cycles += 1
            wear.add_wear(world, s)
            f = field_of(world, s)
            if f is not None:
                f.mined += 1
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
    s.cycle_left_s = r["time_s"]
    s.status = WORKING


def cycle_outputs(world, s, r):
    """What one finished cycle makes: the whole recipe, or for a sorter one
    output picked with the weights of the ground it stands on."""
    if not s.spec.get("picks_one"):
        chance = s.spec.get("chance")
        if not chance:
            return r["out"]
        return {k: n for k, n in r["out"].items() if k not in chance or world.rng.random() < chance[k]}
    weights = s.spec["sorts"][G.zone_at(world.heightmap.geology, s.x, s.y)]
    roll = world.rng.random() * sum(weights.values())
    for item, w in weights.items():
        roll -= w
        if roll < 0:
            return {item: r["out"][item]}
    return {item: r["out"][item]}


def _update_heat(world, s, dt):
    spec = s.spec
    if "heat" in spec:
        h = spec["heat"]
        if s.status == WORKING and s.powered:
            s.heat = min(1.0, s.heat + dt / h["warm_up_s"])
        else:
            s.heat = max(0.0, s.heat - dt / h["cool_s"])
    if "waste_heat" in spec and world.tick_count % W.TICK_RATE == 0:  # neighbours change slowly: once a second
        s.warm = _waste_heat_source(world, s, spec["waste_heat"]) is not None


def progress(s):
    if s.cycle_left_s <= 0.0:
        return 0.0
    return 1.0 - s.cycle_left_s / recipe(s)["time_s"]
