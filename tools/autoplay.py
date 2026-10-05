"""Headless autoplayer: plays a site with a simple build order, for balance
runs and the Milestone 4 exit test (a site can be won, and lost).

    python tools/autoplay.py --seed 3 [--minutes 70] [--neglect] [--quiet] [--mode pressure]

The bot only uses the same commands the UI does (place, research, order unit,
order supply, sell scrap, orbital scan), once per simulated second.
"""

import argparse
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.content import contracts as CT  # noqa: E402
from game.content import world as W  # noqa: E402
from game.content.structures import STRUCTURES  # noqa: E402
from game.sim import structures as ST  # noqa: E402
from game.sim.terrain import generate_terrain, run_to_completion  # noqa: E402
from game.sim.world import build_world  # noqa: E402

RESEARCH_ORDER = ("field_survey", "logistics_1", "extraction", "sintering", "electrolysis", "reduction")
FACTORY = ("crusher", "ice_melter", "sinter_kiln", "electrolyzer", "reduction_furnace", "machine_shop")
# (unit, how many, structure that must exist first)
UNIT_GOALS = (("survey_rover", 1, None), ("hauler", 2, None), ("scavenger", 3, None), ("hauler", 3, "crusher"),
              ("constructor", 2, "sinter_kiln"), ("hauler", 4, "electrolyzer"), ("hauler", 5, "reduction_furnace"))
UNIT_PARTS_RESERVE = 4     # keep this many parts spare after ordering a unit
POWER_MARGIN_KW = 2.0
OUTPOST_RANGE = 70.0       # flagged fields further than this (cost-cells) get a charging pad on the way
OUTPOST_STEP = 55.0


def supply_index(name):
    return next(i for i, e in enumerate(CT.SUPPLY) if e["name"] == name)


