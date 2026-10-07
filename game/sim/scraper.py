"""Scraper brain: sweep a zone for regolith in long passes. Never imports pygame.

A scraper works the area around its zone centre (where it was built, or where
the player last sent it). It drives to the start of the next pass, lowers its
blade and drives the pass at reduced speed, gathering one regolith every
cells_per_load cells. Passes run east-west, lane_spacing apart, from one
side of the zone to the other, each in the opposite direction to the last,
like the harvesters in the film Moon. A full load goes
to the nearest storage. Lumpy ground it scrapes often enough is levelled
(World.scrape). When colony storage holds all the regolith it may, scrapers
wait.

Helium harvesters use this brain too. They process the regolith on board and
keep only what their spec `gathers` (helium-3), one per cells_per_load cells
scraped, times the yield of the zone they are scraping (yield_by_zone).
"""

import math

from game.sim import geology as G
from game.sim import units as UN


def gathers(unit):
    """The item this unit's blade collects."""
    return unit.spec.get("gathers", "regolith")


def _lanes(unit):
    """Lane offsets (in lanes from the middle), in the order they are swept:
    side to side, so each pass starts beside where the last one ended."""
    n = int(unit.spec["zone_radius_cells"] / unit.spec["lane_spacing_cells"])
    return list(range(-n, n + 1))


def _blocked_by_structure(world, x, y):
    for s in world.structures.values():
        if not s.is_line() and math.hypot(s.x - x, s.y - y) <= s.spec["footprint_cells"] + 0.6:
            return True
    return False


def lane_segment(world, unit, k, reverse):
    """(start, end) of the longest clear stretch of pass k, or None."""
    cx, cy = unit.zone
    spec = unit.spec
    r = spec["zone_radius_cells"]
    dy = k * spec["lane_spacing_cells"]
    y = cy + dy
    size = world.heightmap.size
    if not 1 <= y <= size - 2:
        return None
    half = math.sqrt(max(0.0, r * r - dy * dy))
    x0, x1 = max(1.0, cx - half), min(size - 2.0, cx + half)
    grid, home = world.grid, world.home_field
    best, run = None, None
    steps = int(x1 - x0)
    for i in range(steps + 1):
        x = x0 + i
        node = grid.node_at(x, y)
        clear = grid.open[node] and home.reachable(node) and not _blocked_by_structure(world, x, y)
        if clear and run is None:
            run = x
        if run is not None and (not clear or i == steps):
            end = x if clear else x - 1
            if best is None or end - run > best[1] - best[0]:
                best = (run, end)
            run = None
    if best is None or best[1] - best[0] < spec["min_lane_cells"]:
        return None
    a, b = (best[0], y), (best[1], y)
    return (b, a) if reverse else (a, b)


def _room_at(world, s, item):
    return s is not None and s.accepts(item) and s.stored() < s.spec["storage"]


def think(world, unit):
    roles = UN.dock_roles(world, unit)
    room = world.storage_room(gathers(unit)) > 0
    if unit.cargo_total() and "store" in roles and room and _room_at(world, world.structures.get(unit.dock),
                                                                     gathers(unit)):
        UN.work(unit, "unload", unit.spec["unload_s"])
        return
    if UN.try_charge(world, unit):
        return
    if unit.battery < UN.reserve(world, unit) and "charge" not in roles:
        if UN.go_dock(world, unit, "charge"):
            return
    full = unit.cargo_total() >= unit.spec["cargo"]
    if full or not room:
        # Nothing more to scoop for now: drop off what it has, then wait.
        if unit.cargo_total() and room and _go_unload(world, unit):
            return
        UN.head_home(world, unit)
        return
    if unit.zone is None:
        unit.zone = (unit.x, unit.y)
    if _start_pass(world, unit):
        return
    if unit.cargo_total() and _go_unload(world, unit):
        return
    UN.head_home(world, unit)  # nothing it can reach to scrape


def _go_unload(world, unit):
    """Head for the nearest storage with room (go_dock skips full ones)."""
    return UN.go_dock(world, unit, "store")


def _start_pass(world, unit):
    """Head for the start of the next pass it can reach and afford."""
    lanes = _lanes(unit)
    f = UN.here_field(world, unit)
    grid = world.grid
    for _ in range(len(lanes)):
        i = unit.lane % len(lanes)
        unit.lane = i + 1
        seg = lane_segment(world, unit, lanes[i], i % 2 == 1)
        if seg is None:
            continue
        start, end = seg
        node = grid.node_at(*start)
        if not f.reachable(node):
            continue
        # The blade halves the speed, so a pass costs about twice its length.
        length = math.hypot(end[0] - start[0], end[1] - start[1]) / unit.spec["scrape_speed_fraction"]
        if not UN.can_afford(world, unit, f.dist[node] + length + UN.back_cost(world, *end)):
            continue
        unit.pass_end = end
        UN.release_dock(world, unit)
        UN.set_path(unit, UN.path_to(world, unit, start, f) or [start], "to_pass")
        return True
    return False


def arrived(world, unit):
    if unit.activity == "to_pass" and unit.pass_end is not None:
        UN.set_path(unit, [unit.pass_end], "scraping")
        unit.blade_odo = 0.0
        return
    think(world, unit)


def on_move(world, unit):
    if unit.activity != "scraping":
        return
    spec = unit.spec
    item = gathers(unit)
    gain = unit.odometer - unit.blade_odo
    if "yield_by_zone" in spec:
        gain *= spec["yield_by_zone"][G.zone_at(world.heightmap.geology, unit.x, unit.y)]
    unit.scraped += gain
    unit.blade_odo = unit.odometer
    while unit.scraped >= spec["cells_per_load"] and unit.cargo_total() < spec["cargo"]:
        unit.scraped -= spec["cells_per_load"]
        unit.cargo[item] = unit.cargo.get(item, 0) + 1
        world.produced[item] = world.produced.get(item, 0) + 1
    size = world.heightmap.size
    cell = min(max(int(unit.y + 0.5), 0), size - 1) * size + min(max(int(unit.x + 0.5), 0), size - 1)
    if cell != unit.blade_cell:
        unit.blade_cell = cell
        world.scrape(cell)
    if unit.cargo_total() >= spec["cargo"]:
        unit.path = []   # full: the pass ends here (think() runs on arrival)
        unit.pass_end = None


def work_done(world, unit):
    if unit.activity == "unload":
        s = world.structures.get(unit.dock)
        item = gathers(unit)
        if s is not None and item in unit.cargo:
            n = min(unit.cargo[item], world.storage_room(item))
            put = world.store(s, item, n)
            unit.cargo[item] -= put
            if not unit.cargo[item]:
                del unit.cargo[item]
        think(world, unit)


def drop_job(world, unit):
    unit.path = []
    unit.pass_end = None
