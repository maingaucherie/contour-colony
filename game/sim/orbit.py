"""Orbital passes, supply drops and orbital scans. Never imports pygame.

The ship is overhead for PASS_DURATION_S of every PASS_PERIOD_S. Drops can be
ordered any time but only land during a pass. Each pass allows one free
orbital scan, which surveys a region (level 1) and flags fields in it.
"""

import math
from dataclasses import dataclass

from game.content import contracts as C
from game.content import units as U


@dataclass(slots=True)
class Pod:
    item: dict          # supply catalogue entry
    land_s: float
    x: float
    y: float


class Orbit:
    def __init__(self):
        self.pending = []      # catalogue entries waiting for a pass
        self.falling = []      # pods on their way down
        self.was_overhead = False
        self.scan_used = False
        self.orders = 0
        self.landed = []       # (x, y, time) of recent landings, for the dust ring

    @staticmethod
    def overhead(now):
        t = now - C.FIRST_PASS_S
        return t >= 0 and t % C.PASS_PERIOD_S < C.PASS_DURATION_S

    @staticmethod
    def seconds_to_change(now):
        """Seconds until the current state (overhead or not) flips."""
        t = now - C.FIRST_PASS_S
        if t < 0:
            return -t
        phase = t % C.PASS_PERIOD_S
        return C.PASS_DURATION_S - phase if phase < C.PASS_DURATION_S else C.PASS_PERIOD_S - phase

    def order(self, world, index):
        entry = C.SUPPLY[index]
        if world.credits < entry["cost"]:
            return False, "NOT ENOUGH CREDITS"
        world.credits -= entry["cost"]
        self.pending.append(entry)
        self.orders += 1
        when = "THIS PASS" if self.overhead(world.time_s()) else "NEXT PASS"
        world.event(f"SUPPLY ORDERED: {entry['name'].upper()} - LANDS {when}", "info")
        return True, ""

    def scan(self, world, x, y):
        if not self.overhead(world.time_s()):
            return False, "SHIP NOT OVERHEAD"
        if self.scan_used:
            return False, "SCAN ALREADY USED THIS PASS"
        self.scan_used = True
        world.survey_area(x, y, C.SCAN_RADIUS_CELLS, 1)
        found = 0
        for f in world.fields:
            if not f.hinted and math.hypot(f.cx - x, f.cy - y) <= C.SCAN_RADIUS_CELLS + f.radius:
                world.hint_field(f)
                found += 1
        world.event(f"ORBITAL SCAN COMPLETE - {found} FIELD SIGNAL{'S' if found != 1 else ''}", "field")
        return True, ""

    def update(self, world):
        now = world.time_s()
        over = self.overhead(now)
        if over and not self.was_overhead:
            self.scan_used = False
            world.event("ORBITAL PASS BEGINS - DROPS AND SCAN AVAILABLE", "orbit")
        if not over and self.was_overhead:
            world.event("ORBITAL PASS ENDS", "orbit")
        self.was_overhead = over
        if over and self.pending:
            lander = world.lander
            for k, entry in enumerate(self.pending):
                a = 2 * math.pi * (len(self.falling) + k) / 7 + 0.4
                r = C.DROP_OFFSET_CELLS
                self.falling.append(Pod(entry, now + C.DROP_FALL_S, lander.x + r * math.cos(a), lander.y + r * math.sin(a)))
            self.pending = []
        for pod in list(self.falling):
            if now >= pod.land_s:
                self.falling.remove(pod)
                self._land(world, pod)
                self.landed.append((pod.x, pod.y, now))
        self.landed = [d for d in self.landed if now - d[2] < C.DUST_S]

    def _land(self, world, pod):
        entry = pod.item
        if "unit" in entry:
            world.spawn_unit(entry["unit"], pod.x, pod.y)
        for item, n in entry.get("items", {}).items():
            world.lander.storage[item] = world.lander.storage.get(item, 0) + n
            world.produced[item] = world.produced.get(item, 0) + n
        world.event(f"SUPPLY DROP LANDED: {entry['name'].upper()}", "orbit")