class Bot:
    def __init__(self, world, log=None):
        self.w = world
        self.log = log or (lambda text: None)
        self.last_scan_pass = -1

    # Helpers ----------------------------------------------------------------------

    def count(self, kind, built_only=False):
        return sum(1 for s in self.w.structures.values() if s.kind == kind and (s.built or not built_only))

    def units(self, kind):
        return sum(1 for u in self.w.units.values() if u.kind == kind)

    def queued(self, kind):
        return sum(s.queue.count(kind) + (s.building_unit == kind)
                   for s in self.w.structures.values() if s.kind == "rover_bay")

    def spot(self, kind, near, rmin=3.0, rmax=24.0, ok=None):
        r = rmin
        while r <= rmax:
            for a in range(0, 360, 12):
                x = near[0] + r * math.cos(math.radians(a))
                y = near[1] + r * math.sin(math.radians(a))
                if ST.check_placement(self.w, kind, x, y)[0] and (ok is None or ok(x, y)):
                    return x, y
            r += 0.75
        return None

    def nodes(self):
        return [s for s in self.w.structures.values() if s.spec.get("grid_reach_cells", 0) > 0]

    def powered_spot(self, x, y):
        return any(math.hypot(n.x - x, n.y - y) <= n.spec["grid_reach_cells"] for n in self.nodes())

    def place(self, kind, at):
        s, reason = self.w.place(kind, *at)
        if s is not None:
            self.log(f"place {kind} at ({at[0]:.0f},{at[1]:.0f})")
        return s

    def connect(self, x, y):
        """Plan pylons from the nearest grid node toward (x, y) until it's covered."""
        for _ in range(20):
            if self.powered_spot(x, y):
                return True
            n = min(self.nodes(), key=lambda n: math.hypot(n.x - x, n.y - y))
            d = math.hypot(x - n.x, y - n.y)
            step = min(W.PATH_NODE_CELLS * 2.0, d)
            reach = STRUCTURES["pylon"]["grid_reach_cells"]
            tx, ty = n.x + (x - n.x) * step / d, n.y + (y - n.y) * step / d
            at = self.spot("pylon", (tx, ty), 0.0, 4.0,
                           ok=lambda px, py: math.hypot(px - n.x, py - n.y) <= max(reach, n.spec["grid_reach_cells"]))
            if at is None or self.place("pylon", at) is None:
                return False
        return self.powered_spot(x, y)

    def grid_balance(self):
        """Planned supply minus planned demand on the lander's grid (sites count)."""
        supply = demand = 0.0
        for s in self.w.structures.values():
            if s.kind == "solar":
                supply += s.spec["power_kw"] * self.w.illumination_at(s.x, s.y)
            else:
                supply += s.spec.get("power_kw", 0.0)
            demand += s.spec.get("draw_kw", 0.0)
        return supply - demand

    def missing(self):
        """Materials still owed to construction sites and queued bay orders, minus stock."""
        need = {}
        for s in self.w.structures.values():
            if not s.built:
                for k, n in s.materials_needed().items():
                    need[k] = need.get(k, 0) + n
        return {k: n - self.w.stock(k) for k, n in need.items() if n > self.w.stock(k)}

    # Decisions --------------------------------------------------------------------

    def research(self):
        w = self.w
        if w.research.current is not None:
            return
        for node in RESEARCH_ORDER:
            if node not in w.research.done:
                ok, _ = w.research.can_start(node, w.credits)
                if ok:
                    w.start_research(node)
                    self.log(f"research {node}")
                return

    def factory_site(self, kind):
        L = self.w.lander
        return self.spot(kind, (L.x, L.y), 4.0, 26.0, ok=lambda x, y: self.powered_spot(x, y))

    def build(self):
        w = self.w
        L = w.lander
        pending = sum(1 for s in w.structures.values() if not s.built)
        if pending >= 3:
            return
        if self.depot():
            return
        if self.grid_balance() < POWER_MARGIN_KW and w.unlocked("solar"):
            at = self.factory_site("solar")
            if at:
                self.place("solar", at)
                return
        if not self.count("scanner"):
            at = self.factory_site("scanner")
            if at:
                self.place("scanner", at)
                return
        if w.unlocked("rover_bay") and not self.count("rover_bay"):
            at = self.factory_site("rover_bay")
            if at:
                self.place("rover_bay", at)
                return
        for kind, field_kind in (("ilmenite_mine", "ilmenite"), ("ice_mine", "ice")):
            if w.unlocked(kind) and not self.count(kind):
                if self.mine(kind, field_kind) or self.outpost(field_kind):
                    return
        for kind in FACTORY:
            if w.unlocked(kind) and not self.count(kind):
                if kind == "ice_melter" and not self.count("ice_mine"):
                    continue
                at = self.factory_site(kind)
                if at is None:
                    # Grow the grid outward with a pylon and try again next time.
                    a = (w.tick_count // 10) % 8 * math.pi / 4
                    self.connect(L.x + 14 * math.cos(a), L.y + 14 * math.sin(a))
                    return
                self.place(kind, at)
                return

    def depot(self):
        w = self.w
        stored = sum(s.stored() for s in w.storages())
        capacity = sum(s.spec["storage"] for s in w.storages())
        if w.unlocked("depot") and stored > 0.7 * capacity and not any(s.kind == "depot" and not s.built
                                                                       for s in w.structures.values()):
            at = self.factory_site("depot")
            if at:
                return self.place("depot", at) is not None
        return False

    def outpost(self, field_kind):
        """Extend the charging network toward the nearest flagged field of a kind
        when it is beyond comfortable rover range. True if something was placed."""
        w = self.w
        if any(s.kind == "charging_pad" and not s.built for s in w.structures.values()):
            return False
        cf = w.charge_field
        flagged = [f for f in w.fields if f.kind == field_kind and f.hinted]
        if not flagged:
            return False
        f = min(flagged, key=lambda f: cf.dist[w.grid.node_at(f.cx, f.cy)])
        goal = w.grid.node_at(f.cx, f.cy)
        if cf.dist[goal] <= OUTPOST_RANGE or cf.dist[goal] == math.inf:
            return False
        chain = cf.nodes_from_source(goal)
        node = max((n for n in chain if cf.dist[n] <= OUTPOST_STEP), key=lambda n: cf.dist[n])
        at = self.spot("charging_pad", w.grid.node_centre(node), 0.0, 6.0)
        if at is None or self.place("charging_pad", at) is None:
            return False
        self.connect(*at)
        return True

    def mine(self, kind, field_kind):
        w = self.w
        L = w.lander
        best = None
        for f in w.fields:
            if f.kind != field_kind or not f.confirmed:
                continue
            for x, y in f.sample_points(1.0):
                if ST.check_placement(w, kind, x, y)[0]:
                    d = math.hypot(x - L.x, y - L.y)
                    if best is None or d < best[0]:
                        best = (d, (x, y))
        if best is None:
            return False
        at = best[1]
        if w.charge_field.dist[w.grid.node_at(*at)] > OUTPOST_RANGE:
            return self.outpost(field_kind)
        if self.place(kind, at) is None:
            return False
        self.connect(*at)
        return True

    def units_order(self):
        w = self.w
        bays = [s for s in w.structures.values() if s.kind == "rover_bay" and s.built]
        if not bays or bays[0].queue:
            return
        if self.missing():
            return  # construction first
        from game.content.units import UNITS
        for kind, goal, after in UNIT_GOALS:
            if not w.unlocked(kind) or (after and not self.count(after, built_only=True)):
                continue
            if self.units(kind) + self.queued(kind) < goal:
                if w.stock("parts") < UNITS[kind]["bay_cost"].get("parts", 0) + UNIT_PARTS_RESERVE:
                    return
                w.order_unit(bays[0].id, kind)
                self.log(f"order {kind}")
                return

    def supply(self):
        w = self.w
        if any(c.standing for c in w.contracts.open):
            return  # self-sufficiency is the point now
        need = self.missing()
        reserve = 0
        nxt = next((n for n in RESEARCH_ORDER if n not in w.research.done and n != w.research.current), None)
        from game.content.research import RESEARCH
        if nxt is not None:
            reserve = RESEARCH[nxt]["cost"]
        for item, crate in (("parts", "parts crate"), ("scrap", "scrap crate"), ("sinter", "sinter crate")):
            i = supply_index(crate)
            if need.get(item, 0) > 0 and w.credits >= CT.SUPPLY[i]["cost"] + reserve:
                if not any(e["name"] == crate for e in w.orbit.pending):
                    w.order_supply(i)
                    self.log(f"order {crate}")
                    return

    def scan(self):
        w = self.w
        now = w.time_s()
        if not w.orbit.overhead(now) or w.orbit.scan_used:
            return
        # Scan the least-surveyed ring sector around the lander.
        L = w.lander
        best = None
        for k in range(8):
            a = k * math.pi / 4
            for r in (40, 70):
                x, y = L.x + r * math.cos(a), L.y + r * math.sin(a)
                if 0 <= x < w.heightmap.size and 0 <= y < w.heightmap.size and w.survey.level_at(x, y) == 0:
                    best = best or (x, y)
        if best:
            w.orbital_scan(*best)

    def contracts(self):
        """Calm mode: take every offer while there's room (the bot isn't picky)."""
        for c in list(self.w.contracts.offers):
            if self.w.accept_contract(c.id)[0]:
                self.log(f"accept {c.qty} {c.good}")

    def step(self):
        self.contracts()
        self.research()
        self.build()
        self.units_order()
        self.supply()
        self.scan()


def make(seed, mode=CT.DEFAULT_MODE):
    hm = run_to_completion(generate_terrain(seed))
    return run_to_completion(build_world(seed, hm, mode))


def play(world, minutes, neglect=False, log=None, report_every_s=300):
    bot = Bot(world, log)
    step = W.TICK_RATE
    for t in range(int(minutes * 60 * W.TICK_RATE)):
        if not neglect and t % step == 0:
            bot.step()
        world.tick()
        if log and t % (report_every_s * W.TICK_RATE) == 0:
            log(status(world))
        if world.outcome is not None:
            break
    return world


def status(w):
    c = w.contracts
    items = {}
    for s in w.structures.values():
        for d in (s.storage, s.outputs):
            for k, n in d.items():
                items[k] = items.get(k, 0) + n
    built = sorted(s.kind for s in w.structures.values() if s.built and s.kind not in ("pylon", "solar"))
    return (f"t={w.time_s() / 60:5.1f}m cr={w.credits:5d} rep={c.reputation:5.1f} filled={c.filled} "
            f"expired={c.expired} open={[(o.good, o.delivered, o.qty) for o in c.open]} "
            f"units={sorted((k, sum(1 for u in w.units.values() if u.kind == k)) for k in {u.kind for u in w.units.values()})} "
            f"stock={dict(sorted(items.items()))} built={dict((k, built.count(k)) for k in set(built))} solar={sum(1 for s in w.structures.values() if s.kind == 'solar')}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--minutes", type=float, default=75)
    ap.add_argument("--neglect", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--mode", choices=sorted(CT.MODES), default=CT.DEFAULT_MODE)
    args = ap.parse_args()
    t0 = time.time()
    w = make(args.seed, args.mode)

    def log(text):
        if not args.quiet:
            print(f"[{w.time_s() / 60:5.1f}m] {text}")

    seen = [0]

    def log_events(text):
        log(text)

    play(w, args.minutes, args.neglect, log_events)
    for _, text, kind in list(w.events)[-6:]:
        print("  event:", text)
    print(status(w))
    print(f"outcome={w.outcome} at {w.end_s and w.end_s / 60:.1f} min score={w.score()} "
          f"(wall {time.time() - t0:.0f} s)" if w.outcome else f"no outcome (wall {time.time() - t0:.0f} s)")


if __name__ == "__main__":
    main()
