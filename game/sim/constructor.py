"""Constructor brain: supply construction sites and assemble them. Never imports pygame.

Sites are served oldest first. For a site still missing materials, the
constructor loads what it needs (up to its cargo) at the nearest storage that
has any, drives it over and delivers. Once everything is on site, it stays
and assembles. Materials it carries count as `incoming` on the site, so two
constructors never bring the same items.
"""

from game.sim import structures as ST
from game.sim import units as UN


def _sites(world):
    return sorted((s for s in world.structures.values() if not s.built), key=lambda s: (s.created_tick, s.id))


def _storage_with(world, unit, wanted, f):
    """Nearest storage holding any of the wanted items."""
    grid = world.grid
    best = None
    for s in world.structures.values():
        if not s.stores() or not any(s.storage.get(k, 0) for k in wanted):
            continue
        d = f.dist[grid.node_at(s.x, s.y)]
        if best is None or d < best[0]:
            best = (d, s)
    return best


def _deliver_cargo_to(world, unit, f):
    """A site that needs something the unit already carries."""
    for site in _sites(world):
        need = site.materials_needed()
        if any(unit.cargo.get(k, 0) for k in need):
            d = f.dist[world.grid.node_at(site.x, site.y)]
            if UN.can_afford(world, unit, d + UN.back_cost(world, site.x, site.y)):
                return site
    return None


def _reserve_cargo(site, unit):
    need = site.materials_needed()
    for k, n in unit.cargo.items():
        take = min(n, need.get(k, 0))
        if take:
            site.incoming[k] = site.incoming.get(k, 0) + take


def think(world, unit):
    if UN.try_charge(world, unit):
        return
    roles = UN.dock_roles(world, unit)
    if unit.battery < UN.reserve(world, unit) and "charge" not in roles:
        if UN.go_dock(world, unit, "charge"):
            return
    f = UN.here_field(world, unit)
    grid = world.grid

    if unit.cargo_total():
        site = _deliver_cargo_to(world, unit, f)
        if site is not None:
            _reserve_cargo(site, unit)
            unit.job = site.id
            UN.release_dock(world, unit)
            UN.set_path(unit, UN.path_to(world, unit, (site.x, site.y), f), "to_site", site.id)
            return
        if "store" in roles:
            UN.work(unit, "unload", unit.spec["load_s"])
            return
        if UN.go_dock(world, unit, "store"):
            return

    for site in _sites(world):
        site_node = grid.node_at(site.x, site.y)
        back = UN.back_cost(world, site.x, site.y)
        need = site.materials_needed()
        if need:
            found = _storage_with(world, unit, need, f)
            if found is None:
                continue
            d_store, store = found
            leg = grid.field(grid.node_at(store.x, store.y)).dist[site_node]
            if not UN.can_afford(world, unit, d_store + leg + back):
                continue
            unit.job = site.id
            UN.release_dock(world, unit)
            UN.set_path(unit, UN.path_to(world, unit, (store.x, store.y), f), "to_storage", store.id)
            return
        if site.fully_delivered():
            remaining = site.spec["build_time_s"] - site.work_done_s
            energy = remaining / unit.spec["build_rate"] * unit.spec["build_drain_per_s"]
            if not UN.can_afford(world, unit, f.dist[site_node] + back, energy):
                continue
            unit.job = site.id
            UN.release_dock(world, unit)
            UN.set_path(unit, UN.path_to(world, unit, (site.x, site.y), f), "to_site", site.id)
            return
    for s in sorted((s for s in world.structures.values() if s.built and s.deconstruct), key=lambda s: s.id):
        if any(u.job == s.id and u is not unit for u in world.units.values()):
            continue  # one constructor per teardown
        remaining = s.spec["build_time_s"] * ST.S.DECONSTRUCT_TIME_FRACTION - s.teardown_s
        energy = remaining / unit.spec["build_rate"] * unit.spec["build_drain_per_s"]
        if not UN.can_afford(world, unit, f.dist[grid.node_at(s.x, s.y)] + UN.back_cost(world, s.x, s.y), energy):
            continue
        unit.job = s.id
        UN.release_dock(world, unit)
        goal = (s.x + s.spec["footprint_cells"] + 0.5, s.y)
        UN.set_path(unit, UN.path_to(world, unit, goal, f) or [goal], "to_teardown", s.id)
        return
    unit.job = None
    UN.head_home(world, unit)


