"""Scavenger brain: collect surface debris and bring it home. Never imports pygame.

Pick the nearest unclaimed debris it can reach and still get to a charger
from with battery to spare, drive there, pick it up, repeat until the cargo
is full or nothing is in range, then unload at the nearest storage and top
up at a charger.
"""

import math

from game.content import units as U
from game.sim import units as UN


def _choose_debris(world, unit):
    f = UN.here_field(world, unit)
    grid = world.grid
    best = None
    for piece in world.debris.values():
        if piece.claimed_by is not None or not piece.seen:
            continue
        node = grid.node_at(piece.x, piece.y)
        travel = f.dist[node]
        if not UN.can_afford(world, unit, travel + world.charge_field.dist[node], unit.spec["pickup_energy"]):
            continue
        if best is None or travel < best[0]:
            best = (travel, piece)
    if best is None:
        return None
    piece = best[1]
    return piece, UN.path_to(world, unit, (piece.x, piece.y), f)


def think(world, unit):
    roles = UN.dock_roles(world, unit)
    if unit.cargo_total() and "store" in roles:
        UN.work(unit, "unload", unit.spec["unload_s"])
        return
    if UN.try_charge(world, unit):
        return
    if unit.battery < UN.reserve(world, unit) and "charge" not in roles:
        if UN.go_dock(world, unit, "charge"):
            return
    if unit.cargo_total() < unit.spec["cargo"]:
        choice = _choose_debris(world, unit)
        if choice is not None:
            piece, path = choice
            piece.claimed_by = unit.id
            UN.release_dock(world, unit)
            UN.set_path(unit, path, "to_debris", piece.id)
            return
    if unit.cargo_total() and UN.go_dock(world, unit, "store"):
        return
    if unit.cargo_total() < unit.spec["cargo"] and _search(world, unit):
        return
    UN.head_home(world, unit)


def _search(world, unit):
    """Nothing known in range: drive somewhere random nearby and look around."""
    f = UN.here_field(world, unit)
    grid, rng = world.grid, world.rng
    for _ in range(U.SEARCH_ATTEMPTS):
        a = rng.uniform(0.0, 2 * math.pi)
        d = rng.uniform(*U.SEARCH_DISTANCE_CELLS)
        x, y = unit.x + d * math.cos(a), unit.y + d * math.sin(a)
        size = world.heightmap.size
        if not (1 <= x < size - 1 and 1 <= y < size - 1):
            continue
        node = grid.node_at(x, y)
        if not grid.open[node] or not f.reachable(node):
            continue
        if not UN.can_afford(world, unit, f.dist[node] + world.charge_field.dist[node], unit.spec["pickup_energy"]):
            continue
        UN.release_dock(world, unit)
        UN.set_path(unit, UN.path_to(world, unit, (x, y), f), "searching")
        return True
    return False


def arrived(world, unit):
    if unit.activity == "searching":
        think(world, unit)
    else:
        UN.work(unit, "pickup", unit.spec["pickup_s"])


def work_done(world, unit):
    if unit.activity == "pickup":
        piece = world.debris.pop(unit.target, None)
        unit.target = None
        if piece is not None:
            unit.cargo["scrap"] = unit.cargo.get("scrap", 0) + piece.value
            unit.collected += piece.value
            world.scrap_collected += piece.value
            unit.battery = max(0.0, unit.battery - unit.spec["pickup_energy"])
        think(world, unit)
    elif unit.activity == "unload":
        s = world.structures[unit.dock]
        world.unload_scrap(s, unit.cargo.pop("scrap", 0))  # what doesn't fit is sold
        think(world, unit)


def drop_job(world, unit):
    if unit.activity in ("to_debris", "pickup") and unit.target is not None:
        piece = world.debris.get(unit.target)
        if piece is not None and piece.claimed_by == unit.id:
            piece.claimed_by = None
    unit.target = None
    unit.path = []
