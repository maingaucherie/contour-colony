"""The mass driver: the site's goal. Never imports pygame.

Built once like any structure, then completed phase by phase. Each phase is a
bill of goods (spec "phases"), delivered into the driver's input buffer by
haulers and conveyors like any other consumer. When the whole bill is in, the
goods are used up, the phase is done and the next tier of research opens
(research.phase). After the last bill the driver charges: it draws launch_kw
for launch_charge_s while its grid can carry it, then fires, and the site is
won.

After that it ships: whatever exports haulers bring it (spec "ships") go up
the rails ship_batch at a time every ship_every_s while it has ship_kw, each
paying ship_price_mult times its market price. A site kept running after the
win has this to grow: the number shipped.
"""

from game.content import world as W

KIND = "mass_driver"
BUILDING, CHARGING, FIRED = "building phase", "charging", "fired"


def phases(s):
    return s.spec["phases"]


def current(s):
    """The phase being delivered, or None once every bill is in."""
    p = phases(s)
    return p[s.phase] if s.phase < len(p) else None


def shipping(s):
    return s.status == FIRED


def needs(s):
    """{item: still to deliver} for the current phase (once it ships: room
    in its hold for each export)."""
    ph = current(s)
    if shipping(s):
        held = sum(s.inputs.values())
        return {k: s.spec["ship_hold"] - held for k in s.spec["ships"] if held < s.spec["ship_hold"]}
    if ph is None:
        return {}
    return {k: n - s.inputs.get(k, 0) for k, n in ph["needs"].items() if n - s.inputs.get(k, 0) > 0}


def room(s, item):
    """How many more of item it takes now (counting what haulers are bringing)."""
    return max(0, needs(s).get(item, 0) - s.reserved_in.get(item, 0))


def wants(kind):
    """Every item any phase of a building of this kind needs, or it ships (for conveyor planning)."""
    from game.content.structures import STRUCTURES
    spec = STRUCTURES[kind]
    return {k for ph in spec.get("phases", ()) for k in ph["needs"]} | set(spec.get("ships", ()))


def progress(s):
    """0..1 through the current phase's bill (or the launch charge)."""
    ph = current(s)
    if ph is None:
        return min(1.0, s.charge_s / s.spec["launch_charge_s"])
    total = sum(ph["needs"].values())
    return sum(min(s.inputs.get(k, 0), n) for k, n in ph["needs"].items()) / total


def find(world):
    return next((s for s in world.structures.values() if s.kind == KIND), None)


def goal_text(world):
    """One line on how the goal is going, for the HUD."""
    s = find(world)
    if s is None:
        return "GOAL: BUILD THE MASS DRIVER (B)"
    if not s.built:
        return f"GOAL: MASS DRIVER UNDER CONSTRUCTION {s.build_progress() * 100:3.0f}%"
    ph = current(s)
    total = len(phases(s))
    if ph is not None:
        return f"MASS DRIVER PHASE {s.phase + 1}/{total} {ph['name'].upper()} {progress(s) * 100:3.0f}%"
    if s.status == FIRED:
        return f"MASS DRIVER SHIPPING: {world.shipped} SENT TO ORBIT" + ("" if s.powered else
                                                                         f" - NEEDS {s.spec['ship_kw']:.0f} KW")
    return f"MASS DRIVER CHARGING {progress(s) * 100:3.0f}%" + ("" if s.powered else
                                                                f" - NEEDS {s.spec['launch_kw']:.0f} KW")


def receive(s, item, amount):
    """Take up to amount of item into the current phase. Returns how many."""
    put = min(amount, needs(s).get(item, 0))
    if put > 0:
        s.inputs[item] = s.inputs.get(item, 0) + put
    return max(0, put)


def update(world, s):
    if not s.built:
        return
    ph = current(s)
    if ph is not None:
        s.status = BUILDING
        if needs(s):
            return
        for k, n in ph["needs"].items():
            s.inputs[k] -= n
            if not s.inputs[k]:
                del s.inputs[k]
            world.consumed[k] = world.consumed.get(k, 0) + n
        s.phase += 1
        world.research.phase = max(world.research.phase, s.phase)
        if current(s) is None:
            s.status = CHARGING
            world.dirty_power = True
            world.event(f"MASS DRIVER PHASE {s.phase} COMPLETE: {ph['name'].upper()} - "
                        f"CHARGING NEEDS {s.spec['launch_kw']:.0f} KW", "won")
        else:
            world.event(f"MASS DRIVER PHASE {s.phase} COMPLETE: {ph['name'].upper()} - NEW RESEARCH OPEN", "won")
        return
    if s.status == FIRED:
        _ship(world, s)
        return
    s.status = CHARGING
    if s.powered:
        s.charge_s += 1.0 / W.TICK_RATE
        if s.charge_s >= s.spec["launch_charge_s"]:
            s.status = FIRED
            world.dirty_power = True
            world.finish("won", "MASS DRIVER FIRED: FIRST CARGO TO ORBIT")


def _ship(world, s):
    """Every ship_every_s, launch up to ship_batch of what is in the hold."""
    every = max(1, round(s.spec["ship_every_s"] * W.TICK_RATE))
    if not s.powered or not s.inputs or world.tick_count - s.last_launch < every:
        return
    left = s.spec["ship_batch"]
    for item in sorted(s.inputs, key=lambda k: -s.inputs[k]):
        n = min(left, s.inputs[item])
        s.inputs[item] -= n
        if not s.inputs[item]:
            del s.inputs[item]
        world.consumed[item] = world.consumed.get(item, 0) + n
        world.credits += int(n * world.price(item) * s.spec["ship_price_mult"])
        world.shipped += n
        left -= n
        if not left:
            break
    s.last_launch = world.tick_count