def arrived(world, unit):
    if unit.activity == "to_teardown":
        s = world.structures.get(unit.target)
        if s is None or not s.deconstruct:
            unit.target = unit.job = None
            think(world, unit)
        else:
            UN.work(unit, "dismantling", 1.0)
        return
    if unit.activity == "to_storage":
        UN.work(unit, "load", unit.spec["load_s"])
    elif unit.activity == "to_site":
        site = world.structures.get(unit.target)
        if site is None or site.built:
            unit.target = unit.job = None
            think(world, unit)
            return
        for k, n in list(unit.cargo.items()):
            site.incoming[k] = max(0, site.incoming.get(k, 0) - n)
            take = min(n, site.spec["build_cost"].get(k, 0) - site.delivered.get(k, 0))
            if take > 0:
                site.delivered[k] = site.delivered.get(k, 0) + take
                unit.cargo[k] -= take
                if not unit.cargo[k]:
                    del unit.cargo[k]
        if site.fully_delivered():
            UN.work(unit, "building", 1.0)
        else:
            think(world, unit)


def work_tick(world, unit):
    if unit.activity == "dismantling":
        s = world.structures.get(unit.target)
        if s is None or not s.deconstruct:
            unit.timer = 0
            return
        unit.timer = 1
        dt = 1.0 / world.tick_rate
        s.teardown_s += dt * unit.spec["build_rate"]
        unit.battery = max(0.0, unit.battery - dt * unit.spec["build_drain_per_s"])
        if s.teardown_progress() >= 1.0:
            ST.dismantle(world, s)
            unit.timer = 0
        elif unit.battery < UN.reserve(world, unit):
            unit.timer = 0
        return
    if unit.activity != "building":
        return
    site = world.structures.get(unit.target)
    if site is None or site.built:
        unit.timer = 0
        return
    unit.timer = 1  # keep working until the site is done
    dt = 1.0 / world.tick_rate
    site.work_done_s += dt * unit.spec["build_rate"]
    unit.battery = max(0.0, unit.battery - dt * unit.spec["build_drain_per_s"])
    if site.work_done_s >= site.spec["build_time_s"]:
        ST.complete(world, site)
        unit.timer = 0
    elif unit.battery < UN.reserve(world, unit):
        unit.timer = 0


def work_done(world, unit):
    if unit.activity == "load":
        store = world.structures.get(unit.target)
        site = world.structures.get(unit.job)
        if store is not None and site is not None and not site.built:
            space = unit.spec["cargo"] - unit.cargo_total()
            for k, n in site.materials_needed().items():
                take = min(n, store.storage.get(k, 0), space)
                if take > 0:
                    store.storage[k] -= take
                    if not store.storage[k]:
                        del store.storage[k]
                    unit.cargo[k] = unit.cargo.get(k, 0) + take
                    site.incoming[k] = site.incoming.get(k, 0) + take
                    space -= take
            if unit.cargo_total():
                UN.set_path(unit, UN.path_to(world, unit, (site.x, site.y)), "to_site", site.id)
                return
        think(world, unit)
    elif unit.activity == "unload":
        s = world.structures[unit.dock]
        for k in list(unit.cargo):
            moved = world.store(s, k, unit.cargo[k])
            unit.cargo[k] -= moved
            if not unit.cargo[k]:
                del unit.cargo[k]
        if unit.cargo_total():
            UN.work(unit, "unload", unit.spec["load_s"])
        else:
            think(world, unit)
    else:  # building finished or interrupted
        unit.target = unit.job = None
        think(world, unit)


def drop_job(world, unit):
    site = world.structures.get(unit.job) if unit.job is not None else None
    if site is not None and not site.built:
        for k, n in unit.cargo.items():
            site.incoming[k] = max(0, site.incoming.get(k, 0) - n)
    unit.target = unit.job = None
    unit.path = []
